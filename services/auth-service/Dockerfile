FROM node:18-alpine

WORKDIR /app

# Copy all package files and config files
COPY package*.json ./
COPY tsconfig.json ./
COPY services/auth-service/package*.json ./services/auth-service/
COPY services/auth-service/tsconfig.json ./services/auth-service/
COPY shared ./shared

# Install dependencies for the entire workspace
RUN npm ci

# Copy source code
COPY services/auth-service ./services/auth-service

# Build only the auth-service
RUN npm run build -w services/auth-service

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Create logs directory
RUN mkdir -p services/auth-service/logs && chown -R nodejs:nodejs services/auth-service/logs

USER nodejs

EXPOSE 3001

CMD ["npm", "start", "-w", "services/auth-service"]