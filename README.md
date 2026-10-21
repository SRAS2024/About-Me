# About Me

A full-stack personal resume website built with Flask and PostgreSQL. It showcases my profile, resume, experience, skills, projects, and accomplishments, and it is managed through an authenticated admin panel with live preview.

**Live site:** [https://ssimonds.com](https://ssimonds.com) (also served at [about-me-production-361e.up.railway.app](https://about-me-production-361e.up.railway.app))

---

## Features

### Pages

| Page | URL | What it shows |
|------|-----|---------------|
| Home | `/` (also `/index.html`) | Hero, traits, photo, embedded resume, portfolio links, accomplishments, links to every page |
| About | `/about.html` | Background, career objective, strengths, career goals, quick facts |
| Experience | `/experience.html` | Employment history table and details for each role |
| Education & Skills | `/skills.html` | Degree, certification, and a skills table with category and search filters |
| Projects | `/projects.html` | Featured client projects with screenshots, plus public repositories loaded live from the GitHub REST API |
| Contact | `/contact.html` | Contact form with browser and server validation; messages are stored in PostgreSQL |

Short addresses such as `/about` redirect to the `.html` pages.

### Public Portfolio
- Hero section with profile photo, tagline, bio, and skill traits
- Embedded PDF resume viewer with locale-aware selection
- Portfolio section for GitHub and website links
- Accomplishments list
- Multi-language support (10 locales including EN, PT, ES, FR, DE, IT, JA, KO, ZH)
- Automatic language detection from browser preferences
- Shared navigation on every page, with a collapsible menu on phones
- Skills filter (category buttons and search) written in plain JavaScript
- GitHub REST API integration on the Projects page (cached for 10 minutes per visit)
- Contact form with inline validation, a spam honeypot and a per-visitor rate limit

### Admin Panel
- Upload and manage profile photo (automatic optimization and resizing)
- Upload resumes per locale with PDF download
- Add, edit, and delete up to 12 traits
- Manage GitHub links (max 5) and website links (max 5)
- Manage up to 20 accomplishments with drag-and-drop reordering
- Real-time side-by-side live preview of all changes
- Read and delete messages sent through the Contact page
- Optional TinyPNG image compression

---

## Tech Stack

| Layer          | Technology                              |
|----------------|-----------------------------------------|
| Backend        | Flask 3.0.3, Gunicorn                   |
| Database       | PostgreSQL 16, SQLAlchemy               |
| Frontend       | Jinja2, Vanilla JS, CSS                 |
| i18n           | Flask-Babel (10 locales)                |
| Image Processing | Pillow, TinyPNG (optional)           |
| Deployment     | Docker, Railway                         |

---

## Project Structure

```
About-Me/
├── app.py                 # Flask application and routes
├── models.py              # SQLAlchemy database models
├── config.py              # Configuration and environment variables
├── i18n.py                # Internationalization setup
├── services/
│   └── image_processing.py
├── templates/
│   ├── partials/
│   │   ├── site_header.html   # Shared header and navigation
│   │   └── site_footer.html   # Shared footer and scripts
│   ├── index.html         # Homepage
│   ├── about.html
│   ├── experience.html
│   ├── skills.html
│   ├── projects.html
│   ├── contact.html
│   ├── base.html          # Layout for the admin pages
│   ├── admin.html         # Admin control panel
│   └── admin_login.html
├── static/
│   ├── css/styles.css     # One stylesheet for the whole site
│   ├── js/site.js         # Navigation, skills filter, GitHub API, contact form
│   ├── js/i18n.js         # Translates short labels to the visitor's language
│   ├── js/admin.js        # Admin panel
│   └── images/            # Portrait, project screenshots, favicon
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Getting Started

### Prerequisites
- Docker & Docker Compose **or** Python 3.12+ with PostgreSQL

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/SRAS2024/About-Me.git
cd About-Me
cp .env.example .env
# Edit .env with your own values
docker-compose up
```

The app will be available at `http://localhost:8000`.

### Option 2: Local Development

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

---

## Environment Variables

| Variable          | Required | Description                              |
|-------------------|----------|------------------------------------------|
| `SECRET_KEY`      | Yes      | Flask session signing key (a long random string) |
| `DATABASE_URL`    | Yes      | PostgreSQL connection string             |
| `ADMIN_USERNAME`  | Yes      | Admin login username (login is disabled if unset) |
| `ADMIN_PASSWORD`  | Yes      | Admin login password (login is disabled if unset) |
| `TINIFY_API_KEY`  | No       | TinyPNG API key for image compression    |
| `PORT`            | No       | Server port (default: 8000)              |

---

## Usage

1. Navigate to `/admin/login` and sign in with your admin credentials.
2. Use the admin panel to upload your photo, resume, traits, links, and accomplishments.
3. Preview changes in real time using the live preview panel.
4. Click **Save All Changes** to persist to the database.
5. Visit the public page at `/` to see your portfolio.

---

## Health Check

```
GET /health
```

Returns `{"status": "ok", "db_ok": true}` when the application and database are running correctly.

---

## Deployment

The application is configured for deployment on [Railway](https://railway.app) with Docker. The included `Dockerfile` and `docker-compose.yml` handle the full setup including PostgreSQL provisioning and Gunicorn as the production server.

---

## License

This project is open source.
