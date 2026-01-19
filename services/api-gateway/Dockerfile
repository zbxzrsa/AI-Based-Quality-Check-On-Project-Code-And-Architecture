FROM node:18-alpine

WORKDIR /app

# Copy all package files and config files
COPY package*.json ./
COPY tsconfig.json ./
COPY services/api-gateway/package*.json ./services/api-gateway/
COPY services/api-gateway/tsconfig.json ./services/api-gateway/
COPY shared ./shared

# Install dependencies for the entire workspace
RUN npm ci

# Copy source code
COPY services/api-gateway ./services/api-gateway

# Build only the api-gateway
RUN npm run build -w services/api-gateway

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Create logs directory
RUN mkdir -p services/api-gateway/logs && chown -R nodejs:nodejs services/api-gateway/logs

USER nodejs

EXPOSE 3000

CMD ["npm", "start", "-w", "services/api-gateway"]