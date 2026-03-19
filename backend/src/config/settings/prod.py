from .base import *

DEBUG = False

# WhiteNoise: serve compressed + fingerprinted static files
# The Manifest variant embeds content hashes in filenames so browsers cache forever
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
