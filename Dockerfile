# Build and run the web service on Railway via Docker
FROM node:20-alpine AS base

ENV NODE_ENV=production
WORKDIR /app

# Install dependencies first for better layer caching
COPY web/package*.json ./
RUN npm ci --omit=dev

# Copy application source
COPY web/ .

# Default port (Railway will provide PORT)
ENV PORT=10000

# Start the web server
CMD ["node", "server.js"]
