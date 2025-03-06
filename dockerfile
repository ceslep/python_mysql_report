# Usa Python 3.11.9-slim como imagen base
FROM python:3.11.9-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo de requerimientos e instala las dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el contenido del proyecto al contenedor
COPY . /app

# Expone el puerto 5000
EXPOSE 5000

# Ejecuta la aplicación usando gunicorn
# Se asume que en server.py tienes definido el objeto Flask como 'app'
CMD ["gunicorn", "-b", "0.0.0.0:5000", "server:app"]
