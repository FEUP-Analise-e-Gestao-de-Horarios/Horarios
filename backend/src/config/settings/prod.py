from .base import *

DEBUG = False

# WhiteNoise: serve compressed + fingerprinted static files
# Upgrade from CompressedStaticFilesStorage → CompressedManifestStaticFilesStorage
# The Manifest variant embeds content hashes in filenames so browsers cache forever
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
