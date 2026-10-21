# About Me

The personal resume website of **Samuel Ryan Andrew Simonds**, Technical Support Engineer in Colorado Springs, Colorado. It is a Flask and PostgreSQL application with six public pages and a private admin panel for updating the photo, resume, links, traits and accomplishments without touching code.

**Live site:** [https://www.ssimonds.com](https://www.ssimonds.com) (`ssimonds.com` forwards there; the site is also served at [about-me-production-361e.up.railway.app](https://about-me-production-361e.up.railway.app))

---

## Pages

| Page | URL | What it shows |
|------|-----|---------------|
| Home | `/` (also `/index.html`) | Centered introduction (portrait, name, title, traits), the full resume drawn into the page, portfolio links, accomplishments, links to every page |
| About | `/about.html` | Background, career objective, strengths, career goals, quick facts |
| Experience | `/experience.html` | Employment history table (eCatholic and Apple) and details for each role |
| Education & Skills | `/skills.html` | BBA from the University of Massachusetts Global, two IBM certifications, and a skills table with category and search filters |
| Projects | `/projects.html` | Featured client projects with screenshots, plus public repositories loaded live from the GitHub REST API |
| Contact | `/contact.html` | Contact form validated in the browser and on the server; messages are stored in PostgreSQL |

Short addresses such as `/about` redirect to the matching `.html` page. Every public page is a complete HTML document with the title `Samuel Simonds - Web Design and Technologies`.

---

## Features

### Design
- Black, off-white and sage palette; Inter for text and Source Serif 4 for display headings
- Centered, symmetrical layouts: centered hero and section titles, balanced card grids, and a centered footer with every page link, email, GitHub and a line-drawn LinkedIn icon
- Circular portraits framed in sage; resume pages shown as sheets of paper

### Public site
- Shared header and navigation on every page; on phones the menu folds behind a Menu button
- The resume (the PDF that matches the visitor's browser language) is drawn page by page with PDF.js at the full width of the screen, so it reads as part of the page with no inner scrollbar on any device. There are no download or open-in-new-tab buttons; a link to the PDF appears only if the resume can't be drawn (for example with JavaScript turned off)
- Skills table filter (category buttons plus a search box) with a live result count
- GitHub REST API integration that lists public repositories with sort options, a 10-minute session cache and an error fallback
- Contact form with inline error messages, focus on the first error, a character counter, a spam honeypot and a limit of five messages per visitor every ten minutes; it also works without JavaScript
- Short UI labels translated into nine languages based on the visitor's browser
- Accessible markup: real headings, labelled fields, table captions and header scopes, skip link, alt text on every image
- Search engine support: `/sitemap.xml`, `/robots.txt`, and a canonical link on every page pointing to `https://www.ssimonds.com`

### Admin panel (`/admin`)
- Upload or remove the profile photo (resized and compressed automatically, phone rotation respected)
- Upload a resume PDF per language and delete old ones
- Edit up to 12 traits, 5 GitHub links, 5 website links and 20 accomplishments
- Side-by-side live preview before saving
- Read and delete messages sent through the Contact page
- Optional TinyPNG compression

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Back end | Python 3.12, Flask 3.0, Gunicorn |
| Database | PostgreSQL 17 on Railway (16 in the local Docker Compose setup), SQLAlchemy with psycopg |
| Front end | Jinja2 templates, HTML5, one CSS stylesheet, vanilla JavaScript, PDF.js 3.11 (resume rendering) |
| Fonts | Inter and Source Serif 4 (Google Fonts) |
| Images | Pillow, optional TinyPNG |
| Hosting | Docker on Railway, domain registered at Network Solutions |

---

## Project Structure

```
About-Me/
├── app.py                     # Flask app: page routes, contact API, admin APIs, sitemap/robots
├── models.py                  # SQLAlchemy models (photo, resumes, links, traits, accomplishments, contact messages)
├── config.py                  # Settings read from environment variables
├── i18n.py                    # Locale selection
├── services/
│   └── image_processing.py    # Photo resizing, rotation and compression
├── templates/
│   ├── index.html             # Homepage
│   ├── about.html
│   ├── experience.html
│   ├── skills.html
│   ├── projects.html
│   ├── contact.html
│   ├── partials/
│   │   ├── site_header.html   # Shared header and navigation
│   │   └── site_footer.html   # Shared footer (page links, email, GitHub, LinkedIn) and scripts
│   ├── base.html              # Layout for the admin pages
│   ├── admin.html             # Admin panel
│   └── admin_login.html
├── static/
│   ├── css/styles.css         # The single stylesheet for the whole site
│   ├── js/site.js             # Navigation, skills filter, GitHub API, contact form, resume rendering
│   ├── js/i18n.js             # Label translations
│   ├── js/admin.js            # Admin panel
│   └── images/                # Portrait, project screenshots, favicon
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Getting Started

### Prerequisites
- Docker and Docker Compose, **or** Python 3.12+ with PostgreSQL

### Option 1: Docker Compose

```bash
git clone https://github.com/SRAS2024/About-Me.git
cd About-Me
cp .env.example .env
# Edit .env with your own values
docker-compose up
```

The app is then available at `http://localhost:8000`.

### Option 2: Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/aboutme"
export SECRET_KEY="dev-secret"
export ADMIN_USERNAME="choose-a-username"
export ADMIN_PASSWORD="choose-a-strong-password"

python -c "from app import app; app.run(debug=True, port=8000)"
```

Tables are created automatically on startup. SSL is required for remote databases and skipped for `localhost`, `127.0.0.1` and the `db` Docker service.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | Session signing key (a long random string). If missing, a random key is generated at startup and admins are signed out on every restart |
| `ADMIN_USERNAME` | Yes | Admin login username. Admin login is disabled if this is not set |
| `ADMIN_PASSWORD` | Yes | Admin login password. Admin login is disabled if this is not set |
| `SITE_URL` | No | Main public address used in the sitemap, robots.txt and canonical links (default `https://www.ssimonds.com`) |
| `TINIFY_API_KEY` | No | TinyPNG API key for extra image compression |
| `PORT` | No | Server port (default 8000; Railway sets it) |

Never commit real values. On Railway they live in the service's Variables tab.

---

## Using the Admin Panel

1. Go to `/admin/login` and sign in.
2. Upload a photo or resume, and edit traits, links and accomplishments. The preview on the right updates as you type.
3. Click **Save All Changes** to save traits, links and accomplishments. Photo and resume uploads save immediately.
4. Read or delete contact messages in the **Contact Messages** section.

---

## Deployment

The site runs on [Railway](https://railway.app) in the project `romantic-wholeness`, service `About-Me`, next to a managed PostgreSQL service. Railway builds the `Dockerfile` and deploys automatically on every push to the `main` branch, which is the only branch in this repository.

### Domain

`ssimonds.com` is registered at Network Solutions and connected to Railway with these DNS records:

| Type | Name | Value |
|------|------|-------|
| CNAME | `www` | `n1fpne6m.up.railway.app` |
| TXT | `_railway-verify.www` | Railway's verification value for `www.ssimonds.com` |
| CNAME | `@` | `0b38yxji.up.railway.app` |
| TXT | `_railway-verify` | Railway's verification value for `ssimonds.com` |

`https://www.ssimonds.com` is the main address. Requests to the bare `ssimonds.com` are forwarded there by the app (`redirect_bare_domain` in `app.py`). Railway issues the HTTPS certificates automatically.

Because the root of the domain is a CNAME, Network Solutions cannot serve other records (such as a Google TXT record) at `ssimonds.com` itself; use subdomain records or file-based verification instead.

### Google Search Console

The site is verified in Google Search Console as the URL-prefix property `https://www.ssimonds.com/` using the HTML file method: the app serves `/google0292583cfdf40074.html`. Keep that route in `app.py`, or Search Console will lose verification. The sitemap `https://www.ssimonds.com/sitemap.xml` is submitted there.

---

## Health Check

```
GET /health
```

Returns `{"status": "ok", "db_ok": true, "db": "ok"}` when the app and database are working.

---

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
