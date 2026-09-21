# Vigie Foncier — site statique (carte + filtres). Les données sont pré-calculées par pipeline/.
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY web/ /usr/share/nginx/html/
# Seules les versions .gz des GeoJSON sont versionnées : nginx les sert telles quelles.
RUN rm -f /usr/share/nginx/html/data/*.geojson
