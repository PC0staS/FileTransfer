import sqlite3
from typing import Optional, Dict
from werkzeug.security import check_password_hash  # type: ignore

DB_PATH = '/app/db/database.db'


def insert_user(username, email, password):
    """Inserta un nuevo usuario en la base de datos."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO usuarios (nombre, email, password) VALUES (?, ?, ?)',
            (username, email, password),
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
        cursor.execute('SELECT id, nombre, password FROM usuarios WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        user_id, nombre, stored_hash = row
        if check_password_hash(stored_hash, password_plain):
            return {"id": user_id, "nombre": nombre}
        return None
    except Exception as e:
        print(f"Error en login: {e}")
        return None
