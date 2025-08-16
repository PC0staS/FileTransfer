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
