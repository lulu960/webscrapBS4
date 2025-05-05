# 📰 Scraper BDM (Blog du Modérateur)

Interface web en Flask permettant de scraper automatiquement les articles du Blog du Modérateur par catégorie, et de les filtrer selon plusieurs critères.

---

## 🚀 Fonctionnalités

- Scraping par catégorie (`Web`, `Marketing`, `Social`, `Tech`)
- Spécification du nombre de pages à scraper
- Sauvegarde dans MongoDB
- Interface avec filtres :
  - Catégorie et sous-catégorie
  - Auteur (recherche)
  - Titre (sous-chaîne)
  - Période de publication (début / fin)
  - Tri par date ou auteur
- Visualisation détaillée de chaque article

---

## 🔧 Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/ton-utilisateur/scraper-bdm.git
cd webscrapBS4
```

### 2. Créer un environnement virtuel (optionnel)
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Lancer MongoDB
Assurez-vous que MongoDB est lancé sur `localhost:27017`.

### 5. Lancer le serveur Flask
```bash
python app.py
```

L’application est disponible sur [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 📦 Fichier `requirements.txt`

```
Flask==2.3.2
requests==2.31.0
beautifulsoup4==4.12.2
pymongo==4.5.0
```

---

## 🧪 Exemple de structure MongoDB

```json
{
  "url": "https://www.blogdumoderateur.com/exemple/",
  "title": "Titre",
  "author": "Jean Dupont",
  "date": "2025-03-20T11:10:00+01:00",
  "summary": "Chapeau de l’article...",
  "category": "Web",
  "subcategories": ["Google", "DMA"],
  "image": "https://image-principale.jpg",
  "content": "Contenu complet...",
  "content_images": [
    "https://img1.jpg",
    "https://img2.jpg"
  ]
}
```

---

## 📁 Structure du projet

```
.
├── app.py
├── template.html
├── article_template.html
├── requirements.txt
└── README.md
```

---

## ✅ TODO

- [ ] Ajout de pagination
- [ ] Export CSV ou JSON
- [ ] Déploiement Docker
- [ ] Support multi-thread scraping
- [ ] Debuger la recherche par catégorie

---
