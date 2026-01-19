FROM node:18-alpine

WORKDIR /app

# Copy all package files and config files
COPY package*.json ./
COPY tsconfig.json ./
COPY services/agentic-ai/package*.json ./services/agentic-ai/
COPY shared ./shared

# Install dependencies for the entire workspace
RUN npm ci

# Copy source code
COPY services/agentic-ai ./services/agentic-ai

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# Create logs directory
RUN mkdir -p services/agentic-ai/logs && chown -R nodejs:nodejs services/agentic-ai/logs

USER nodejs

EXPOSE 3004

CMD ["npm", "start", "-w", "services/agentic-ai"]
