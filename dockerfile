FROM ubuntu:22.04
# Crear estructura de carpetas
WORKDIR /app
RUN mkdir -p /app/code /app/db /app/uploads
WORKDIR /app/code

RUN apt update && apt install -y python3 python3-venv sqlite3

# Crear entorno virtual en /app/code/.venv
RUN python3 -m venv .venv

# Copiar requirements y luego instalar dependencias usando el venv
COPY code/requirements.txt ./
RUN .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements.txt

ENV PATH="/app/code/.venv/bin:$PATH"
# Copiar el resto de la aplicación (code y db)
COPY code/ ./
WORKDIR /app
COPY db/ ./db/

EXPOSE 3000

# Comando por defecto: usar Gunicorn con wsgi:app desde /app/code
WORKDIR /app/code
CMD ["gunicorn", "-b", "0.0.0.0:3000", "wsgi:app"]

