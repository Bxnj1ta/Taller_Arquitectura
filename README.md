# Andres Toledo, Benjamin González, Daniel Reyes y Sebastian Urrego

# 🌐  Tarea arquitectura de software - CRUD e inicio sesión con "admin"

Proyecto de ejemplo en **Django** para la gestión de ítems mediante un **CRUD (Create, Read, Update, Delete)**.  
Incluye autenticación de usuario, vistas con formularios y una API REST para interactuar con los datos.  
Se integran servicios en **AWS** (S3 y Lambda) y un microservicio en **FastAPI**.

---

## 🚀 Características
✅ Autenticación de usuario con login.  
✅ Listado de ítems dinámico con JavaScript (fetch API).  
✅ Operaciones CRUD (crear, leer, editar, eliminar).  
✅ API REST construida con Django REST Framework.  
✅ Estilo moderno y responsive en las vistas (HTML + CSS).  
✅ AWS S3 como almacenamiento de archivos estáticos y multimedia.  
✅ AWS Lambda para procesamiento automático de archivos.  
✅ FastAPI como microservicio auxiliar para endpoints ligeros.  

---

## 📂 Estructura del proyecto

```
SOA_CRUD/
│── items/ # App principal con modelos, vistas y API
│── soa_crud/ # Configuración global de Django (urls, settings, wsgi asgi)
│── fastapi_service/ # Microservicio con FastAPI
│── db.sqlite3 # Base de datos SQLite (puede ser reemplazada por PostgreSQL/MySQL)
│── manage.py # Script principal de Django para ejecutar el proyecto
│── requirements.txt # Dependencias del proyecto
│── .env # Variables de entorno (NO se sube a GitHub)
```
---

## ⚙️ Instalación y ejecución

### 1️⃣ Clonar el repositorio
```bash
git clone https://github.com/tu_usuario/soa_crud.git
cd soa_crud

```
### 2️⃣ Crear entorno virtual
```bash
python -m venv soa_crud_env
```

Activar el entorno:
- **Windows (PowerShell):**
  ```bash
  .\soa_crud_env\Scripts\activate
  ```
- **Linux/Mac:**
  ```bash
  source soa_crud_env/bin/activate
  ```

### 3️⃣ Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4️⃣ Aplicar migraciones
```bash
python manage.py migrate
```

### 5️⃣ Crear superusuario (para /admin)
```bash
python manage.py createsuperuser
```

### 6️⃣ Ejecutar el servidor
```bash
python manage.py runserver
```
Acceder en navegador:  
👉 `http://127.0.0.1:8000/login/`


### 7 Ejecutar el fastapi
```bash
uvicorn fastapi_service.main:app --reload --port 8001

```

Acceder en navegador:  
👉 `http://127.0.0.1:8001/docs`

---

## 📡 Endpoints principales

- `/login/` → Página de login.  
- `/list/` → Lista de ítems (vista principal).  
- `/form/` → Formulario para crear/editar ítems.  
- `/api/items/` → API REST para listar ítems.  
- `/api/items/create/` → API REST para crear un nuevo ítem.  
- `/api/items/<id>/` → API REST para consultar, actualizar o eliminar un ítem.  

---

## 🎨 Vista previa

📌 **Login**  
Pantalla centrada con diseño moderno y gradiente de fondo.

📌 **Lista de ítems**  
Vista con botones de **Editar** y **Borrar**, cargada dinámicamente con JavaScript.

---

## 👨‍💻 Tecnologías utilizadas
- [Django](https://www.djangoproject.com/) (backend)
- [Django REST Framework](https://www.django-rest-framework.org/) (API)
- HTML, CSS, JavaScript (frontend)
- SQLite (base de datos por defecto)
- FastAPI (microservicio)
- AWS S3 (almacenamiento de archivos)
- AWS Lambda (serverless functions)
---

# 📊 Estado de Cumplimiento OWASP API Top 10

| Riesgo OWASP API | Estado | Implementación |
|------------------|--------|----------------|
| **API1 – Autorización a nivel objeto roto** | ✅ | Validación de objetos por usuario con `get_object_or_404` |
| **API2 – Autenticación rota** | ✅ | Django auth, JWT, hashing de contraseñas, CSRF |
| **API3 – Autorización a nivel de propiedad de objeto roto** | ✅ | Serializadores limitados, exclusión de campos sensibles |
| **API4 – Consumo de recursos sin restricciones** | ✅ (básico) | Throttling en DRF; falta Redis/Memcached en prod |
| **API5 – Autorización a nivel de función rota** | ✅ | Roles y `@permission_classes` aplicados |
| **API6 – Acceso sin restricciones a flujos comerciales sensibles** | ✅ | Validación explícita en `serializers.py`, `read_only` en campos |
| **API7 – Falsificación de solicitudes del lado del servidor** | ✅ | `DEBUG=False`, CSRF activo, headers de seguridad |
| **API8 – MAla configuración de seguridad** | ✅ | ORM seguro, sanitización de entradas |
| **API9 – Gestión inadecuada del inventario** | ✅ | Versionado `/api/v1`, eliminación de endpoints inseguros |
| **API10 – Consumo inseguro de API** | ✅ (básico) | Logging Django; falta SIEM/monitoring en prod |

---

📌 **Resumen**:  
- ✔️ APIs 1–9 están **implementadas y seguras** en el entorno actual.  
- ⚠️ APIs 4 y 10 requieren **endurecimiento en producción** (Redis/Memcached para rate limiting + SIEM para logs).  
