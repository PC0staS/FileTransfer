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
            password TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente")

if __name__ == "__main__":
    init_database()
