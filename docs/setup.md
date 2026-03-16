# Setup Guide

## 1. Clone the repository

```sh
git clone <repository-url>
cd Horarios
```

## 2. Configure environment variables

```sh
cp backend/.env.template backend/.env
```

Open `backend/.env` and set at minimum:

```
SECRET_KEY=any-random-string-for-local-dev
```

The remaining variables have sensible defaults for local development and can be left as-is.

---

## 3. Install local tools for development

### Python 3.14

We recommend [pyenv](https://github.com/pyenv/pyenv) to manage Python versions:

```sh
# Install pyenv (if not already installed)
curl https://pyenv.run | bash

# Install Python 3.14
pyenv install 3.14
pyenv local 3.14   # pins the version for this directory
```

### pipenv

```sh
pip install pipenv
```

### Node.js 24

We recommend [nvm](https://github.com/nvm-sh/nvm):

```sh
# Install nvm (if not already installed)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash

# Install and use Node 24
nvm install 24
nvm use 24
```

### Install dependencies

**Backend:**

```sh
cd backend
pipenv install --dev
```

**Frontend:**

```sh
cd frontend
npm ci
```

---

## 4. Run locally

<details>
<summary><strong>Docker (recommended)</strong></summary>

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) with the Compose plugin (v2) and `make`.

```sh
make dev
```

This builds and starts two containers:

| Service    | URL                   | Description                                   |
| ---------- | --------------------- | --------------------------------------------- |
| `frontend` | http://localhost:5173 | Vite dev server (React + TypeScript) with HMR |
| `backend`  | http://localhost:8000 | Django development server                     |

Both services use bind mounts, so code changes are reflected immediately without rebuilding.

</details>

<details>
<summary><strong>Bare-metal</strong></summary>

Requires the local tools from step 3 to be installed.

**Backend:**

```sh
cd backend
pipenv shell           # activate the virtual env
python manage.py migrate
python manage.py runserver
```

To exit the virtual env: `exit`

**Frontend** — in a separate terminal:

```sh
cd frontend
npm run dev
```

</details>

### Log in

Navigate to http://localhost:5173 and log in with the default credentials:

- **Username:** `admin`
- **Password:** `passhorarios`

---

## Mirror service

The mirror service creates a local snapshot of the FEUP schedule website so the ingestion pipeline can run without network access to the institution.

<details>
<summary><strong>Docker</strong></summary>

```sh
# Start only the mirror
make mirror

# Start the full stack including the mirror
make dev-mirror
```

</details>

<details>
<summary><strong>Bare-metal</strong></summary>

Requires `wget` and Python 3 to be installed.

```sh
# From the project root
bash scripts/serve-mirror-site.sh
```

This will download the site if it hasn't been mirrored yet, then serve it at http://localhost:8080.

To force a fresh download:

```sh
bash scripts/create-mirror-site.sh
bash scripts/serve-mirror-site.sh
```

</details>

The mirror is accessible at http://localhost:8080 from the host.

When creating a project in the application, set the schedule URL to:

- **Docker:** `http://mirror:8080` — the backend reaches the mirror over the internal Docker network
- **Bare-metal:** `http://localhost:8080`

---

## Useful commands

| Command             | Description                                 |
| ------------------- | ------------------------------------------- |
| `make dev`          | Build and start frontend + backend          |
| `make dev-mirror`   | Build and start frontend + backend + mirror |
| `make mirror`       | Start only the mirror service               |
| `make clean-db`     | Delete all local SQLite databases           |
| `make clean-mirror` | Delete the downloaded mirror data           |
