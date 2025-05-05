from flask import Flask, render_template_string, request, redirect, url_for
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time

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
    subcategories = []
    if article_tag:
        for c in article_tag.get("class", []):
            if c.startswith("category-"):
                category = c.replace("category-", "").capitalize()
            if c.startswith("tag-"):
                subcategories.append(c.replace("tag-", "").capitalize())

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
        "subcategories": subcategories,
        "date": date,
        "image": image,
        "content_images": content_images,
        "content": content,
    }

    if SAVE_TO_MONGO:
        collection.insert_one(article)

    return article

# --- Flask Web App ---
app = Flask(__name__)

with open("template.html", encoding="utf-8") as f:
    TEMPLATE = f.read()

with open("article_template.html", encoding="utf-8") as f:
    ARTICLE_TEMPLATE = f.read()


@app.route("/", methods=["GET"])
def index():
    sort_by = request.args.get("sort", "date")
    order = -1 if sort_by == "date" else 1
    sort_field = "date" if sort_by == "date" else "author"
    existing_articles = list(collection.find().sort(sort_field, order)) if SAVE_TO_MONGO else []
    return render_template_string(TEMPLATE, articles=existing_articles, selected_category="all", sort_by=sort_by)

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
    sort_by = request.form.get("sort", "date")
    order = -1 if sort_by == "date" else 1
    sort_field = "date" if sort_by == "date" else "author"

    if category == "all":
        articles = list(collection.find().sort(sort_field, order))
    else:
        articles = list(collection.find({"category": category.capitalize()}).sort(sort_field, order))
    return render_template_string(TEMPLATE, articles=articles, selected_category=category, sort_by=sort_by)

@app.route("/article")
def view_article():
    url = request.args.get("url")
    article = collection.find_one({"url": url})
    if not article:
        article = scrape_article(url)
    return render_template_string(ARTICLE_TEMPLATE, article=article)

if __name__ == "__main__":
    app.run(debug=True)
