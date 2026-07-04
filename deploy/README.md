# Deploy Saloon MIS to DigitalOcean (via GitHub)

Droplet example: **Saloon-mis** — `168.144.17.152`

## Overview

1. Push code to GitHub (`main` branch).
2. One-time setup on the droplet (clone, Python, nginx, gunicorn).
3. Every push to `main` runs GitHub Actions → SSH → `deploy/deploy.sh`.

Uses **SQLite** on the droplet (no managed database required).

---

## A. Put the project on GitHub

On your PC (PowerShell), in the project folder:

```powershell
cd c:\Users\anton\projects\saloon-mis
git add .
git commit -m "Prepare production deploy"
```

Create a new empty repo on GitHub (e.g. `saloon-mis`), then:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/saloon-mis.git
git branch -M main
git push -u origin main
```

Use your real GitHub username/repo URL.

---

## B. One-time droplet setup

### 1. SSH into the droplet

```powershell
ssh root@168.144.17.152
```

(If you created a non-root user with your SSH key, use that user and `sudo` where needed.)

### 2. Run setup (replace YOUR_USERNAME)

```bash
export REPO_URL=https://github.com/YOUR_USERNAME/saloon-mis.git
export DOMAIN_OR_IP=168.144.17.152
# Temporary clone to get scripts, or clone fully:
git clone "$REPO_URL" /tmp/saloon-mis-setup
bash /tmp/saloon-mis-setup/deploy/setup_droplet.sh
```

Or, if the repo is private, use a deploy token / SSH deploy key for `git clone`.

### 3. Create admin user (if seed did not run)

```bash
cd /var/www/saloon-mis
sudo -u www-data .venv/bin/python manage.py createsuperuser
```

### 4. Open in browser

http://168.144.17.152

---

## C. GitHub Actions secrets

In GitHub: **Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|-------------|--------|
| `DROPLET_HOST` | `168.144.17.152` |
| `DROPLET_USER` | `root` (or your sudo user) |
| `DROPLET_SSH_KEY` | **Private** key contents (`id_ed25519`, not `.pub`) |

Private key (on your PC):

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519
```

Paste the full block including:

```text
-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
```

The **public** key must already be in the droplet’s `~/.ssh/authorized_keys` (you added it when creating the droplet).

If the Actions user is not `root`, that user needs passwordless sudo for deploy:

```bash
echo 'YOUR_USER ALL=(ALL) NOPASSWD: /bin/bash /var/www/saloon-mis/deploy/deploy.sh' >> /etc/sudoers.d/saloon-mis
```

(Or run Actions as `root` for simplicity.)

---

## D. Deploy from GitHub

Every push to `main`:

```powershell
git add .
git commit -m "Your message"
git push origin main
```

Check: **GitHub → Actions** tab for the deploy run.

Manual deploy without waiting for Actions (on the droplet):

```bash
cd /var/www/saloon-mis
bash deploy/deploy.sh
```

---

## Files

| Path | Purpose |
|------|---------|
| `deploy/setup_droplet.sh` | One-time server install |
| `deploy/deploy.sh` | Pull, migrate, restart |
| `deploy/saloon-mis.service` | systemd / gunicorn |
| `deploy/nginx-saloon-mis.conf` | nginx reverse proxy |
| `.github/workflows/deploy.yml` | GitHub Actions |

---

## Troubleshooting

```bash
# App status
systemctl status saloon-mis

# Logs
journalctl -u saloon-mis -n 50 --no-pager
tail -n 50 /var/log/saloon-mis/error.log

# Nginx
nginx -t
systemctl status nginx
```

If the site does not load, check DigitalOcean **Firewall / Networking**: allow inbound **TCP 80** (and 22 for SSH).
