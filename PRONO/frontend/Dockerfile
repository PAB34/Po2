FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY styles.css /usr/share/nginx/html/styles.css
COPY app.js /usr/share/nginx/html/app.js
COPY sw.js /usr/share/nginx/html/sw.js
COPY manifest.json /usr/share/nginx/html/manifest.json
COPY icons /usr/share/nginx/html/icons
