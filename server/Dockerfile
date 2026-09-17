FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev --ignore-scripts
COPY index.js ./
COPY lib ./lib
COPY routes ./routes
COPY services ./services
ENV HOST=0.0.0.0 PORT=3000
USER node
EXPOSE 3000
CMD ["node","index.js"]
