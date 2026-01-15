# Simple development Dockerfile for Next.js
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code
COPY . .

# Build step is optional for dev, but we'll include it to verify code
# ENV NEXT_TELEMETRY_DISABLED 1
# RUN npm run build

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Use the dev script by default
CMD ["npm", "run", "dev"]
