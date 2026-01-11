# Usamos una imagen oficial de Python como base
FROM python:3.11-slim

# Evita que Python escriba archivos .pyc
ENV PYTHONDONTWRITEBYTECODE 1
# Asegura que la salida de Python se muestre en la terminal sin buffer
ENV PYTHONUNBUFFERED 1

# Creamos un directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos las dependencias
# Copiamos primero el archivo de requerimientos para aprovechar el cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código de la aplicación al directorio de trabajo
COPY . .