from flask import Flask, render_template_string, request, redirect, url_for
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time

app = Flask(__name__)

# --- CONFIGURATION ---
BASE_URL_TEMPLATE = "https://www.blogdumoderateur.com/{category}/page/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SAVE_TO_MONGO = True

if SAVE_TO_MONGO:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["blog"]
    collection = db["articles"]

# --- Scraper Functions ---
def get_article_links(page_url):
    response = requests.get(page_url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    article_blocks = soup.select("article.post")
    links = []
    for article in article_blocks:
        a_tag = article.select_one(".entry-header a")
        if a_tag and a_tag.get("href"):
            links.append(a_tag["href"])
    return links

def scrape_article(url):
    if SAVE_TO_MONGO and collection.find_one({"url": url}):
        return collection.find_one({"url": url})

    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("h1", class_="entry-title")
    title = title_tag.text.strip() if title_tag else "Sans titre"

    date_tag = soup.select_one("span.posted-on time")
    date = date_tag["datetime"] if date_tag and date_tag.has_attr("datetime") else None

    author_tag = soup.select_one("span.byline a")
    author = author_tag.text.strip() if author_tag else None

    summary_tag = soup.select_one("div.article-hat p")
    summary = summary_tag.text.strip() if summary_tag else None

    article_tag = soup.find("article")
    category = None
    if article_tag:
        for c in article_tag.get("class", []):
            if c.startswith("category-"):
                category = c.replace("category-", "").capitalize()
                break

    image_tag = soup.select_one("figure.article-hat-img img")
    image = None
    if image_tag:
        if image_tag.has_attr("data-lazy-src"):
            image = image_tag["data-lazy-src"]
        elif image_tag.has_attr("src") and not image_tag["src"].startswith("data:image"):
            image = image_tag["src"]

    if not image:
        fallback_tag = soup.select_one(".entry-content img")
        if fallback_tag and fallback_tag.has_attr("src") and not fallback_tag["src"].startswith("data:image"):
            image = fallback_tag["src"]

    content_parts = soup.select("div.entry-content p")
    content = "\n".join([p.text.strip() for p in content_parts])

    content_images = []
    seen = set()
    for img in soup.select(".entry-content img"):
        src = img.get("data-lazy-src") or img.get("src")
        if src and not src.startswith("data:image") and src not in seen:
            seen.add(src)
            content_images.append(src)

    article = {
        "url": url,
        "title": title,
        "author": author,
        "summary": summary,
        "category": category,
        "date": date,
        "image": image,
        "content_images": content_images,
        "content": content,
    }

    if SAVE_TO_MONGO:
        collection.insert_one(article)

    return article

TEMPLATE = """
<!DOCTYPE html>
<html lang=\"fr\">
<head>
  <meta charset=\"UTF-8\">
  <title>Scraper BDM</title>
  <style>
    body { font-family: sans-serif; margin: 2rem; background: #f8f9fa; }
    h1 { color: #222; }
    form { margin-bottom: 2rem; padding: 1rem; background: #fff; border: 1px solid #ddd; border-radius: 6px; }
    select, input, button { margin-left: 1rem; padding: 0.4rem; }
    ul { list-style: none; padding-left: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }
    li { background: #fff; padding: 1rem; border: 1px solid #ddd; border-radius: 6px; box-shadow: 1px 1px 4px rgba(0,0,0,0.1); position: relative; }
    a { text-decoration: none; color: #007BFF; }
    .image-preview { width: 100%; height: 180px; object-fit: cover; margin-bottom: 0.5rem; border-radius: 4px; background: #eee; }
    .loader { display: none; margin-top: 1rem; }
    .loading .loader { display: block; font-weight: bold; color: #555; }
    small { color: #555; }
  </style>
<script>
  function showLoader() {
    document.querySelector('form').classList.add('loading');
  }

  function updateFormAction(el) {
    const category = el.value;
    const pageInput = document.querySelector('input[name=pages]');
    const button = document.querySelector('form button');
    if (category === 'all') {
      button.disabled = true;
    } else {
      button.disabled = false;
    }

    const formData = new URLSearchParams();
    formData.append('category', category);
    formData.append('pages', pageInput.value);

    fetch('/filter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData
    }).then(response => response.text()).then(html => {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      document.body.innerHTML = doc.body.innerHTML;

      // Réattacher l’event une seule fois
      attachEvents();
    });
  }

  function attachEvents() {
    const catSelect = document.querySelector('select[name=category]');
    if (catSelect && !catSelect.dataset.bound) {
      catSelect.addEventListener('change', () => updateFormAction(catSelect));
      catSelect.dataset.bound = "true";
    }
  }

  window.addEventListener('DOMContentLoaded', attachEvents);
</script>

</head>
<body>
  <h1>📰 Scraper Blog du Modérateur</h1>
  <form method=\"post\" action=\"/scrape\" onsubmit=\"showLoader()\">
    <label>Catégorie :
      <select name=\"category\">
        <option value=\"all\" {% if selected_category == 'all' %}selected{% endif %}>ALL</option>
        <option value=\"web\" {% if selected_category == 'web' %}selected{% endif %}>Web</option>
        <option value=\"marketing\" {% if selected_category == 'marketing' %}selected{% endif %}>Marketing</option>
        <option value=\"social\" {% if selected_category == 'social' %}selected{% endif %}>Social</option>
        <option value=\"tech\" {% if selected_category == 'tech' %}selected{% endif %}>Tech</option>
        <option value=\"tools\" {% if selected_category == 'tools' %}selected{% endif %}>Tools</option>
      </select>
    </label>
    <label>Nombre de pages : <input type=\"number\" name=\"pages\" min=\"1\" value=\"5\"></label>
    <button type=\"submit\" {% if selected_category == 'all' %}disabled{% endif %}>Lancer le scraping</button>
    <div class=\"loader\">⏳ Scraping en cours...</div>
  </form>

  <h2>{{ articles|length }} articles affichés :</h2>
  <ul>
    {% for art in articles %}
      <li>
        {% if art.image %}<img src=\"{{ art.image }}\" class=\"image-preview\">{% endif %}
        <a href=\"/article?url={{ art.url|urlencode }}\"><strong>{{ art.title }}</strong></a><br>
        <small>{{ art.date }} par {{ art.author }}</small>
      </li>
    {% endfor %}
  </ul>
</body>
</html>
"""

ARTICLE_TEMPLATE = """
<!DOCTYPE html>
<html lang='fr'>
<head>
  <meta charset='UTF-8'>
  <title>{{ article.title }}</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: auto; background: #f9f9f9; padding: 2rem; }
    h1 { color: #333; }
    img { max-width: 100%; margin: 1rem 0; border-radius: 6px; }
    .meta { color: #666; font-size: 0.9rem; margin-bottom: 1rem; }
    .summary { font-style: italic; margin-bottom: 1.5rem; }
  </style>
</head>
<body>
  <h1>{{ article.title }}</h1>
  <div class="meta">Publié le {{ article.date }} par {{ article.author }} | Catégorie : {{ article.category }}</div>
  {% if article.image %}<img src="{{ article.image }}" alt="Image de l'article">{% endif %}
  <p class="summary">{{ article.summary }}</p>
  <p>{{ article.content.replace('\n', '<br>')|safe }}</p>
  {% if article.content_images %}
    <h3>Images dans l'article :</h3>
    {% for img in article.content_images %}
      <img src="{{ img }}" alt="Image de l'article">
    {% endfor %}
  {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    existing_articles = list(collection.find().sort("date", -1)) if SAVE_TO_MONGO else []
    return render_template_string(TEMPLATE, articles=existing_articles, selected_category="all")

@app.route("/scrape", methods=["POST"])
def scrape():
    category = request.form.get("category")
    if category == "all":
        return redirect(url_for("index"))
    nb_pages = int(request.form.get("pages", 5))
    base_url = BASE_URL_TEMPLATE.format(category=category)

    results = []
    for page_num in range(1, nb_pages + 1):
        page_url = f"{base_url}{page_num}/"
        try:
            links = get_article_links(page_url)
            for link in links:
                if not collection.find_one({"url": link}):
                    article = scrape_article(link)
                    results.append(article)
                    time.sleep(0.5)
        except Exception as e:
            print(f"Erreur sur la page {page_num}: {e}")

    return redirect(url_for("index"))

@app.route("/filter", methods=["POST"])
def filter_category():
    category = request.form.get("category")
    if category == "all":
        articles = list(collection.find().sort("date", -1))
    else:
        articles = list(collection.find({"category": category.capitalize()}).sort("date", -1))
    return render_template_string(TEMPLATE, articles=articles, selected_category=category)

@app.route("/article")
def view_article():
    url = request.args.get("url")
    article = collection.find_one({"url": url})
    if not article:
        article = scrape_article(url)
    return render_template_string(ARTICLE_TEMPLATE, article=article)

if __name__ == "__main__":
    app.run(debug=True)

