# Development-focused Dockerfile for Next.js frontend

FROM node:22-alpine3.21

RUN apk upgrade --no-cache && apk add --no-cache dumb-init curl

WORKDIR /app

# Install dependencies first for better layer caching
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# Copy app source
COPY . .

ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=6066

EXPOSE 6066

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:6066/api/health || exit 1

ENTRYPOINT ["dumb-init", "--"]
CMD ["npm", "run", "dev"]
