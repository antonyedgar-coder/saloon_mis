# Salon MIS

Management Information System for salon operations — built with **Django**.

## Features

- **Accounts:** GRN (stock inward), outward register with per-branch invoices
- **Branch:** Accept transfers (partial acceptance supported), retail/consumption outward
- **Reports:** Stock registers, DSR, petty cash — Excel export
- **Access control:** Role-based permissions + branch-level data scoping

## Tech stack

- Python 3.11+
- Django 5
- SQLite (dev) / PostgreSQL (production)
- openpyxl for Excel reports

## Getting started

```bash
cd salon-mis
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

Create your own admin with `createsuperuser` (role is set to Super Admin automatically).

## Production (PostgreSQL)

```bash
docker compose up -d
```

Set in `.env`:

```
DATABASE_URL=postgresql://salon:salon@localhost:5432/salon_mis
SECRET_KEY=your-long-random-secret
DEBUG=False
```

Then run `python manage.py migrate`.

## Business rules

See [docs/business-rules.md](docs/business-rules.md)

Report templates: [docs/templates/](docs/templates/)
