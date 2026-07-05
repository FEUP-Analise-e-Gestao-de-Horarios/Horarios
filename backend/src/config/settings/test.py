from .base import *

# A fixed, insecure key so the test suite never depends on the environment.
SECRET_KEY = "test-insecure-key-not-for-prod"

DEBUG = False

# Deliberately NOT importing dev.py: it adds the dev-only ``livereload`` app and
# middleware and depends on the ``.env`` symlink. Tests must run against a clean,
# self-contained configuration derived only from ``base.py``.
