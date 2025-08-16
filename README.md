# 🚀 DockerApp - Aplicación Web Moderna

Una aplicación web elegante y moderna construida con Flask, Docker y SQLite, que demuestra las mejores prácticas de desarrollo y containerización.

![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white)

## ✨ Características

- 🎨 **Diseño Moderno**: Interfaz elegante con gradientes, efectos de cristal y animaciones suaves
- 🔐 **Sistema de Autenticación**: Registro e inicio de sesión seguro con manejo de sesiones
- 🐳 **Containerización Completa**: Aplicación completamente dockerizada para fácil despliegue
- 📱 **Responsive Design**: Adaptable a todos los dispositivos y tamaños de pantalla
- 🎯 **UX/UI Optimizada**: Experiencia de usuario fluida con feedback visual inmediato
- 🔒 **Seguridad**: Manejo seguro de contraseñas y sesiones persistentes

## 🛠️ Tecnologías Utilizadas

| Tecnología | Propósito | Versión |
|------------|-----------|---------|
| **Python** | Backend | 3.10+ |
| **Flask** | Framework web | Latest |
| **SQLite** | Base de datos | Latest |
| **Docker** | Containerización | Latest |
| **Bootstrap 5** | Framework CSS | 5.3.3 |
| **JavaScript** | Interactividad | ES6+ |
| **Gunicorn** | Servidor WSGI | Latest |

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker y Docker Compose instalados
- Git (para clonar el repositorio)

### Instalación y Ejecución

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/PC0staS/prueba-docker.git
   cd prueba-docker
   ```

2. **Construir y ejecutar con Docker Compose**
   Añade tu clave al .env para producción.

   ```bash
   docker compose up --build
   ```

3. **Acceder a la aplicación**
   
   Abre tu navegador y ve a: `http://localhost:3000`

¡Eso es todo! La aplicación estará disponible y lista para usar.

## 📁 Estructura del Proyecto

```
prueba-docker/
├── 📄 docker-compose.yml     # Configuración de Docker Compose
├── 📄 dockerfile            # Imagen Docker personalizada
├── 📁 code/                 # Código fuente de la aplicación
│   ├── 📄 app.py            # Aplicación principal Flask
│   ├── 📄 db_logic.py       # Lógica de base de datos
│   ├── 📄 init_db.py        # Inicialización de DB
│   ├── 📄 wsgi.py           # Punto de entrada WSGI
│   ├── 📄 requirements.txt  # Dependencias Python
│   ├── 📁 static/           # Archivos estáticos
│   │   ├── 📄 styles.css    # Estilos personalizados
│   │   └── 📁 js/
│   │       └── 📄 app.js    # JavaScript interactivo
│   └── 📁 templates/        # Plantillas HTML
│       ├── 📄 base.html     # Plantilla base
│       ├── 📄 index.html    # Página de inicio
│       ├── 📄 login.html    # Formulario de login
│       ├── 📄 register.html # Formulario de registro
│       └── 📄 dashboard.html # Panel de usuario
└── 📁 db/                   # Base de datos SQLite
    └── 📄 database.db       # Archivo de base de datos
```

## 🎨 Características del Diseño

### Paleta de Colores
- **Primario**: `#6366f1` (Índigo vibrante)
- **Secundario**: `#10b981` (Verde esmeralda)
- **Fondo**: Gradiente oscuro con efectos de cristal
- **Texto**: Esquema de colores optimizado para legibilidad

### Efectos Visuales
- ✨ Animaciones suaves al cargar
- 🔮 Efectos de cristal (glass morphism)
- 🌊 Gradientes dinámicos
- 🎯 Hover effects interactivos
- 📱 Transiciones responsivas

## 🔧 Comandos Útiles

### Docker
```bash
# Construir la imagen
docker compose build

# Ejecutar en segundo plano
docker compose up -d

# Ver logs
docker compose logs -f

# Detener servicios
docker compose down

# Limpiar volúmenes
docker compose down -v
```

### Exponer temporalmente la app con Cloudflare Tunnel (desde Docker)

Si tu aplicación corre en el host y quieres ejecutar cloudflared desde un contenedor Docker, usa `host.docker.internal` para que el contenedor apunte al host Windows:

```bash
# Ejecutar cloudflared desde Docker y apuntar al host (Windows/Docker Desktop)
docker run --rm -it cloudflare/cloudflared tunnel --url http://host.docker.internal:3000
```

Esto crea una URL pública temporal que reenvía a `http://host.docker.internal:3000`. Detén el túnel con Ctrl+C en la terminal del contenedor.

### Desarrollo Local
```bash
# Instalar dependencias (si desarrollas sin Docker)
pip install -r code/requirements.txt

# Ejecutar la aplicación
python code/app.py

# Ejecutar con Gunicorn
gunicorn --bind 0.0.0.0:3000 wsgi:app
```

## 🗄️ Base de Datos

La aplicación utiliza SQLite con la siguiente estructura:

### Tabla `usuarios`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INTEGER PRIMARY KEY | ID único del usuario |
| `nombre` | TEXT NOT NULL | Nombre de usuario |
| `email` | TEXT UNIQUE NOT NULL | Email (único) |
| `password` | TEXT NOT NULL | Contraseña hasheada |

## 🌟 Funcionalidades

### 🔐 Sistema de Autenticación
- Registro de nuevos usuarios
- Inicio de sesión seguro
- Manejo de sesiones persistentes (7 días)
- Validación de formularios
- Protección de rutas

### 🎨 Interfaz de Usuario
- Página de inicio atractiva
- Formularios modernos con validación visual
- Dashboard personalizado
- Mensajes flash informativos
- Navegación intuitiva

### 🔧 Administración
- Limpieza de base de datos
- Manejo de errores elegante
- Logs de aplicación
- Configuración mediante variables de entorno

## 🚀 Despliegue en Producción

Para desplegar en producción, considera:

1. **Variables de Entorno**
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=tu-clave-secreta-muy-segura
   ```

### .env y uso con Docker

Antes de construir/ejecutar con Docker, crea un archivo `.env` en la raíz del repositorio con la variable `SECRET_KEY`.(Tiene que ser una clave segura.)

Usar el `.env` con Docker:

```powershell

# Run (compose lee .env automáticamente cuando usas env_file en compose, o puedes pasar explícitamente)
docker compose up --build

```
2. **Proxy Reverso** (Nginx recomendado)
3. **SSL/TLS** para HTTPS
4. **Backup de Base de Datos** regular
5. **Monitoreo** de aplicación

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Para contribuir:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👨‍💻 Autor

**Pablo Costas**
- GitHub: [@PC0staS](https://github.com/PC0staS)

## 🙏 Agradecimientos

- Flask por el framework web minimalista
- Docker por la containerización
- Bootstrap por el framework CSS
- La comunidad open source por las herramientas increíbles

---

<div align="center">

**¿Te gusta el proyecto? ¡Dale una ⭐!**

Made with ❤️ and Docker 🐳

</div>