FROM node:18-alpine

WORKDIR /app

# Copy all package files and config files
COPY package*.json ./
COPY tsconfig.json ./
COPY services/architecture-analyzer/package*.json ./services/architecture-analyzer/
COPY shared ./shared

# Install dependencies for the entire workspace
RUN npm ci

# Copy source code
COPY services/architecture-analyzer ./services/architecture-analyzer

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Create logs directory
RUN mkdir -p services/architecture-analyzer/logs && chown -R nodejs:nodejs services/architecture-analyzer/logs

USER nodejs

EXPOSE 3003

CMD ["npm", "start", "-w", "services/architecture-analyzer"]
