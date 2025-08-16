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
    if status not in {'activo', 'rechazado', 'pendiente'}:
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
