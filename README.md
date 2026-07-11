# SkillBuddy

SkillBuddy is a Django learning-management platform with courses, quizzes,
results, payments, AI tutoring, and student well-being tools.

## Local Setup

Requirements: Python 3.12 and SQLite (included with Python).

### Windows (PowerShell)

```powershell
cd SkillBuddy-master
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements\local.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_role_demo
python manage.py runserver
```

### macOS / Linux

```bash
cd SkillBuddy-master
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements/local.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_role_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000` and sign in. The role-aware workspace opens automatically.

### Demo role accounts

All demo accounts use password `Demo@123`:

| Role | Username |
|---|---|
| Super Admin | `superadmin` |
| College Admin / Principal | `principal` |
| HOD | `hod` |
| Faculty | `faculty` |
| Student | `student` |
| Placement Officer | `placement` |

The seed command is idempotent, so it is safe to run again. These credentials are for local demonstration only; create unique accounts and passwords before deployment. Roles, college scope, and department scope can be edited from Django Admin at `/admin/`.

To use your own administrator instead, run `python manage.py createsuperuser`.

### Verification

```bash
python manage.py check
python manage.py test enterprise core.test_role_workspaces
python manage.py test
```

## Enterprise Operations

SkillBuddy now includes a persistent, tenant-aware operations layer rather than dashboard-only role labels.

- **College tenants:** create, edit, activate, suspend, extend, upgrade, brand, allocate storage, and safely delete colleges.
- **Subscriptions:** plan, monthly price, expiry date, trial/active/suspended lifecycle, and revenue totals.
- **Tenant security:** users are attached to a college; college administrators cannot view or mutate another tenant. Suspended colleges and disabled users cannot authenticate.
- **User operations:** create users, assign primary/custom roles, change college/department, lock/unlock, disable/enable login, verify email, reset passwords, and force logout.
- **Custom RBAC:** create, edit, disable, assign, and delete tenant-scoped custom roles with a persisted permission matrix.
- **Placements:** manage companies and drives, accept one application per student/drive, and move candidates through applied, shortlisted, interview, offered, accepted, or rejected states.
- **Support:** create tenant-scoped tickets and track open, in-progress, and resolved states.
- **Audit trail:** sensitive tenant, user, role, placement, and support actions record actor, target, tenant, time, and IP address.

Operational pages are available through the role-aware Workspace and under `/enterprise/`. Django Admin also exposes these models for controlled back-office recovery.

### Production checklist

Before a public deployment:

1. Replace demo credentials and remove or disable demo accounts.
2. Use PostgreSQL, Redis, HTTPS, secure cookies, and production email/payment credentials.
3. Set a unique `SECRET_KEY`, exact `ALLOWED_HOSTS`, and exact `CSRF_TRUSTED_ORIGINS`.
4. Run `python manage.py check --deploy --settings=config.settings.production` and the complete test suite.
5. Configure database and media backups, log retention, monitoring, and an incident-response contact.

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
