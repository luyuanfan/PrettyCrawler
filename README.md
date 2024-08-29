# PrettyScraper

clone this repo.

make a virtual env.
```bash
$ python3 -m venv .venv
$ . .venv/bin/activate
```

to run server, go to the crawler directory and run:

```bash
$ python manage.py runserver
```

```
PrettyScrapper
├─ 📁prettyscraper
│  ├─ 📁frontend
│  │  ├─ 📁src
│  │  │  └─ 📄index.ts
│  │  ├─ 📁static
│  │  │  ├─ 📄scraper_icon.png
│  │  │  └─ 📄scraper_logo.png
│  │  ├─ 📄package-lock.json
│  │  ├─ 📄package.json
│  │  ├─ 📄tsconfig.json
│  │  └─ 📄urls.py
│  ├─ 📁prettyscraper
│  │  ├─ 📄__init__.py
│  │  ├─ 📄asgi.py
│  │  ├─ 📄settings.py
│  │  ├─ 📄urls.py
│  │  └─ 📄wsgi.py
│  ├─ 📁scraper
│  │  ├─ 📁templates
│  │  │  ├─ 📄home.html
│  │  │  └─ 📄pdf_result.html
│  │  ├─ 📄__init__.py
│  │  ├─ 📄admin.py
│  │  ├─ 📄apps.py
│  │  ├─ 📄models.py
│  │  ├─ 📄tests.py
│  │  ├─ 📄urls.py
│  │  └─ 📄views.py
│  ├─ 📁static
│  │  ├─ 📄scraper_icon.png
│  │  └─ 📄scraper_logo.png
│  ├─ 📄db.sqlite3
│  └─ 📄manage.py
├─ 📄.dockerignore
├─ 📄.gitignore
├─ 📄Dockerfile
├─ 📄README.Docker.md
├─ 📄README.md
├─ 📄compose.yaml
└─ 📄requirements.txt
```