import secrets
import os
import re
from flask import Flask, render_template, request, redirect, url_for, flash, session  # type: ignore
from init_db import init_database as init_db
from db_logic import insert_user, clear_db, check_user_login
from logging_config import setup_logging, attach_request_logging # type: ignore
from werkzeug.security import generate_password_hash  # type: ignore

DB_PATH = '/app/db/database.db'  # ruta usada también en db_logic (mantener si se requiere en otro lugar)

def main():
    init_db()
    app = Flask(__name__)

    setup_logging(app)
    attach_request_logging(app)

    # Read SECRET_KEY from environment in production. Fallback to a generated key only for local dev.
    app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    from datetime import timedelta
    app.permanent_session_lifetime = timedelta(days=7)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/register")
    def register():
        return render_template("register.html")

    @app.route("/login")
    def login():
        return render_template("login.html")

    @app.route("/dashboard")
    def dashboard():
        if 'user_id' not in session or 'username' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        return render_template("dashboard.html", username=session['username'])

    @app.route("/logout")
    def logout():
        session.clear()
        flash('Sesión cerrada exitosamente', 'success')
        return redirect(url_for('index'))

    @app.route("/clear_db")
    def clear_database():
        if clear_db():
            flash('Base de datos limpiada exitosamente', 'success')
        else:
            flash('Error al limpiar la base de datos', 'error')
        return redirect(url_for('dashboard'))

    @app.route("/register_submit", methods=["POST"])
    def register_submit():
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('register'))

        # Password strength: mínimo 8 caracteres, al menos 1 mayúscula y 1 número
        pw_pattern = re.compile(r'^(?=.*[A-Z])(?=.*\d).{8,}$')
        if not pw_pattern.match(password):
            flash('La contraseña debe tener al menos 8 caracteres, una mayúscula y un número', 'error')
            return redirect(url_for('register'))

        hash_pw = generate_password_hash(password)  # se guarda el hash

        if insert_user(username, email, hash_pw):
            flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error: El email ya existe o hubo un problema', 'error')
            return redirect(url_for('register'))

    @app.route("/login_submit", methods=["POST"])
    def login_submit():
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email y contraseña son obligatorios', 'error')
            return redirect(url_for('login'))

        user = check_user_login(email, password)
        if user:
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['nombre']
            flash(f'¡Bienvenido {user["nombre"]}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Email o contraseña incorrectos', 'error')
        return redirect(url_for('login'))

    return app

if __name__ == "__main__":
    app = main()
    app.run(host="0.0.0.0", port=3000, debug=True)