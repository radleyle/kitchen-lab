# Recipe for the frontend lunchbox (development version).
FROM node:22-slim

WORKDIR /app

# Same caching trick as the backend: install deps first, copy code after.
COPY package.json package-lock.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
