# Dashboard Mikrotik

Dashboard Mikrotik es una aplicación web desarrollada en Django que permite administrar y monitorear dispositivos MikroTik con RouterOS de manera centralizada y sencilla. Proporciona una interfaz moderna para gestionar usuarios Hotspot, interfaces de red, enlaces activos, colas de ancho de banda (Queues) y conexiones PPP.

## Funcionalidades principales

- **Gestión de usuarios Hotspot:**  
  Visualiza, crea, edita y elimina usuarios Hotspot. Consulta perfiles, contraseñas y límites de tiempo.

- **Monitoreo y configuración de interfaces:**  
  Lista todas las interfaces de red del router, mostrando su estado, tipo y MTU.

- **Control de enlaces activos:**  
  Visualiza los usuarios actualmente conectados al Hotspot, su dirección IP, MAC, tiempo de conexión y estado de pago. Permite desconectar usuarios manualmente.

- **Administración de colas (Queues):**  
  Consulta y administra las colas simples configuradas en el MikroTik, incluyendo nombre, IP objetivo, límite máximo, uso actual y estado (activo/desactivado). Permite activar, desactivar y eliminar colas.

- **Supervisión de conexiones PPP:**  
  Muestra las sesiones PPP activas, con información relevante como nombre, dirección IP, MAC y tiempo de conexión. Permite desconectar o eliminar sesiones.

- **Caché y tolerancia a fallos:**  
  Si el router MikroTik no está disponible, la aplicación muestra datos en caché o datos de prueba, notificando al usuario de la situación.

## Requisitos

- Python 3.8+
- pip
- [Django](https://www.djangoproject.com/) (versión compatible con tu código)
- Acceso a un router MikroTik con API habilitada

## Instalación

1. **Clona el repositorio:**
   ```sh
   git clone https://github.com/Sptzr1/MikrotikPage.git
   cd MikrotikPage
   ```

2. **Crea y activa un entorno virtual:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instala las dependencias:**
   ```sh
   pip install -r requirements.txt
   ```
   > Si no tienes `requirements.txt`, instala Django y cualquier librería adicional que uses para la conexión con MikroTik.

4. **Configura las variables de entorno:**
   - Crea un archivo `.env` en la raíz del proyecto con las variables necesarias, por ejemplo:
     ```
     MIKROTIK_HOST=192.168.88.1
     MIKROTIK_USER=admin
     MIKROTIK_PASSWORD=tu_password
     ```

5. **Realiza las migraciones de la base de datos:**
   ```sh
   python manage.py migrate
   ```

6. **Crea un superusuario para acceder al panel de administración (opcional):**
   ```sh
   python manage.py createsuperuser
   ```

7. **Ejecuta el servidor de desarrollo:**
   ```sh
   python manage.py runserver
   ```

8. **Accede a la aplicación:**
   - Abre tu navegador y entra a [http://localhost:8000/](http://localhost:8000/)

## Estructura del proyecto

- `config/` — Configuración principal de Django (settings, urls, wsgi, asgi)
- `dashboard/` — Aplicación principal con vistas, modelos y lógica de negocio
- `templates/` — Plantillas HTML para la interfaz de usuario
- `static/` — Archivos estáticos (CSS, JS, imágenes)
- `db.sqlite3` — Base de datos SQLite por defecto

## Notas

- El archivo `.gitignore` ya está configurado para ignorar archivos sensibles y temporales como `.env`, `db.sqlite3`, carpetas de entorno virtual, etc.
- Si necesitas desplegar en producción, asegúrate de configurar correctamente las variables de entorno, la base de datos y los archivos estáticos.

## Créditos

Desarrollado por Luis Manuel Brito.

---

¿Dudas o sugerencias? Abre un issue o contacta al desarrollador.