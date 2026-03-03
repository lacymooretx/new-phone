# Stage 1: Build
FROM node:22-alpine AS build
WORKDIR /app
ARG VITE_GOOGLE_MAPS_API_KEY=""
ENV VITE_GOOGLE_MAPS_API_KEY=${VITE_GOOGLE_MAPS_API_KEY}
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:1.27-alpine
RUN apk upgrade --no-cache
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh

# Run as non-root nginx user
RUN chmod +x /docker-entrypoint.sh && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid
USER nginx

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
