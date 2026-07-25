FROM node:26-alpine

WORKDIR /workspace/frontend

COPY package*.json .npmrc ./
RUN npm ci --include=optional

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
