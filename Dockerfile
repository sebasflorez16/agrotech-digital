# Usa una imagen oficial de Python
FROM python:3.11

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto al contenedor
COPY . /app

# Instala las dependencias
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expone el puerto (ajusta si usas otro)
EXPOSE 8000

# Comando de inicio (ajusta si usas gunicorn)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
