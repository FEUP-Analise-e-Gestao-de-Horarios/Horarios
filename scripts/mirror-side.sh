#!/bin/bash
wget --mirror --convert-links --adjust-extension --page-requisites --no-parent \
  --no-host-directories --cut-dirs=3 \
  -e robots=off \
  -P ./site-mirror https://fe.up.pt/horarios/25_26_2s/final/

# Commands to format html in case you need
# find site-mirror/ -type f -name "*.html" -exec sed -i 's|</br>|<br>|g' {} +
# npx prettier --write "site-mirror/**/*"
