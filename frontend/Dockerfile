FROM nginx:alpine

# Copia la configuración personalizada de nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copia los archivos estáticos del frontend (ajusta la ruta si usas otra carpeta)
COPY ./dist /usr/share/nginx/html
