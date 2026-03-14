from .base import *

DEBUG = True

# Vite dev server — allow CSRF requests from it
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
]

# Vite forwards X-Forwarded-Host so Django generates correct URLs
# pointing back to :5173 (e.g. in redirects after login)
USE_X_FORWARDED_HOST = True

INSTALLED_APPS += ["livereload"]
MIDDLEWARE += ["livereload.middleware.LiveReloadScript"]
