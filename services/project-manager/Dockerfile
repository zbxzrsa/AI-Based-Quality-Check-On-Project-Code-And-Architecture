FROM node:18-alpine

WORKDIR /app

# Copy all package files and config files
COPY package*.json ./
COPY tsconfig.json ./
COPY services/project-manager/package*.json ./services/project-manager/
COPY shared ./shared

# Install dependencies for the entire workspace
RUN npm ci

# Copy source code
COPY services/project-manager ./services/project-manager

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Create logs directory
RUN mkdir -p services/project-manager/logs && chown -R nodejs:nodejs services/project-manager/logs

USER nodejs

EXPOSE 3005

CMD ["npm", "start", "-w", "services/project-manager"]
