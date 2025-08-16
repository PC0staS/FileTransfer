# FileTransfer

Servidor de intercambio de archivos ligero usando Flask.

Características principales
- Autenticación básica de usuarios.
- Subida mediante formulario o drag & drop con barra de progreso (AJAX).
- Soporta cualquier tipo de archivo (sin limitación de extensión ni restricciones de tamaño).
- Almacenamiento por usuario en `uploads/user_{id}/`.
- Enlaces de descarga directos y botón "copiar enlace" con fallback para macOS/Safari.
- Expiración automática de archivos: 5 días desde la subida (se puede cambiar fácilmente en `code/uploads.py`).
- Base de datos SQLite persistente en `db/database.db`.

Estructura del repositorio
```
/ (repo root)
  docker-compose.yml
  Dockerfile
  code/
    app.py
    uploads.py
    db_logic.py
    init_db.py
    wsgi.py
    templates/
    static/
  db/
    database.db
  uploads/  (mount/volume for file storage)
```

Requisitos
- Docker / Docker Compose (recomendado)
- O Python 3.8+ y pip si quieres ejecutar sin Docker

Quick start (con Docker Compose)

Abre PowerShell en la carpeta del repo y ejecuta:

```powershell
# Construir y levantar servicios en background
docker-compose up --build -d

# Ver logs
docker-compose logs -f
```

Accede a http://localhost:3000

Ejecutar localmente sin Docker (desarrollo)

```powershell
# Crear entorno virtual
cd .\code
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Asegurar SECRET_KEY persistente
# Genera un secreto y guárdalo en la raíz del repo como .secret_key (una sola línea)
python - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
# Copia el valor y pégal o crea el archivo .secret_key con ese contenido

# Lanzar la app
$env:FLASK_APP = 'app.py'
python app.py
```

Variables / archivos importantes
- `.secret_key` (en la raíz del repo): valor persistente del `SECRET_KEY` de Flask (si no existe, la app intenta leer `.env` o genera uno temporal).
- `db/database.db`: archivo SQLite que guarda usuarios y metadatos.
- `uploads/` (montado en Docker): directorio donde se guardan los archivos por usuario.

Rutas y endpoints relevantes
- `/` - Página de inicio
- `/register`, `/login`, `/logout` - Autenticación
- `/upload` - UI para subir archivos (drag & drop, multi-file)
- `/dashboard` - Lista y gestión de "Mis archivos"
- `/download/<filename>` - Descarga de archivo
- `/api/upload_progress` - Endpoint AJAX para subir archivos con progreso
- `/api/delete_file` - Eliminar archivo (AJAX)
- `/api/cleanup_expired` - Forzar limpieza de archivos expirados para el usuario actual

Comportamiento de subida
- Cualquier extensión está permitida. El servidor añade un timestamp al nombre para evitar colisiones.
- Metadatos por archivo (original name, fecha de subida, fecha de expiración) se guardan como `.{filename}.meta` en la misma carpeta del usuario.
- La expiración por defecto es 5 días. Cambia `timedelta(days=5)` en `code/uploads.py` si quieres otro periodo.

Barra de progreso y compatibilidad
- La UI usa XHR y eventos `progress` + `loadend` para que la barra llegue al 100% incluso cuando el evento `progress` no marca exactamente 100%.
- El botón "Copiar enlace" usa `navigator.clipboard` si está disponible y seguro; si no, usa un fallback con `document.execCommand('copy')` y, en último caso, abre un modal con el enlace para copiar manualmente (esto resuelve problemas en macOS/Safari).

Cambiar la ruta de almacenamiento o la base de datos
- Si usas Docker, ajusta `docker-compose.yml` para montar otros volúmenes.
- Si ejecutas en local, cambia la constante `UPLOAD_FOLDER` en `code/uploads.py` y `DB_PATH` en `code/app.py` si es necesario.

Depuración rápida
- Si las subidas fallan: revisa `docker-compose logs` o los logs del contenedor.
- Si ves problemas con sesiones: confirma que `.secret_key` existe o que `SECRET_KEY` está en el entorno.
- Para verificar importación rápida (desde `code/`):

```powershell
python -c "from uploads import get_user_files; print('OK', callable(get_user_files))"
```

Cómo contribuir
- Haz fork, crea una rama, añade tests si cambias lógica y abre PR.
- Pequeñas mejoras recomendadas: enlaces temporales con tokens, límites opcionales por usuario, limpieza programada con cron o un worker.

Notas finales
- Esta app está pensada para uso en redes locales o como proyecto de aprendizaje. Para producción considera:
  - Usar HTTPS (necesario para la API del portapapeles en navegadores modernos)
  - Autenticación más robusta (hashing, salted passwords ya se usa con werkzeug)
  - Limitar tamaños/escaneo antivirus si aceptas archivos públicos

Si quieres, genero una sección con ejemplos curl para la API o añado un script de limpieza cron para eliminar expirados automáticamente.

---

## Índice ampliado
1. Características
2. Arquitectura y flujo
3. Persistencia y volúmenes
4. Variables de entorno y configuración
5. Integración con Cloudflare Tunnel (dominio propio)
6. Alternativas de exposición (ngrok / Tailscale / Nginx + Certbot)
7. Seguridad y buenas prácticas
8. Personalización (expiración, límites, nombres, UI)
9. Ejemplos API (curl)
10. Automatizar limpieza de expirados (cron)
11. Backup / Restore
12. Troubleshooting

## 2. Arquitectura y flujo
Resumen del ciclo:
1. Usuario se registra (hash de contraseña via `generate_password_hash`).
2. Al iniciar sesión se guarda `user_id` y `username` en `session` (cookie firmada con `SECRET_KEY`).
3. Subida: JS -> `/api/upload_progress` (XHR) -> `handle_file_upload` guarda archivo en `uploads/user_<id>/` + crea metadata `.<nombre>.meta`.
4. Dashboard lee `get_user_files`, formatea tamaños, iconos y calcula días restantes.
5. Descarga: ahora es pública (`/download/<filename>`) busca en el dueño y, si no, en todos los usuarios (salta expirados).
6. Limpieza: al listar se ejecuta `cleanup_expired_files(user_id)`; opcional endpoint manual `/api/cleanup_expired`.

## 3. Persistencia y volúmenes
En `docker-compose.yml`:
```
volumes:
  - ./db:/app/db          # SQLite persistente
  - ./uploads:/app/uploads # Archivos de usuario
```
Si pierdes usuarios tras reiniciar contenedor:
* Asegura que la carpeta `./db` exista antes del `up`.
* Comprueba permisos (UID dentro del contenedor pueda escribir). Ej: `chmod 755 db`.
* Verifica que no montas un volumen vacío encima después (evitar nombres de volumen anónimos).

## 4. Variables de entorno y configuración
| Variable        | Uso                                   | Default / Comentario |
|-----------------|----------------------------------------|----------------------|
| SECRET_KEY      | Firmar cookies Flask                   | Busca `.env` / `.secret_key` |
| FLASK_ENV       | Modo (production/development)          | production            |
| PYTHONUNBUFFERED| Logs inmediatos                        | 1                    |

Modificar expiración: en `uploads.py` busca `timedelta(days=5)`.

## 5. Integración con Cloudflare Tunnel (dominio propio)
Recomendado para usar `https://files.tu-dominio.com` sin abrir puertos.

### Requisitos
* Dominio gestionado en Cloudflare (nameservers apuntando allí).
* Raspberry (o servidor) con acceso a Internet.

### Pasos
1. Instalar `cloudflared` (ARM64 ejemplo):
  ```bash
  wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb -O cloudflared.deb
  sudo apt install ./cloudflared.deb
  ```
2. Login:
  ```bash
  cloudflared tunnel login
  ```
3. Crear túnel:
  ```bash
  cloudflared tunnel create filetransfer
  # Guarda el UUID que imprime
  ```
4. Archivo de config `~/.cloudflared/config.yml`:
  ```yaml
  tunnel: <TUNNEL-UUID>
  credentials-file: /home/pi/.cloudflared/<TUNNEL-UUID>.json
  ingress:
    - hostname: files.tu-dominio.com
     service: http://localhost:3000
    - service: http_status:404
  ```
5. Crear DNS (Cloudflare lo añade automáticamente):
  ```bash
  cloudflared tunnel route dns filetransfer files.tu-dominio.com
  ```
6. Probar:
  ```bash
  cloudflared tunnel run filetransfer
  ```
7. Servicio systemd (si el instalador no lo crea):
  ```bash
  sudo tee /etc/systemd/system/cloudflared-filetransfer.service > /dev/null <<'EOF'
  [Unit]
  Description=Cloudflare Tunnel FileTransfer
  After=network-online.target
  [Service]
  User=pi
  ExecStart=/usr/local/bin/cloudflared tunnel run filetransfer
  Restart=on-failure
  RestartSec=5
  [Install]
  WantedBy=multi-user.target
  EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now cloudflared-filetransfer.service
  ```

### Notas
* TLS automático por Cloudflare.
* Puedes restringir acceso con Cloudflare Access (Zero Trust) si el sitio no debe ser totalmente público.
* Si cambias puerto interno, actualiza `service: http://localhost:<puerto>`.

## 6. Alternativas de exposición
| Método       | Público | TLS | Persistencia URL | Observaciones |
|--------------|---------|-----|------------------|---------------|
| Cloudflare   | Sí      | Sí  | Alta             | Sin abrir puertos |
| ngrok        | Sí      | Sí  | Baja (free)      | Subdominio aleatorio gratis |
| Tailscale    | Privado | N/A | Alta             | Acceso tipo VPN |
| Nginx+Certbot| Sí      | Sí  | Alta             | Requiere abrir 80/443 |

## 7. Seguridad y buenas prácticas
* Cambia el `SECRET_KEY` y mantenlo fuera de Git.
* Considera añadir límite de tamaño (middleware) si usuarios externos suben archivos.
* Añade validación antivirus (ClamAV) si vas a compartir públicamente.
* Habilita HTTPS siempre (Cloudflare o reverse proxy).
* Revisa logs de acceso para detectar abuso.

## 8. Personalización
* Cambiar expiración: `save_file_metadata` -> `timedelta(days=5)`.
* Desactivar expiración: guarda `expires_date = None` y ajusta comprobaciones.
* UI: modifica `templates/dashboard.html` y `templates/upload.html`.
* Iconos: tabla en `get_file_icon` (añade extensiones).
* Descargar sin sesión ya activado (`handle_public_download`). Para desactivar, vuelve a exigir sesión en la ruta.

## 9. API (curl)
Subida (sesión iniciada; requiere cookie de login):
```bash
curl -F "file=@/ruta/miarchivo.txt" http://localhost:3000/api/upload_progress
```
Eliminar archivo:
```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"filename":"20240101_120000_miarchivo.txt"}' \
  http://localhost:3000/api/delete_file
```
Limpiar expirados:
```bash
curl -X POST http://localhost:3000/api/cleanup_expired
```
Descarga pública:
```bash
curl -O http://localhost:3000/download/20240101_120000_miarchivo.txt
```

## 10. Limpieza programada (cron)
Ejemplo: ejecutar cada noche una limpieza global (simple script Python que recorra `uploads/`). Crea `scripts/cleanup_all.py` (no incluido aquí) y añade en crontab:
```
0 2 * * * /usr/bin/python3 /ruta/proyecto/scripts/cleanup_all.py >> /var/log/filetransfer_cleanup.log 2>&1
```

## 11. Backup / Restore
Backup:
```bash
tar czf backup_$(date +%Y%m%d).tgz db/database.db uploads/
```
Restore:
```bash
tar xzf backup_YYYYMMDD.tgz -C .
```
Recomendado: snapshots periódicos + sincronizar `uploads/` a almacenamiento externo.

## 12. Troubleshooting
| Problema | Causa común | Solución |
|----------|-------------|----------|
| Usuarios desaparecen | Volumen `./db` no montado / carpeta vacía | Verifica bind mount en compose |
| SECRET_KEY cambia | No existe `.env` ni `.secret_key` | Crear uno fijo y reiniciar |
| Barra progreso no llega 100% | Evento `progress` no cierra exacto | Implementado `loadend`; refrescar caché |
| Copiar enlace falla en Safari | Restricciones clipboard | Usa fallback modal (ya incluido) |
| Archivo no se descarga público | Expiró o nombre distinto | Verificar metadatos y días restantes |

Logs dentro de Docker:
```bash
docker-compose logs -f web
```

Reconstruir sin cache:
```bash
docker-compose build --no-cache web && docker-compose up -d
```

---
Si necesitas una guía específica para ngrok/Tailscale u otro reverse proxy, pídelo y la añado.
