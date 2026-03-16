FROM python:3-slim

RUN apt-get update && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY  scripts/ ./scripts/

EXPOSE 8080
CMD ["bash", "scripts/serve-mirror-site.sh"]
