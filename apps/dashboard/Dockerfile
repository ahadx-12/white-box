FROM node:20-alpine

WORKDIR /app

# Copy only the dashboard package files first (for caching)
COPY apps/dashboard/package.json apps/dashboard/package-lock.json ./
RUN npm ci

# Copy the dashboard source
COPY apps/dashboard ./

RUN npm run build

EXPOSE 3000
CMD ["sh", "-c", "npm run start -- -p ${PORT:-3000} -H 0.0.0.0"]
