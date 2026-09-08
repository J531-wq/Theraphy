# Deploying MyTherapyDoctor to a VPS (Ubuntu 22.04/24.04)

Stack: **Nginx** (reverse proxy + static files) → **Gunicorn** (app server) → **Django**, with **PostgreSQL** and **HTTPS via Let's Encrypt**.

---

## 0. Prerequisites

- A VPS running Ubuntu, Debian, CentOS/Rocky/AlmaLinux, Alibaba Cloud Linux, or Alpine
- A domain name (e.g. `mytherapydoctor.com`) with an **A record** pointing to the VPS IP
- Your secrets ready: `SECRET_KEY`, `GROQ_API_KEY`, ZeptoMail `EMAIL_HOST_PASSWORD`

> **First, identify your OS** → `cat /etc/os-release`
>
> - **Debian/Ubuntu** → use the commands below (`apt`, `ufw`, `sudo` group)
> - **CentOS/Rocky/AlmaLinux/Alibaba Cloud Linux** → see **RHEL-family variant** below
>   (`dnf` instead of `apt`, `wheel` group instead of `sudo`, `firewalld` instead of `ufw`)
> - **Alpine** → see **Alpine variant** below (`apk` instead of `apt`, no `ufw`)
>
> The Django / gunicorn / nginx / certbot steps (steps 5–12) are identical on
> RHEL-family and Alpine **except** nginx config goes in `/etc/nginx/conf.d/`
> on those systems (not `sites-available/`), and you must
> `setsebool -P httpd_can_network_connect 1` on RHEL-family to let nginx proxy.

---

### RHEL-family variant (CentOS 9 / Rocky / Alma / Alibaba Cloud Linux 3)
Run as **root** — no deployment user is created (run the app as root or `deploy`):

```bash
dnf update -y
dnf install -y epel-release
dnf install -y python3 python3-pip python3-venv glibc-langpack-en git nginx postgresql-server firewalld
systemctl enable --now postgresql
systemctl enable --now firewalld
systemctl enable --now nginx
# app user (replaces ufw; firewalld):
adduser deploy && passwd deploy
usermod -aG wheel deploy
echo 'deploy ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/deploy
mkdir -p /home/deploy/therapy_site && chown -R deploy:deploy /home/deploy/therapy_site
# SELinux: allow nginx to proxy to gunicorn
setsebool -P httpd_can_network_connect 1
firewall-cmd --permanent --add-service=ssh --add-service=http --add-service=https
firewall-cmd --reload
```

Continue at **Step 5** below, but use `yum`/`dnf` instead of `apt` when installing,
place the nginx config at `/etc/nginx/conf.d/therapy_site.conf`, and restart with
`systemctl restart nginx`. PostgreSQL version on RHEL/CentOS 9: `postgresql-server`
(currently 15). Adjust the `CREATE USER` syntax if psql gives an error — modern
psql is fine with `CREATE USER ... WITH PASSWORD;`.

### Alpine variant
Use `apk add` instead of `apt`/`ufw` (no ufw on Alpine; use `iptables` or the
cloud provider firewall). Install with: `apk add --no-cache python3 py3-pip git nginx postgresql py3-virtualenv`.
Create the user with `adduser -D deploy` and add to wheel: `addgroup deploy wheel`.
Configure nginx the same way as RHEL (drop config in `/etc/nginx/http.d/` on
Alpine), and start services with `rc-service` instead of `systemctl`.

---

## 1. Point your domain to the VPS

In your DNS provider, create:

| Type | Name  | Value         | TTL  |
|------|-------|---------------|------|
| A    | @     | YOUR.VPS.IP   | 300  |
| A    | www   | YOUR.VPS.IP   | 300  |

Verify (from your PC): `ping yourdomain.com` → should show the VPS IP.

---

## 2. Initial server setup (on the VPS via SSH)

```bash
ssh root@YOUR.VPS.IP

# update system
apt update && apt upgrade -y

# create a non-root user that will run the app
adduser deploy
usermod -aG sudo deploy

# firewall: allow SSH, HTTP, HTTPS only
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
ufw status
```

Log in as the new user from now on: `ssh deploy@YOUR.VPS.IP`

---

## 3. Install packages

```bash
sudo apt install -y python3 python3-venv python3-pip git nginx postgresql postgresql-contrib
```

---

## 4. Create the PostgreSQL database

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE therapy_db;
CREATE USER therapy_user WITH PASSWORD 'STRONG_PASSWORD_HERE';
GRANT ALL PRIVILEGES ON DATABASE therapy_db TO therapy_user;
ALTER USER therapy_user CREATEDB;   -- lets Django run tests later
\q
```

---

## 5. Get the code onto the server

Run these **on the VPS** (from your home folder), replacing the URL with your repo:

```bash
cd ~
git clone https://github.com/J531-wq/Theraphy.git
mv Theraphy therapy_site
cd therapy_site/therapy_site   # this is the Django project root (contains manage.py)
pwd                            # should print /home/deploy/therapy_site/therapy_site
```

(If the repo is private, set up a GitHub **deploy key** or use HTTPS with a token.)

---

## 6. Create the Python virtual environment & install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` already contains gunicorn, whitenoise, psycopg2-binary, dj-database-url, python-dotenv, groq — everything needed.

---

## 7. Create the production `.env`

The Django settings load `.env` from the project root (`therapy_site/`). Copy the template and edit:

```bash
cp .env.example .env
nano .env
```

Set it to **production mode**:

```env
SECRET_KEY=a-long-random-64-char-string
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
GROQ_API_KEY=your-groq-key

DATABASE_URL=postgresql://therapy_user:STRONG_PASSWORD_HERE@localhost:5432/therapy_db

EMAIL_HOST=smtp.zeptomail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=emailapikey
EMAIL_HOST_PASSWORD=your-zepto-api-key
DEFAULT_FROM_EMAIL=info@mytherapydoctor.com
ADMIN_EMAIL=info@mytherapydoctor.com

SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

Generate a secret key:
`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

Lock the file down: `chmod 600 .env`

> ⚠️ With `DEBUG=False`, Django refuses to start unless `SECRET_KEY` is set — that's intentional (enforced in `settings.py`).

---

## 8. Migrate, collect static files, create admin

```bash
python manage.py migrate
python manage.py collectstatic --noinput   # → staticfiles/ (served by nginx)
python manage.py createsuperuser
```

Quick sanity test with gunicorn:

```bash
gunicorn --bind 0.0.0.0:8000 therapy_site.wsgi:application
```

Visit `http://YOUR.VPS.IP:8000` — the welcome page should load (CSS included thanks to whitenoise). Stop it with `CTRL+C`.

---

## 9. Run Gunicorn as a systemd service

```bash
sudo cp deploy/therapy_site.service /etc/systemd/system/
sudo nano /etc/systemd/system/therapy_site.service   # check paths/user match yours
sudo systemctl daemon-reload
sudo systemctl enable --now therapy_site
sudo systemctl status therapy_site
```

Useful commands later:

```bash
sudo systemctl restart therapy_site   # after code changes
sudo journalctl -u therapy_site -f    # live logs
```

---

## 10. Configure Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/therapy_site
sudo nano /etc/nginx/sites-available/therapy_site   # set your real domain in server_name
sudo ln -s /etc/nginx/sites-available/therapy_site /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t          # must say "syntax is ok"
sudo systemctl restart nginx
```

Now open `http://yourdomain.com` — the site should be live over HTTP.

---

## 11. Enable HTTPS (Let's Encrypt — free, auto-renewing)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
sudo certbot renew --dry-run   # verify auto-renewal
```

Because `settings.py` already sets `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` and `SECURE_PROXY_SSL_HEADER` when `DEBUG=False`, everything is HTTPS-only after this step. ✅

---

## 12. Deploying updates (from your PC)

```bash
git add -A && git commit -m "update" && git push origin main
```

On the VPS:

```bash
cd ~/therapy_site/therapy_site
source venv/bin/activate
git pull
pip install -r requirements.txt      # only if deps changed
python manage.py migrate             # only if migrations changed
python manage.py collectstatic --noinput
sudo systemctl restart therapy_site
```

---

## Troubleshooting

| Symptom | Check |
|---|---|
| 502 Bad Gateway | `sudo systemctl status therapy_site` — gunicorn down. `sudo journalctl -u therapy_site -n 50` for the error. |
| CSS/images missing | `collectstatic` not run, or wrong `alias` path in nginx; check `staticfiles/` exists. |
| 400 Bad Request on POST | Domain missing from `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` in `.env`, then restart the service. |
| `SECRET_KEY must be set when DEBUG=False` | `.env` unreadable by the service user or key missing. |
| Emails not sending | Verify `EMAIL_HOST_PASSWORD`; confirm VPS allows outbound port 587. |
| Verify deployment config | `python manage.py check --deploy` |

---

## Security checklist

- [x] `DEBUG=False` in production
- [x] `SECRET_KEY` generated, only in `.env` (chmod 600), git-ignored
- [x] PostgreSQL instead of SQLite
- [x] HTTPS + HSTS enabled (settings already handle cookies/redirect)
- [ ] `ufw` enabled (done in step 2 — verify with `sudo ufw status`)
- [ ] Optional: `sudo apt install unattended-upgrades` for auto security patches
- [ ] Optional: nightly DB backup via cron: `sudo -u postgres pg_dump therapy_db > ~/backups/therapy_db_$(date +\%F).sql`

