# Deployment Guide

The production build is a single Docker container that serves both the Django backend (via Daphne/ASGI) and the pre-built React frontend (via WhiteNoise).

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with the Compose plugin (v2)
- `make`

---

## Steps

### 1. Configure environment variables

```sh
cp backend/.env.template backend/.env
```

Edit `backend/.env` and set the following for production:

```
SECRET_KEY=<a-long-random-secret-key>
ALLOWED_HOSTS=<your-server-ip-or-domain>
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

`DEBUG` is forced to `False` by the production settings module regardless of this file.

### 2. Build and start

```sh
make prod
```

This runs `docker compose -f docker-compose.prod.yml up --build`, which:

1. Builds the frontend (`npm run build`) inside a Node.js container.
2. Copies the resulting `dist/` assets into the Python image.
3. Runs `collectstatic` at build time so WhiteNoise can serve static files.
4. Starts Daphne on port `8000`.

The application is accessible on **port 8000** of the host.

### 3. Persistent data

Schedule databases are stored in a named Docker volume (`pi_db_data`) mounted at `/workspace/databases` inside the container. This volume persists across container restarts and rebuilds.

To inspect or back up the databases, use:

```sh
docker run --rm -v pi_db_data:/data alpine ls /data
```

---

## Maintenance

### Stop the application

```sh
docker compose -f docker-compose.prod.yml down
```

### View logs

```sh
docker compose -f docker-compose.prod.yml logs -f
```

### Wipe the database volume

```sh
make clean-db-volume
```

> **Warning:** this permanently deletes all schedule projects and user data stored in the volume.

### Rebuild after code changes

```sh
make prod
```

Docker Compose will rebuild the image and recreate the container. The database volume is unaffected.

---

## Reverse proxy (optional)

The container exposes only port 8000. If you need HTTPS or want to expose the app on port 80/443, place a reverse proxy (e.g. Nginx, Caddy, Traefik) in front of it and proxy requests to `localhost:8000`.

Example minimal Nginx block:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
