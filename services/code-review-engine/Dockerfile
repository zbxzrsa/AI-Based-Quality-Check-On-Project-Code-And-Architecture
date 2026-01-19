FROM node:18-alpine

WORKDIR /app

# Copy all package files and config files
COPY package*.json ./
COPY tsconfig.json ./
COPY services/code-review-engine/package*.json ./services/code-review-engine/
COPY shared ./shared

# Install dependencies for the entire workspace
RUN npm ci

# Copy source code
COPY services/code-review-engine ./services/code-review-engine

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Create logs directory
RUN mkdir -p services/code-review-engine/logs && chown -R nodejs:nodejs services/code-review-engine/logs

USER nodejs

EXPOSE 3002

CMD ["npm", "start", "-w", "services/code-review-engine"]
