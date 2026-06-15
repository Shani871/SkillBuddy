# SkillBuddy

SkillBuddy is a Django learning-management platform with courses, quizzes,
results, payments, AI tutoring, and student well-being tools.

## Local Setup

Requirements: Python 3.12 and SQLite (included with Python).

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements/local.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Production Environment

Copy `.env.production.template` to `.env.production` and replace every
placeholder. At minimum, configure:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<unique random value, at least 50 characters>
ALLOWED_HOSTS=your-domain.example
CSRF_TRUSTED_ORIGINS=https://your-domain.example
DATABASE_URL=postgresql://user:password@host:5432/database
DB_SSL_REQUIRE=True
```

Generate a secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## Deploy With Docker

Docker Compose starts Django, PostgreSQL, and Redis with persistent database
and media volumes.

```bash
cp .env.production.template .env.production
# Edit .env.production before continuing.
docker compose up --build -d
docker compose exec web python manage.py createsuperuser
```

The app is served at `http://localhost:8000`. Put a TLS reverse proxy such as
Caddy, Nginx, or your cloud load balancer in front of it for a public server.

To run the optional Celery worker:

```bash
docker compose --profile async up --build -d
```

## Deploy On Render

1. Push this repository to GitHub or GitLab.
2. In Render, create a Blueprint and select the repository.
3. Render reads `render.yaml` and creates the web service and PostgreSQL.
4. Set `ALLOWED_HOSTS` to the generated host, such as
   `skillbuddy-xxxx.onrender.com`.
5. Set `CSRF_TRUSTED_ORIGINS` to its full HTTPS URL.
6. After deployment, open a Render shell and run:

```bash
python manage.py createsuperuser
```

The included `/health/` endpoint is used for health checks.
The Blueprint uses small paid instances because persistent media disks are not
available on free web instances.

## Static And Media Files

Static files are collected automatically and served by WhiteNoise.

For one web instance, set `SERVE_MEDIA_FILES=True` and attach a persistent
volume at `/app/media`. For multiple instances, configure the `AWS_*`
variables in `.env.production.template` for Amazon S3, Cloudflare R2, or
another S3-compatible service, and leave `SERVE_MEDIA_FILES=False`.

## Optional Face Analysis

Face-emotion packages are intentionally separate because they substantially
increase build size:

```bash
pip install -r requirements/ai.txt
```

Without them, emotion capture remains available and safely falls back to a
neutral result.

## Production Commands

```bash
python manage.py check --deploy --settings=config.settings.production
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Run tests with:

```bash
python manage.py test --settings=config.settings.test
```
