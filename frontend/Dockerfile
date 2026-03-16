FROM node:24-alpine

WORKDIR /workspace

COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY frontend/ ./frontend/

WORKDIR /workspace/frontend
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
