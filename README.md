# Saloon MIS

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
cd saloon-mis
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Demo users

| Role | Username | Password |
|------|----------|----------|
| Super Admin | admin | admin123 |
| Accounts | accounts | accounts123 |
| Branch Manager | manager | manager123 |

## Production (PostgreSQL)

```bash
docker compose up -d
```

Set in `.env`:

```
DATABASE_URL=postgresql://saloon:saloon@localhost:5432/saloon_mis
SECRET_KEY=your-long-random-secret
DEBUG=False
```

Then run `python manage.py migrate`.

## Business rules

See [docs/business-rules.md](docs/business-rules.md)

Report templates: [docs/templates/](docs/templates/)
