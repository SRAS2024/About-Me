# About Me

A full-stack personal portfolio web application built with Flask and PostgreSQL. Showcase your profile, resume, portfolio links, accomplishments, and traits — all manageable through an authenticated admin panel with live preview.

**Live Demo:** [https://about-me-production-361e.up.railway.app](https://about-me-production-361e.up.railway.app)

---

## Features

### Public Portfolio
- Hero section with profile photo, tagline, bio, and skill traits
- Embedded PDF resume viewer with locale-aware selection
- Portfolio section for GitHub and website links
- Accomplishments list
- Multi-language support (10 locales including EN, PT, ES, FR, DE, IT, JA, KO, ZH)
- Automatic language detection from browser preferences

### Admin Panel
- Upload and manage profile photo (automatic optimization and resizing)
- Upload resumes per locale with PDF download
- Add, edit, and delete up to 12 traits
- Manage GitHub links (max 5) and website links (max 5)
- Manage up to 20 accomplishments with drag-and-drop reordering
- Real-time side-by-side live preview of all changes
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
│   ├── base.html
│   ├── index.html         # Public portfolio page
│   ├── admin.html         # Admin control panel
│   └── admin_login.html
├── static/
│   ├── css/styles.css
│   └── js/admin.js
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
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="admin"

python -c "from app import app; app.run(debug=True, port=8000)"
```

---

## Environment Variables

| Variable          | Required | Description                              |
|-------------------|----------|------------------------------------------|
| `SECRET_KEY`      | Yes      | Flask session signing key                |
| `DATABASE_URL`    | Yes      | PostgreSQL connection string             |
| `ADMIN_USERNAME`  | Yes      | Admin login username                     |
| `ADMIN_PASSWORD`  | Yes      | Admin login password                     |
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
