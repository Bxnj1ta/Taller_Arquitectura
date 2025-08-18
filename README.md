# Andres Toledo, Benjamin González, Daniel Reyes y Sebastian Urrego

# 🌐  Tarea aquitectura de software - CRUD e inicio sesión con "admin"

Proyecto de ejemplo en **Django** para la gestión de ítems mediante un **CRUD (Create, Read, Update, Delete)**.  
Incluye autenticación de usuario, vistas con formularios y una API REST para interactuar con los datos.

---

## 🚀 Características
- ✅ Autenticación de usuario con login.
- ✅ Listado de ítems dinámico con **JavaScript (fetch API)**.
- ✅ Operaciones CRUD (crear, leer, editar, eliminar).
- ✅ API REST construida con **Django REST Framework**.
- ✅ Estilo moderno y responsive en las vistas (HTML + CSS).

---

## 📂 Estructura del proyecto
```
SOA_CRUD/
│── items/         # App principal con modelos, vistas y API
│── soa_crud/      # Configuración global de Django (urls, settings, wsgi, asgi)
│── db.sqlite3     # Base de datos SQLite (puede ser reemplazada por PostgreSQL/MySQL)
│── manage.py      # Script principal de Django para ejecutar el proyecto
│── requirements.txt # Dependencias del proyecto
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

---