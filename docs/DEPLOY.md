# Deploying to a VPS

Two supported paths. **Docker is recommended** — Tesseract OCR and all system
dependencies are baked into the images, so there's nothing to install on the
host except Docker itself.

---

## Option A — Docker (recommended)

### 1. Install Docker on the VPS (Ubuntu)

```bash
curl -fsSL https://get.docker.com | sh
```

### 2. Get the code + set secrets

```bash
git clone <your-repo-url> document-processor
cd document-processor
cp backend/.env.example backend/.env
nano backend/.env        # set GEMINI_API_KEY and PINECONE_API_KEY
```

> Leave `TESSERACT_CMD` blank — Tesseract is installed inside the backend image
> and is on the PATH. (The compose file also force-clears it.)

### 3. Launch

```bash
docker compose up -d --build
```

That's it. Open **http://&lt;your-server-ip&gt;/**

- `frontend` (nginx) serves the built React app on **port 80** and proxies
  `/api` + `/health` to the backend container.
- `backend` is internal only (not published) and persists data in the
  `backend-data` volume.

### Common operations

```bash
docker compose logs -f backend     # tail backend logs
docker compose ps                  # status
docker compose up -d --build       # redeploy after a code change
docker compose down                # stop (data volume is kept)
```

### HTTPS

Put a TLS-terminating reverse proxy in front (recommended): Caddy or Traefik with
automatic Let's Encrypt, or nginx + certbot on the host pointing at port 80. For
a quick start, [Caddy](https://caddyserver.com/) needs only a two-line Caddyfile
proxying your domain to `localhost:80`.

---

## Option B — Bare metal (systemd + nginx, no Docker)

A script installs everything, **including Tesseract via apt**, builds the
frontend, and wires up systemd + nginx.

```bash
git clone <your-repo-url> /opt/document-processor
cd /opt/document-processor
sudo bash deploy/install-ubuntu.sh
# edit the generated backend/.env, then:
sudo systemctl restart docprocessor
```

What the script does:

- `apt-get install tesseract-ocr …` — the OCR engine, installed directly.
- Creates a Python 3.11 venv and installs `backend/requirements.txt`.
- `npm run build` → static frontend in `frontend/dist`.
- Installs a **systemd** unit (`docprocessor`) running uvicorn on `127.0.0.1:8000`.
- Installs an **nginx** site serving `frontend/dist` and proxying `/api` + `/health`.

### Operations

```bash
sudo systemctl status docprocessor
sudo journalctl -u docprocessor -f      # logs
sudo systemctl restart docprocessor      # after editing .env or pulling code
```

After pulling new code, rebuild the frontend and restart:

```bash
cd /opt/document-processor/frontend && npm run build
sudo systemctl restart docprocessor
```

---

## Sizing & notes

- **RAM:** the embedding model (~`all-MiniLM-L6-v2`) plus OCR want a little
  headroom — a 2 GB VPS is a sensible minimum, 4 GB is comfortable.
- **Single worker by design.** The document registry is in-process state, so the
  backend runs one uvicorn worker. For higher throughput, move the registry to a
  database and ingestion to a task queue first (see `docs/ARCHITECTURE.md`).
- **Uploads & timeouts.** Both nginx configs allow 200 MB uploads and use long
  proxy timeouts so large-document summarisation / OCR doesn't get cut off. Keep
  `client_max_body_size` in sync with `MAX_UPLOAD_MB`.
- **Persistence.** Docker keeps data in the `backend-data` volume; bare metal
  keeps it in `backend/data/`. Pinecone holds the vectors either way.
- **Local development** uses a different compose file:
  `docker compose -f docker-compose.dev.yml up --build` (hot-reload frontend +
  backend).
