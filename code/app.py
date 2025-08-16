import secrets
import os
import re
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify  # type: ignore
from init_db import init_database as init_db
from db_logic import insert_user, clear_db, check_user_login, get_pending_users, set_user_status, get_user_by_id
from logging_config import setup_logging, attach_request_logging # type: ignore
from werkzeug.security import generate_password_hash  # type: ignore
from uploads import (
    get_user_files, handle_file_upload, handle_file_download,  # type: ignore
    delete_user_file, allowed_file, handle_public_download # type: ignore
)

DB_PATH = '/app/db/database.db'  # ruta usada también en db_logic (mantener si se requiere en otro lugar)

def main():
    init_db()
    app = Flask(__name__)

    # Seguridad de cookies de sesión
    # Requiere HTTPS en producción para SESSION_COOKIE_SECURE=True
    app.config.update({
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SECURE': True,
        'SESSION_COOKIE_SAMESITE': 'Lax'
    })

    setup_logging(app)
    attach_request_logging(app)

    # Determine SECRET_KEY with priority:
    # 1. environment variable SECRET_KEY
    # 2. .env file at repo root (simple parser)
    # 3. persistent .secret_key file in repo root
    # 4. generated fallback
    secret_key = os.environ.get('SECRET_KEY')
    # attempt to load from .env in repo root (one level up from code/)
    if not secret_key:
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        if k.strip() == 'SECRET_KEY':
                            secret_key = v.strip().strip('"').strip("'")
                            break
        except Exception:
            pass
    if not secret_key:
        secret_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.secret_key'))
        try:
            with open(secret_file, 'r') as f:
                secret_key = f.read().strip()
        except Exception:
            # generate and save
            secret_key = secrets.token_hex(32)
            try:
                # ensure directory exists (should be project root)
                os.makedirs(os.path.dirname(secret_file), exist_ok=True)
                with open(secret_file, 'w') as f:
                    f.write(secret_key)
            except Exception:
                # if saving fails, fall back to in-memory key (dev only)
                pass

    app.secret_key = secret_key
    from datetime import timedelta
    app.permanent_session_lifetime = timedelta(days=7)

    # ---------------- Rate limiting simple (anti fuerza bruta login) ----------------
    from time import time
    failed_logins = {}  # key -> {count, first, blocked_until}

    # Config desde entorno (valores por defecto razonables)
    LOGIN_MAX_ATTEMPTS = int(os.environ.get('LOGIN_MAX_ATTEMPTS', '5'))
    LOGIN_WINDOW_SECONDS = int(os.environ.get('LOGIN_WINDOW_SECONDS', '300'))  # 5 min
    LOGIN_BLOCK_SECONDS = int(os.environ.get('LOGIN_BLOCK_SECONDS', '900'))  # 15 min

    def get_client_ip():
        # Soporte simple detrás de reverse proxy si se añade X-Forwarded-For
        xf = request.headers.get('X-Forwarded-For', '')
        if xf:
            return xf.split(',')[0].strip()
        return request.remote_addr or 'unknown'

    def check_bruteforce(email: str):
        now = time()
        key = f"{get_client_ip()}:{(email or '').lower()}"
        rec = failed_logins.get(key)
        if rec and rec.get('blocked_until', 0) > now:
            return True, int(rec['blocked_until'] - now)
        # Limpieza ventana expirada
        if rec and (now - rec.get('first', now)) > LOGIN_WINDOW_SECONDS:
            failed_logins.pop(key, None)
        return False, 0

    def register_failed_login(email: str):
        now = time()
        key = f"{get_client_ip()}:{(email or '').lower()}"
        rec = failed_logins.get(key)
        if not rec:
            failed_logins[key] = {'count': 1, 'first': now, 'blocked_until': 0}
            return
        # Reset si ventana expirada
        if (now - rec['first']) > LOGIN_WINDOW_SECONDS:
            failed_logins[key] = {'count': 1, 'first': now, 'blocked_until': 0}
            return
        rec['count'] += 1
        # Bloqueo
        if rec['count'] >= LOGIN_MAX_ATTEMPTS:
            rec['blocked_until'] = now + LOGIN_BLOCK_SECONDS

    def clear_failed_login(email: str):
        key = f"{get_client_ip()}:{(email or '').lower()}"
        failed_logins.pop(key, None)

    # ---------------- CSRF Protección simple -----------------
    import secrets as _secrets

    def _get_csrf_token():
        token = session.get('_csrf')
        if not token:
            token = _secrets.token_hex(16)
            session['_csrf'] = token
        return token

    @app.context_processor  # type: ignore[misc]
    def inject_csrf():
        return {'csrf_token': _get_csrf_token()}

    @app.before_request  # type: ignore[misc]
    def csrf_protect():
        # Métodos que cambian estado
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            # Permitir endpoints públicos sin estado si se añaden en esta lista
            exempt = set([])
            if request.endpoint in exempt:
                return
            session_token = session.get('_csrf')
            supplied = (
                request.headers.get('X-CSRF-Token')
                or request.form.get('_csrf')
                or (request.is_json and isinstance(request.get_json(silent=True), dict) and request.get_json(silent=True).get('_csrf'))
            )
            if not session_token or not supplied or supplied != session_token:
                return ("CSRF token inválido", 400)

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
        
        # Obtener archivos del usuario
        user_files = get_user_files(session['user_id'])
        return render_template("dashboard.html", username=session['username'], files=user_files)

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

    # --------------------- Email & Tokens (definido antes de uso) ---------------------
    import smtplib, ssl
    from email.message import EmailMessage
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired # type: ignore

    def get_serializer():
        return URLSafeTimedSerializer(app.secret_key, salt='user-approval')

    def generate_action_token(action: str, user_id: int) -> str:
        s = get_serializer()
        return s.dumps({'a': action, 'u': user_id})

    def verify_action_token(action: str, user_id: int, token: str) -> bool:
        s = get_serializer()
        max_age = 60 * 60 * 24  # 24h
        try:
            data = s.loads(token, max_age=max_age)
            return data.get('a') == action and data.get('u') == user_id
        except (BadSignature, SignatureExpired):
            return False

    def _send_email(to_email: str, subject: str, body: str):
        host = os.environ.get('SMTP_HOST')
        port = int(os.environ.get('SMTP_PORT', '587'))
        user = os.environ.get('SMTP_USER')
        pwd = os.environ.get('SMTP_PASS')
        if not (host and user and pwd):
            app.logger.warning('SMTP no configurado, email omitido.')
            return
        msg = EmailMessage()
        msg['From'] = user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.set_content(body)
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=context)
            server.login(user, pwd)
            server.send_message(msg)

    def notify_admin_new_user(username: str, email: str):
        admin_mail = os.environ.get('ADMIN_EMAIL')
        if not admin_mail:
            return
        from sqlite3 import connect
        conn = connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT id FROM usuarios WHERE email=?', (email,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return
        uid = row[0]
        approve_t = generate_action_token('approve', uid)
        reject_t = generate_action_token('reject', uid)
        base_url = os.environ.get('PUBLIC_BASE_URL', 'http://localhost:3000')
        approve_url = f"{base_url}/admin/approve/{uid}/{approve_t}"
        reject_url = f"{base_url}/admin/reject/{uid}/{reject_t}"
        body = (f"Nuevo usuario pendiente:\n\nNombre: {username}\nEmail: {email}\n\n" \
                f"Aprobar: {approve_url}\nRechazar: {reject_url}\n\nEste enlace expira en 24h.")
        _send_email(admin_mail, 'Nuevo usuario pendiente', body)

    def notify_user_status(user_id: int, status: str):
        u = get_user_by_id(user_id)
        if not u:
            return
        if status == 'activo':
            subject = 'Tu cuenta fue aprobada'
            body = f"Hola {u['nombre']}, tu cuenta ha sido activada. Ya puedes iniciar sesión."
        elif status == 'rechazado':
            subject = 'Tu registro fue rechazado'
            body = f"Hola {u['nombre']}, tu registro ha sido rechazado. Si crees que es un error, contacta al administrador."
        else:
            subject = 'Estado de cuenta actualizado'
            body = f"Hola {u['nombre']}, estado cambiado a: {status}."
        _send_email(u['email'], subject, body)

    # --------------------- Registro y Aprobación ---------------------
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
            flash('Registro recibido. Tu cuenta está pendiente de aprobación.', 'success')
            # Notificar admin
            try:
                notify_admin_new_user(username, email)
            except Exception as e:
                app.logger.error(f"Fallo envío correo admin: {e}")
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

        # Comprobar bloqueo por fuerza bruta
        blocked, remaining = check_bruteforce(email)
        if blocked:
            minutos = max(1, round(remaining / 60))
            flash(f'Demasiados intentos fallidos. Intenta de nuevo en ~{minutos} min.', 'error')
            return redirect(url_for('login'))

        # check credentials
        user = check_user_login(email, password)
        if user:
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['nombre']
            clear_failed_login(email)
            flash('¡Bienvenido al Dashboard!\nHas iniciado sesión exitosamente en la aplicación.\nDesde aquí puedes subir archivos.', 'success')
            return redirect(url_for('dashboard'))
        # Diferenciar mensajes: usuario existe pero pendiente / rechazado
        from sqlite3 import connect
        try:
            conn = connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('SELECT estado FROM usuarios WHERE email=?', (email,))
            r = cur.fetchone()
            conn.close()
            if r:
                estado = r[0]
                if estado == 'pendiente':
                    flash('Tu cuenta aún está pendiente de aprobación.', 'error')
                elif estado == 'rechazado':
                    flash('Tu registro fue rechazado. Contacta al administrador.', 'error')
                else:
                    flash('Email o contraseña incorrectos', 'error')
            else:
                flash('Email o contraseña incorrectos', 'error')
        except Exception:
            flash('Email o contraseña incorrectos', 'error')
        # Registrar intento fallido tras procesar
        register_failed_login(email) # type: ignore
        return redirect(url_for('login'))

    # --------------------- Admin: aprobación usuarios ---------------------
    def is_admin_session():
        # Sencillo: comparar email almacenado en session (si se desea) o usar variable entorno
        admin_email = os.environ.get('ADMIN_EMAIL')
        return session.get('admin_authed') is True or (admin_email and session.get('user_email') == admin_email)

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'GET':
            return render_template('admin_login.html')
        pwd = request.form.get('password')
        expected = os.environ.get('ADMIN_PANEL_PASSWORD')
        if expected and pwd == expected:
            session['admin_authed'] = True
            flash('Admin autenticado', 'success')
            return redirect(url_for('admin_pending'))
        flash('Credenciales admin inválidas', 'error')
        return redirect(url_for('admin_login'))

    @app.route('/admin/pending')
    def admin_pending():
        if not is_admin_session():
            return redirect(url_for('admin_login'))
        pending = get_pending_users()
        return render_template('admin_pending.html', users=pending)

    @app.route('/admin/approve/<int:user_id>/<token>')
    def admin_approve(user_id, token):
        if not verify_action_token('approve', user_id, token):
            return 'Token inválido/expirado', 400
        if not set_user_status(user_id, 'activo'):
            return 'No se pudo activar', 400
        # Notificar usuario activado (best effort)
        try:
            notify_user_status(user_id, 'activo')
        except Exception as e:
            app.logger.error(f"Fallo notificar usuario activo: {e}")
        return redirect(url_for('admin_pending'))

    @app.route('/admin/reject/<int:user_id>/<token>')
    def admin_reject(user_id, token):
        if not verify_action_token('reject', user_id, token):
            return 'Token inválido/expirado', 400
        if not set_user_status(user_id, 'rechazado'):
            return 'No se pudo rechazar', 400
        try:
            notify_user_status(user_id, 'rechazado')
        except Exception as e:
            app.logger.error(f"Fallo notificar usuario rechazado: {e}")
        return redirect(url_for('admin_pending'))


    @app.route("/upload", methods=["GET", "POST"])
    def upload_file():
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        
        if request.method == 'GET':
            return render_template("upload.html")
        
        # POST request - manejar subida usando el módulo uploads
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        result, status_code = handle_file_upload(file, session['user_id'])
        
        if status_code == 200:
            flash(result['message'], 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(result['error'], 'error')
            return redirect(request.url)

    @app.route("/download/<filename>")
    def download_file(filename):
        # Si el usuario está logueado, validar que el archivo es suyo para mantener separación visual en dashboard
        from uploads import handle_public_download # type: ignore
        if 'user_id' in session:
            result = handle_file_download(filename, session['user_id'])
            if result is None:
                # Intentar descarga pública si no pertenece al usuario
                public_result = handle_public_download(filename)
                if public_result is None:
                    flash('Archivo no encontrado', 'error')
                    return redirect(url_for('dashboard'))
                return public_result
            return result
        else:
            # Descarga pública sin sesión
            public_result = handle_public_download(filename)
            if public_result is None:
                # Respuesta simple sin redirecciones a dashboard para usuarios públicos
                return "Archivo no encontrado o expirado", 404
            return public_result

    @app.route("/api/upload_progress", methods=["POST"])
    def upload_progress():
        """Endpoint para subida con progreso vía AJAX"""
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        
        if 'file' not in request.files:
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        file = request.files['file']
        result, status_code = handle_file_upload(file, session['user_id'])
        
        return jsonify(result), status_code

    # -------------------- Subidas resumibles (chunked) --------------------
    @app.route('/api/chunk/init', methods=['POST'])
    def chunk_init():
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        data = request.get_json(silent=True) or {}
        original_name = data.get('filename')
        total_size = data.get('total_size')
        if not original_name or not isinstance(total_size, int):
            return jsonify({'error': 'Datos inválidos'}), 400
        from uploads import init_resumable_upload  # type: ignore
        meta = init_resumable_upload(session['user_id'], original_name, total_size)
        return jsonify({
            'success': True,
            'upload_id': meta['upload_id'],
            'chunk_size': meta['chunk_size']
        }), 200

    @app.route('/api/chunk/upload', methods=['POST'])
    def chunk_upload():
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        upload_id = request.form.get('upload_id')
        try:
            chunk_index = int(request.form.get('chunk_index', -1))
        except ValueError:
            return jsonify({'error': 'chunk_index inválido'}), 400
        chunk = request.files.get('chunk')
        if not upload_id or chunk_index < 0 or not chunk:
            return jsonify({'error': 'Parámetros incompletos'}), 400
        from uploads import append_chunk  # type: ignore
        data = chunk.read()
        result, code = append_chunk(session['user_id'], upload_id, chunk_index, data)
        return jsonify(result), code

    @app.route('/api/chunk/finalize', methods=['POST'])
    def chunk_finalize():
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        data = request.get_json(silent=True) or {}
        upload_id = data.get('upload_id')
        if not upload_id:
            return jsonify({'error': 'upload_id requerido'}), 400
        from uploads import finalize_resumable_upload  # type: ignore
        result, code = finalize_resumable_upload(session['user_id'], upload_id)
        return jsonify(result), code

    @app.route("/api/delete_file", methods=["POST"])
    def delete_file():
        """Endpoint para eliminar archivos vía AJAX"""
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        
        filename = request.json.get('filename')
        if not filename:
            return jsonify({'error': 'Nombre de archivo requerido'}), 400
        
        result, status_code = delete_user_file(filename, session['user_id'])
        return jsonify(result), status_code

    @app.route("/api/cleanup_expired", methods=["POST"])
    def api_cleanup_expired():
        """Endpoint para limpiar archivos expirados manualmente"""
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        
        try:
            from uploads import cleanup_expired_files # type: ignore
            cleaned_files = cleanup_expired_files(session['user_id'])
            
            if cleaned_files:
                return jsonify({
                    'success': True, 
                    'message': f'Se eliminaron {len(cleaned_files)} archivo(s) expirado(s)',
                    'files': cleaned_files
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'message': 'No hay archivos expirados para limpiar'
                }), 200
                
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500

    return app

if __name__ == "__main__":
    app = main()
    app.run(host="0.0.0.0", port=3000, debug=True)