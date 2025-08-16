"""
Módulo para manejo de uploads de archivos
"""
import os
import re
import json
from datetime import datetime, timedelta
from flask import flash, session, request, jsonify, send_file # type: ignore

# Configuración de uploads
UPLOAD_FOLDER = '/app/uploads'
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'zip', 'rar', '7z', 'tar', 'gz',
    'mp3', 'mp4', 'avi', 'mov', 'mkv',
    'py', 'js', 'html', 'css', 'json', 'xml'
}

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
    """Manejar la subida de un archivo"""
    if not file or file.filename == '':
        return {'error': 'No se seleccionó ningún archivo'}, 400
    
    if not allowed_file(file.filename):
        return {'error': f'Tipo de archivo no permitido. Extensiones permitidas: {", ".join(sorted(ALLOWED_EXTENSIONS))}'}, 400
    
    try:
        original_filename = file.filename
        filename = secure_filename(original_filename)
        # Añadir timestamp para evitar colisiones
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        user_dir = get_user_upload_dir(user_id)
        file_path = os.path.join(user_dir, filename)
        
        file.save(file_path)
        
        # Guardar metadatos con fecha de expiración
        save_file_metadata(user_id, filename, original_filename)
        
        return {
            'success': True,
            'message': f'Archivo "{original_filename}" subido exitosamente. Expira en 5 días.',
            'filename': filename,
            'size': format_file_size(os.path.getsize(file_path))
        }, 200
        
    except Exception as e:
        return {'error': f'Error al subir el archivo: {str(e)}'}, 500

def handle_file_download(filename, user_id):
    """Manejar la descarga de un archivo"""
    user_dir = get_user_upload_dir(user_id)
    file_path = os.path.join(user_dir, filename)
    
    if not os.path.exists(file_path):
        return None
    
    # Obtener nombre original sin timestamp
    display_name = filename.split('_', 3)[-1] if '_' in filename else filename
    
    return send_file(file_path, as_attachment=True, download_name=display_name)

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
