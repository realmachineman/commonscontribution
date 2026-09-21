FROM node:22-bookworm AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY --from=frontend /app/dist ./dist
COPY server.py ./
COPY config ./config
ENV HOST=0.0.0.0
EXPOSE 8000
CMD ["python3","server.py"]
