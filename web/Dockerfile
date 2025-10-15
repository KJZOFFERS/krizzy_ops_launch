# Railway-compatible Dockerfile for web + worker
FROM node:20-slim

WORKDIR /app

# Install system deps used by node modules (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget bash tini && \
    rm -rf /var/lib/apt/lists/*

COPY web/package*.json ./
RUN npm ci --omit=dev

COPY web ./

ENV NODE_ENV=production
ENV PORT=10000
EXPOSE 10000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["npm", "start"]
