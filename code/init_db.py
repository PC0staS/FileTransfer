import sqlite3
import os

def init_database():
    """Inicializa la base de datos si no existe"""
    db_path = '/app/db/database.db'
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Conectar (crea la DB si no existe)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Crear tablas de ejemplo
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migraciones ligeras para versiones anteriores (añadir columnas si faltan)
    try:
        cursor.execute("PRAGMA table_info(usuarios)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'estado' not in cols:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN estado TEXT NOT NULL DEFAULT 'pendiente'")
        if 'fecha_registro' not in cols:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except Exception as e:
        print(f"Aviso migración columnas: {e}")
    
    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente")

if __name__ == "__main__":
    init_database()
