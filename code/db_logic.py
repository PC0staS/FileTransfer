import sqlite3
from typing import Optional, Dict, List
from werkzeug.security import check_password_hash  # type: ignore

DB_PATH = '/app/db/database.db'


def insert_user(username, email, password):
    """Inserta un nuevo usuario estado pendiente por defecto."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO usuarios (nombre, email, password, estado) VALUES (?, ?, ?, ?)',
            (username, email, password, 'pendiente'),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False  # Email ya existe
    except Exception as e:
        print(f"Error: {e}")
        return False


def clear_db():
    """Elimina todos los usuarios de la base de datos."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM usuarios')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error al limpiar la base de datos: {e}")
        return False


def check_user_login(email: str, password_plain: str) -> Optional[Dict[str, str]]:
    """Valida credenciales. Devuelve dict con id y nombre si ok, si no None.

    Busca por email, recupera hash y verifica con check_password_hash.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, nombre, password, estado FROM usuarios WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        user_id, nombre, stored_hash, estado = row
        if estado != 'activo':
            return None
        if check_password_hash(stored_hash, password_plain):
            return {"id": user_id, "nombre": nombre}
        return None
    except Exception as e:
        print(f"Error en login: {e}")
        return None


def get_pending_users() -> List[Dict[str, str]]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, email, estado FROM usuarios WHERE estado='pendiente'")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "nombre": r[1], "email": r[2], "estado": r[3]} for r in rows]
    except Exception as e:
        print(f"Error obteniendo pendientes: {e}")
        return []


def set_user_status(user_id: int, status: str) -> bool:
    if status not in {'activo', 'rechazado', 'pendiente', 'suspendido'}:
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE usuarios SET estado=? WHERE id=?', (status, user_id))
        conn.commit()
        ok = cursor.rowcount > 0
        conn.close()
        return ok
    except Exception as e:
        print(f"Error actualizando estado: {e}")
        return False


def get_user_by_id(user_id: int) -> Optional[Dict[str, str]]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, nombre, email, estado FROM usuarios WHERE id=?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {"id": row[0], "nombre": row[1], "email": row[2], "estado": row[3]}
    except Exception as e:
        print(f"Error get_user_by_id: {e}")
        return None


def get_all_users(search: str = "", estado_filter: str = "") -> List[Dict]:
    """Obtiene todos los usuarios con filtros opcionales."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Query simplificado - primero obtener usuarios
        query = "SELECT id, nombre, email, estado, fecha_registro FROM usuarios WHERE 1=1"
        params = []
        
        # Filtros
        if search:
            query += " AND (nombre LIKE ? OR email LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
            
        if estado_filter:
            query += " AND estado = ?"
            params.append(estado_filter)
            
        query += " ORDER BY fecha_registro DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        users = []
        for row in rows:
            # Contar archivos para cada usuario (si la tabla existe)
            try:
                cursor.execute("SELECT COUNT(*) FROM archivos WHERE user_id = ? AND (deleted_at IS NULL OR deleted_at = '')", (row[0],))
                num_archivos = cursor.fetchone()[0]
            except:
                # Si la tabla archivos no existe, poner 0
                num_archivos = 0
                
            users.append({
                "id": row[0],
                "nombre": row[1],
                "email": row[2],
                "estado": row[3],
                "fecha_registro": row[4],
                "num_archivos": num_archivos
            })
        
        conn.close()
        return users
    except Exception as e:
        print(f"Error get_all_users: {e}")
        return []


def get_user_stats() -> Dict[str, int]:
    """Obtiene estadísticas de usuarios y archivos."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Conteo por estado
        cursor.execute("SELECT estado, COUNT(*) FROM usuarios GROUP BY estado")
        estado_counts = dict(cursor.fetchall())
        
        # Total de archivos (si la tabla existe)
        try:
            cursor.execute("SELECT COUNT(*) FROM archivos WHERE deleted_at IS NULL OR deleted_at = ''")
            total_archivos = cursor.fetchone()[0]
        except:
            total_archivos = 0
        
        conn.close()
        
        return {
            "activos": estado_counts.get("activo", 0),
            "pendientes": estado_counts.get("pendiente", 0), 
            "rechazados": estado_counts.get("rechazado", 0),
            "total_archivos": total_archivos
        }
    except Exception as e:
        print(f"Error get_user_stats: {e}")
        return {"activos": 0, "pendientes": 0, "rechazados": 0, "total_archivos": 0}


def delete_user_completely(user_id: int) -> bool:
    """Elimina un usuario y todos sus archivos asociados."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Primero eliminar archivos de la tabla
        cursor.execute('DELETE FROM archivos WHERE user_id = ?', (user_id,))
        
        # Luego eliminar el usuario
        cursor.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        
        # También eliminar archivos físicos del disco
        if success:
            import os
            import shutil
            user_dir = f"/app/uploads/user_{user_id}"
            if os.path.exists(user_dir):
                try:
                    shutil.rmtree(user_dir)
                except Exception as e:
                    print(f"Error eliminando directorio {user_dir}: {e}")
        
        return success
    except Exception as e:
        print(f"Error delete_user_completely: {e}")
        return False
