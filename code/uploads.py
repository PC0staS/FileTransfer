"""
Módulo para manejo de uploads de archivos
"""
import os
import re
import json
from datetime import datetime, timedelta
from flask import flash, session, request, jsonify, send_file, Response # type: ignore
import logging

# Configuración de uploads
UPLOAD_FOLDER = '/app/uploads'
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'zip', 'rar', '7z', 'tar', 'gz',
    'mp3', 'mp4', 'avi', 'mov', 'mkv',
    'py', 'js', 'html', 'css', 'json', 'xml'
}

# ------------------------- Subidas Resumibles (Chunks) -------------------------
import uuid

CHUNK_THRESHOLD = int(os.environ.get('CHUNK_UPLOAD_THRESHOLD_MB', '512')) * 1024 * 1024  # >512MB usa chunks
DEFAULT_CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE_MB', '64')) * 1024 * 1024  # 64MB

def _resumable_meta_path(user_id, upload_id):
    return os.path.join(get_user_upload_dir(user_id), f".upload_{upload_id}.json")

def _temp_file_path(user_id, upload_id):
    return os.path.join(get_user_upload_dir(user_id), f".upload_{upload_id}.part")

def init_resumable_upload(user_id, original_name, total_size):
    """Crear/recuperar estado de una subida resumible.
    Retorna dict con upload_id, received_bytes, chunk_size.
    """
    upload_id = uuid.uuid4().hex
    meta = {
        'upload_id': upload_id,
        'original_name': secure_filename(original_name),
        'display_name': original_name,
        'total_size': total_size,
        'received_bytes': 0,
        'chunk_size': DEFAULT_CHUNK_SIZE,
        'started_at': datetime.now().isoformat()
    }
    with open(_resumable_meta_path(user_id, upload_id), 'w', encoding='utf-8') as f:
        json.dump(meta, f)
    return meta

def load_resumable_meta(user_id, upload_id):
    path = _resumable_meta_path(user_id, upload_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def save_resumable_meta(user_id, meta):
    path = _resumable_meta_path(user_id, meta['upload_id'])
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(meta, f)
    except Exception:
        pass

def append_chunk(user_id, upload_id, chunk_index, chunk_data, total_chunks=None):
    meta = load_resumable_meta(user_id, upload_id)
    if not meta:
        return {'error': 'Upload no encontrada'}, 404
    temp_path = _temp_file_path(user_id, upload_id)

    # Validar consistencia de tamaño ya recibido vs índice
    expected_index = meta['received_bytes'] // meta['chunk_size']
    if chunk_index != expected_index:
        return {
            'error': 'Índice de chunk inesperado',
            'expected_index': expected_index,
            'received_bytes': meta['received_bytes']
        }, 409

    with open(temp_path, 'ab', buffering=8*1024*1024) as f:
        f.write(chunk_data)
    meta['received_bytes'] += len(chunk_data)
    save_resumable_meta(user_id, meta)

    completed = meta['received_bytes'] >= meta['total_size']
    return {
        'success': True,
        'received_bytes': meta['received_bytes'],
        'completed': completed,
        'total_size': meta['total_size']
    }, 200

def finalize_resumable_upload(user_id, upload_id):
    meta = load_resumable_meta(user_id, upload_id)
    if not meta:
        return {'error': 'Upload no encontrada'}, 404
    if meta['received_bytes'] < meta['total_size']:
        return {'error': 'Upload incompleta'}, 400
    temp_path = _temp_file_path(user_id, upload_id)
    if not os.path.exists(temp_path):
        return {'error': 'Archivo temporal no encontrado'}, 404

    # Renombrar a nombre final con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    final_name = timestamp + meta['original_name']
    final_path = os.path.join(get_user_upload_dir(user_id), final_name)
    os.replace(temp_path, final_path)
    save_file_metadata(user_id, final_name, meta['display_name'])

    # Limpiar metadata
    try:
        os.remove(_resumable_meta_path(user_id, upload_id))
    except Exception:
        pass

    return {
        'success': True,
        'filename': final_name,
        'size': format_file_size(meta['total_size']),
        'message': f'Archivo "{meta["display_name"]}" subido exitosamente (chunked).'
    }, 200

def secure_filename(filename):
    """Función para asegurar nombres de archivo"""
    # Remover caracteres peligrosos y mantener solo alfanuméricos, puntos, guiones y guiones bajos
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Evitar nombres que empiecen con punto
    if filename.startswith('.'):
        filename = '_' + filename[1:]
    return filename[:255]  # Limitar longitud

def allowed_file(filename):
    """Verificar si el archivo tiene una extensión permitida"""
    # Ahora permitimos cualquier extensión para subir cualquier tipo de archivo.
    # Conservamos la comprobación mínima de que exista un nombre con punto para mantener consistencia,
    # pero devolvemos True si tiene nombre.
    return bool(filename and filename.strip())

def get_file_icon(filename):
    """Retorna el icono de Bootstrap Icons apropiado para el tipo de archivo"""
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    icon_map = {
        # Documentos
        'pdf': 'bi-file-pdf',
        'doc': 'bi-file-word',
        'docx': 'bi-file-word', 
        'xls': 'bi-file-excel',
        'xlsx': 'bi-file-excel',
        'ppt': 'bi-file-ppt',
        'pptx': 'bi-file-ppt',
        
        # Imágenes
        'png': 'bi-file-image',
        'jpg': 'bi-file-image',
        'jpeg': 'bi-file-image',
        'gif': 'bi-file-image',
        'webp': 'bi-file-image',
        'svg': 'bi-file-image',
        
        # Archivos comprimidos
        'zip': 'bi-file-zip',
        'rar': 'bi-file-zip',
        '7z': 'bi-file-zip',
        'tar': 'bi-file-zip',
        'gz': 'bi-file-zip',
        
        # Multimedia
        'mp3': 'bi-file-music',
        'mp4': 'bi-file-play',
        'avi': 'bi-file-play',
        'mov': 'bi-file-play',
        'mkv': 'bi-file-play',
        
        # Código
        'py': 'bi-file-code',
        'js': 'bi-file-code',
        'html': 'bi-file-code',
        'css': 'bi-file-code',
        'json': 'bi-file-code',
        'xml': 'bi-file-code',
        
        # Texto
        'txt': 'bi-file-text',
    }
    
    return icon_map.get(extension, 'bi-file-earmark')

def format_file_size(size_bytes):
    """Formatear el tamaño del archivo de manera legible"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_user_upload_dir(user_id):
    """Crear y retornar directorio de usuario"""
    user_dir = os.path.join(UPLOAD_FOLDER, f"user_{user_id}")
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_file_metadata_path(user_id, filename):
    """Obtener la ruta del archivo de metadatos"""
    user_dir = get_user_upload_dir(user_id)
    return os.path.join(user_dir, f".{filename}.meta")

def save_file_metadata(user_id, filename, original_name):
    """Guardar metadatos del archivo incluyendo fecha de expiración"""
    try:
        metadata = {
            'original_name': original_name,
            'upload_date': datetime.now().isoformat(),
            'expires_date': (datetime.now() + timedelta(days=5)).isoformat(),
            'user_id': user_id
        }
        
        metadata_path = get_file_metadata_path(user_id, filename)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving metadata: {e}")
        return False

def load_file_metadata(user_id, filename):
    """Cargar metadatos del archivo"""
    try:
        metadata_path = get_file_metadata_path(user_id, filename)
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception:
        return None

def is_file_expired(user_id, filename):
    """Verificar si un archivo ha expirado"""
    metadata = load_file_metadata(user_id, filename)
    if not metadata or 'expires_date' not in metadata:
        return False
    
    try:
        expires_date = datetime.fromisoformat(metadata['expires_date'])
        return datetime.now() > expires_date
    except Exception:
        return False

def cleanup_expired_files(user_id):
    """Limpiar archivos expirados del usuario"""
    user_dir = get_user_upload_dir(user_id)
    cleaned_files = []
    
    if os.path.exists(user_dir):
        for filename in os.listdir(user_dir):
            if filename.startswith('.') and filename.endswith('.meta'):
                continue
                
            file_path = os.path.join(user_dir, filename)
            if os.path.isfile(file_path) and is_file_expired(user_id, filename):
                try:
                    os.remove(file_path)
                    # Remover también el archivo de metadatos
                    metadata_path = get_file_metadata_path(user_id, filename)
                    if os.path.exists(metadata_path):
                        os.remove(metadata_path)
                    cleaned_files.append(filename)
                except Exception as e:
                    print(f"Error removing expired file {filename}: {e}")
    
    return cleaned_files

def get_user_files(user_id):
    """Obtener lista de archivos del usuario con información extendida"""
    # Limpiar archivos expirados primero
    cleanup_expired_files(user_id)
    
    user_dir = get_user_upload_dir(user_id)
    files = []
    if os.path.exists(user_dir):
        for filename in os.listdir(user_dir):
            # Saltar archivos de metadatos
            if filename.startswith('.') and filename.endswith('.meta'):
                continue
                
            file_path = os.path.join(user_dir, filename)
            if os.path.isfile(file_path):
                # Cargar metadatos
                metadata = load_file_metadata(user_id, filename)
                
                file_size = os.path.getsize(file_path)
                display_name = filename
                expires_date = None
                days_left = None
                
                if metadata:
                    display_name = metadata.get('original_name', filename.split('_', 3)[-1] if '_' in filename else filename)
                    if 'expires_date' in metadata:
                        try:
                            expires_date = datetime.fromisoformat(metadata['expires_date'])
                            days_left = max(0, (expires_date - datetime.now()).days)
                        except Exception:
                            pass
                else:
                    # Fallback para archivos sin metadatos
                    display_name = filename.split('_', 3)[-1] if '_' in filename else filename
                
                file_info = {
                    'name': filename,
                    'display_name': display_name,
                    'size': file_size,
                    'size_formatted': format_file_size(file_size),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%d/%m/%Y %H:%M'),
                    'icon': get_file_icon(filename),
                    'extension': filename.rsplit('.', 1)[1].upper() if '.' in filename else 'FILE',
                    'expires_date': expires_date.strftime('%d/%m/%Y') if expires_date else None,
                    'days_left': days_left
                }
                files.append(file_info)
    
    # Ordenar por fecha de modificación (más recientes primero)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(user_dir, x['name'])), reverse=True)
    return files

def handle_file_upload(file, user_id):
    """Manejar la subida de un archivo de forma segura y eficiente para archivos grandes.

    - Usa escritura por chunks para no cargar el archivo completo en memoria.
    - Valida un límite máximo opcional configurable por env MAX_UPLOAD_SIZE (bytes).
    """
    if not file or file.filename == '':
        return {'error': 'No se seleccionó ningún archivo'}, 400

    if not allowed_file(file.filename):
        return {'error': f'Tipo de archivo no permitido. Extensiones permitidas: {", ".join(sorted(ALLOWED_EXTENSIONS))}'}, 400

    # Límite opcional
    try:
        max_size_env = os.environ.get('MAX_UPLOAD_SIZE')
        max_size = int(max_size_env) if max_size_env else None
    except ValueError:
        max_size = None

    file_path = None  # para limpieza segura en caso de excepción
    try:
        original_filename = file.filename
        filename = secure_filename(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename

        user_dir = get_user_upload_dir(user_id)
        file_path = os.path.join(user_dir, filename)

        # Escritura por chunks
        total_written = 0
        logger = logging.getLogger('uploads')
        logger.info("[upload] start user=%s original='%s' target='%s' max_size=%s", user_id, original_filename, filename, format_file_size(max_size) if max_size else 'None')
        chunk_size = 8 * 1024 * 1024  # 8MB
        stream = file.stream  # werkzeug FileStorage stream
        # Prealocación si se conoce el tamaño total (no chunked)
        total_size_header = request.headers.get('X-Upload-Length')
        preallocate = False
        total_int = 0
        if total_size_header and total_size_header.isdigit():
            try:
                total_int = int(total_size_header)
                preallocate = total_int > 0
            except Exception:
                preallocate = False
        with open(file_path, 'wb', buffering=8*1024*1024) as f:
            if preallocate and total_int > 0:
                try:
                    f.truncate(total_int)
                    f.seek(0)
                except Exception:
                    pass
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                total_written += len(chunk)
                # Log cada ~1GB
                if total_written % (1024 * 1024 * 1024) < chunk_size:
                    logger.info("[upload] progress user=%s file='%s' written=%s", user_id, filename, format_file_size(total_written))
            if max_size and total_written > max_size:
                f.close()
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                logger.warning("[upload] aborted user=%s file='%s' reason=max_size_exceeded written=%s limit=%s", user_id, filename, total_written, max_size)
                return {'error': f'Tamaño excede el máximo permitido ({format_file_size(max_size)})', 'error_code': 'MAX_SIZE_EXCEEDED'}, 400

        # Guardar metadatos
        save_file_metadata(user_id, filename, original_filename)
        logger.info("[upload] complete user=%s file='%s' size=%s", user_id, filename, format_file_size(total_written))

        return {
            'success': True,
            'message': f'Archivo "{original_filename}" subido exitosamente. Expira en 5 días.',
            'filename': filename,
            'size': format_file_size(total_written)
        }, 200
    except Exception as e:
        # Intentar limpiar archivo parcial
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        logging.getLogger('uploads').exception(f"[upload] failure user={user_id} original='{getattr(file,'filename',None)}' err={e}")
        return {'error': f'Error al subir el archivo: {str(e)}'}, 500

def handle_file_download(filename, user_id):
    """Manejar la descarga de un archivo"""
    user_dir = get_user_upload_dir(user_id)
    file_path = os.path.join(user_dir, filename)
    
    if not os.path.exists(file_path):
        return None
    
    # Obtener nombre original sin timestamp
    display_name = filename.split('_', 3)[-1] if '_' in filename else filename
    
    return range_or_full_file(file_path, display_name)

def find_file_any_user(filename):
    """Buscar un archivo por nombre dentro de todos los directorios de usuarios.
    Retorna (file_path, display_name) o (None, None) si no se encuentra o expiró.
    """
    if not filename:
        return None, None
    if not os.path.exists(UPLOAD_FOLDER):
        return None, None
    try:
        for entry in os.listdir(UPLOAD_FOLDER):
            if not entry.startswith('user_'):
                continue
            user_dir = os.path.join(UPLOAD_FOLDER, entry)
            if not os.path.isdir(user_dir):
                continue
            candidate = os.path.join(user_dir, filename)
            if os.path.isfile(candidate):
                # determinar user_id
                try:
                    user_id = int(entry.replace('user_',''))
                except Exception:
                    user_id = None
                # Verificar expiración (si hay metadatos)
                if user_id is not None and is_file_expired(user_id, filename):
                    continue
                metadata = load_file_metadata(user_id, filename) if user_id is not None else None
                display_name = metadata.get('original_name') if metadata else (filename.split('_',3)[-1] if '_' in filename else filename)
                return candidate, display_name
    except Exception:
        pass
    return None, None

def handle_public_download(filename):
    """Descarga pública (sin sesión) buscando en todos los usuarios"""
    file_path, display_name = find_file_any_user(filename)
    if not file_path:
        return None
    return range_or_full_file(file_path, display_name)

# ---------------- Descarga con soporte Range (parcial) -----------------
def range_or_full_file(path, download_name):
    """Soporta descargas parciales usando header Range para permitir reanudación y aceleradores.
    """
    try:
        file_size = os.path.getsize(path)
        range_header = request.headers.get('Range', None)
        if not range_header:
            # Respuesta completa normal
            resp = send_file(path, as_attachment=True, download_name=download_name, conditional=True)
            resp.headers['Accept-Ranges'] = 'bytes'
            return resp

        # Parse ejemplo: bytes=START-END
        import re as _re
        m = _re.match(r'bytes=(\d*)-(\d*)', range_header)
        if not m:
            return send_file(path, as_attachment=True, download_name=download_name)
        start_str, end_str = m.groups()
        if start_str == '' and end_str == '':
            return send_file(path, as_attachment=True, download_name=download_name)
        if start_str == '':
            # últimos N bytes
            length = int(end_str)
            start = max(0, file_size - length)
            end = file_size - 1
        else:
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
        if start > end or start >= file_size:
            return Response(status=416, headers={
                'Content-Range': f'bytes */{file_size}'
            })
        # Tamaño de lectura por chunk configurable (default 4MB) para reducir syscalls
        try:
            chunk_mb = int(os.environ.get('RANGE_CHUNK_SIZE_MB', '4'))
        except ValueError:
            chunk_mb = 4
        chunk_size = max(256*1024, min(chunk_mb * 1024 * 1024, 32 * 1024 * 1024))  # entre 256KB y 32MB
        def generate():
            with open(path, 'rb') as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
        rv = Response(generate(), status=206, mimetype='application/octet-stream')
        rv.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        rv.headers['Accept-Ranges'] = 'bytes'
        rv.headers['Content-Length'] = str(end - start + 1)
        rv.headers['Content-Disposition'] = f"attachment; filename={download_name}"
        return rv
    except Exception:
        # Fallback completo si algo falla
        resp = send_file(path, as_attachment=True, download_name=download_name)
        resp.headers['Accept-Ranges'] = 'bytes'
        return resp

def delete_user_file(filename, user_id):
    """Eliminar un archivo del usuario y sus metadatos"""
    user_dir = get_user_upload_dir(user_id)
    file_path = os.path.join(user_dir, filename)
    
    if not os.path.exists(file_path):
        return {'error': 'Archivo no encontrado'}, 404
    
    try:
        os.remove(file_path)
        
        # Eliminar también los metadatos
        metadata_path = get_file_metadata_path(user_id, filename)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
        
        return {'success': True, 'message': 'Archivo eliminado exitosamente'}, 200
    except Exception as e:
        return {'error': f'Error al eliminar el archivo: {str(e)}'}, 500
