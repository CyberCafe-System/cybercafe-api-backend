# cybercafe-api-backend
# CyberCafe Backend

Backend del sistema de gestión integral para Cybercafé.

Este proyecto corresponde a la API central del sistema y será responsable de gestionar la lógica de negocio, autenticación, usuarios, equipos, inventario, ventas, rentas y reportes.

El backend está desarrollado utilizando **Django** y **Django REST Framework**, con autenticación mediante **JWT**.

---

## Tecnologías utilizadas

* **Python**
* **Django**
* **Django REST Framework**
* **Simple JWT**
* **django-cors-headers**
* **MySQL**
* **mysqlclient**
* **PyMySQL**
* **Git / GitHub**

---

## Requisitos

Antes de instalar el proyecto se debe contar con:

* Python instalado.
* `pip` funcionando correctamente.
* MySQL instalado y configurado.
* Git instalado.
* Un editor de código, como Visual Studio Code.
* Acceso al repositorio del proyecto.

Se recomienda utilizar un entorno virtual de Python para mantener aisladas las dependencias del proyecto.

---

## 1. Crear el entorno virtual

Desde la carpeta donde se encuentra el proyecto:

```bash
python -m venv venv
```

Activar el entorno virtual en Windows:

```bash
venv\Scripts\activate
```

Una vez activado, la terminal debería mostrar algo similar a:

```text
(venv) C:\ruta\cybercafe-backend>
```

---

## 2. Instalar las dependencias

Las dependencias utilizadas inicialmente en el proyecto son:

```bash
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers mysqlclient pymysql
```

### Dependencias principales

| Dependencia                     | Función                                                                            |
| ------------------------------- | ---------------------------------------------------------------------------------- |
| `django`                        | Framework principal del backend                                                    |
| `djangorestframework`           | Desarrollo de la API REST                                                          |
| `djangorestframework-simplejwt` | Autenticación mediante JWT                                                         |
| `django-cors-headers`           | Permitir solicitudes desde otros orígenes, como el frontend web o aplicación móvil |
| `mysqlclient`                   | Conexión de Django con MySQL                                                       |
| `pymysql`                       | Cliente MySQL escrito en Python                                                    |

Después de instalar las dependencias se puede generar el archivo:

```bash
pip freeze > requirements.txt
```

Este archivo permite registrar las versiones de las dependencias utilizadas por el proyecto.

---

## 3. Crear el proyecto Django

El proyecto Django fue creado utilizando:

```bash
django-admin startproject config .
```

El nombre `config` corresponde al paquete principal de configuración de Django.

Por decisión del proyecto, se utiliza `config` y no un nombre como `core_cybercafe`.

El punto (`.`) al final del comando permite crear el proyecto directamente dentro de la carpeta actual.

La estructura inicial contiene:

```text
config/
├── settings.py
├── urls.py
├── asgi.py
└── wsgi.py

manage.py
```

---

## 4. Estructura del proyecto

Se recomendó utilizar una estructura modular para separar las diferentes funcionalidades del sistema.

La estructura propuesta es:

```text
cybercafe-backend/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── users/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
│
├── equipment/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
│
├── inventory/
│
├── sales/
│
├── rentals/
│
├── reports/
│
├── tests/
│
├── .env
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

Esta estructura fue recomendada para mantener el backend organizado por módulos y facilitar el desarrollo colaborativo.

Aunque actualmente se está comenzando a trabajar con Django, separar las funcionalidades desde el inicio permite que cada parte del sistema tenga un lugar definido y sea más fácil de localizar, modificar y mantener posteriormente.

La idea general es que cada aplicación de Django represente una parte funcional del sistema.

---

## 5. Organización de las aplicaciones

### `config/`

Contiene la configuración general del proyecto Django.

```text
config/
├── settings.py
├── urls.py
├── asgi.py
└── wsgi.py
```

#### `settings.py`

Contiene la configuración principal del proyecto, incluyendo:

* Aplicaciones instaladas.
* Base de datos.
* Middleware.
* Configuración de Django REST Framework.
* Autenticación.
* Archivos estáticos.
* Configuración de CORS.
* Variables de entorno.

#### `urls.py`

Define las rutas principales de la API y conecta las rutas de las diferentes aplicaciones.

#### `asgi.py`

Punto de entrada para servidores compatibles con ASGI.

#### `wsgi.py`

Punto de entrada para servidores compatibles con WSGI.

---

### `users/`

Se encargará de la gestión de usuarios y autenticación.

En este módulo se trabajarán posteriormente:

* Usuarios.
* Roles.
* Permisos.
* Autenticación.
* JWT.

Los roles principales definidos para el sistema son:

* Administrador.
* Cajero.
* Asistente.

---

### `equipment/`

Se encargará de la administración de los equipos del Cybercafé.

Aquí se desarrollará la lógica relacionada con:

* Computadoras.
* Consolas.
* Componentes.
* Estados de los equipos.
* Repuestos.
* Registro de daños.
* Reemplazo de componentes.

---

### `inventory/`

Se encargará del inventario de productos destinados a la venta.

Aquí se trabajará posteriormente con:

* Productos.
* Categorías.
* Cantidades disponibles.
* Precio de compra.
* Precio de venta.
* Actualización de existencias.

---

### `sales/`

Se encargará del registro de las ventas realizadas en el Cybercafé.

Entre sus funciones estarán:

* Registrar ventas.
* Registrar detalles de venta.
* Calcular totales.
* Asociar productos con ventas.
* Actualizar inventario.

---

### `rentals/`

Se encargará de la gestión de las rentas de equipos.

Aquí se desarrollará la lógica relacionada con:

* Clientes.
* Rentas.
* Equipos rentados.
* Tiempo contratado.
* Hora de inicio.
* Tiempo restante.
* Tiempo adicional.
* Tarifas.
* Finalización de rentas.

---

### `reports/`

Se encargará de las consultas y reportes del sistema.

Permitirá posteriormente obtener información como:

* Ventas por fechas.
* Rentas por fechas.
* Ingresos por ventas.
* Ingresos por rentas.
* Información agrupada por periodos.

---

### `tests/`

Carpeta destinada a pruebas generales del proyecto.

Además, cada aplicación puede tener su propio archivo:

```text
tests.py
```

para pruebas específicas del módulo.

---

## 6. Archivo `.env`

Las configuraciones sensibles no deben escribirse directamente en el código fuente.

Se utilizará un archivo:

```text
.env
```

para almacenar información como:

```env
SECRET_KEY=...
DEBUG=True

DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=...
```

El archivo `.env` debe agregarse al `.gitignore` para evitar subir información sensible al repositorio.

---

## 7. Archivo `.gitignore`

El proyecto debe utilizar un `.gitignore` para evitar subir archivos innecesarios o sensibles.

Entre ellos:

```text
venv/
.env
__pycache__/
*.pyc
```

También se deben excluir archivos generados automáticamente que no sean necesarios para el repositorio.

---

## 8. Ejecutar el servidor de desarrollo

Con el entorno virtual activado:

```bash
python manage.py runserver
```

Django iniciará el servidor de desarrollo.

Por defecto estará disponible en:

```text
http://127.0.0.1:8000/
```

Para detener el servidor:

```text
Ctrl + C
```

---

## 9. Comandos principales de Django

Durante el desarrollo se utilizarán principalmente los siguientes comandos.

### Crear una aplicación

```bash
python manage.py startapp nombre_app
```

Ejemplo:

```bash
python manage.py startapp users
```

### Crear migraciones

Después de realizar cambios en los modelos:

```bash
python manage.py makemigrations
```

### Aplicar migraciones

```bash
python manage.py migrate
```

### Ejecutar el servidor

```bash
python manage.py runserver
```

### Crear un superusuario

```bash
python manage.py createsuperuser
```

### Revisar posibles problemas del proyecto

```bash
python manage.py check
```

---

## 10. Flujo básico de desarrollo

El desarrollo de cada módulo seguirá, de manera general, un flujo similar:

```text
Modelo
   ↓
Migración
   ↓
Serializer
   ↓
View / ViewSet
   ↓
URL
   ↓
API
   ↓
Cliente Web / Flutter
```

Por ejemplo:

```text
Base de datos
     ↓
models.py
     ↓
makemigrations
     ↓
migrate
     ↓
serializers.py
     ↓
views.py
     ↓
urls.py
     ↓
API REST
```

Esta estructura permite que el backend funcione como API central para los diferentes clientes del sistema.

---

## 11. Arquitectura general

El backend será el punto central de comunicación entre las aplicaciones del sistema.

```text
                    ┌──────────────────────┐
                    │   Django Backend     │
                    │      REST API        │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       Sistema Web       Aplicación móvil    Otros clientes
          / POS              Flutter
             │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                         Base de datos
                              MySQL
```

El backend será responsable de centralizar las reglas de negocio y proporcionar los datos necesarios para el sistema web y la aplicación móvil.

---

## 12. Estado actual del proyecto

Actualmente el proyecto se encuentra en la etapa inicial de configuración del backend.

Se ha establecido:

* Django como framework principal.
* Django REST Framework para la API.
* JWT para autenticación.
* CORS para permitir comunicación con otros clientes.
* MySQL como sistema gestor de base de datos.
* Una estructura modular dividida por funcionalidades.
* `config` como paquete principal de configuración.

Los módulos funcionales se irán desarrollando progresivamente conforme avance el proyecto.

---

## 13. Próximos pasos

El desarrollo continuará aproximadamente en este orden:

1. Configuración de la base de datos.
2. Configuración de Django REST Framework.
3. Configuración de JWT.
4. Configuración de CORS.
5. Desarrollo del módulo de usuarios.
6. Desarrollo de equipos.
7. Desarrollo de inventario.
8. Desarrollo de ventas.
9. Desarrollo de rentas.
10. Desarrollo de reportes.
11. Pruebas de integración.
12. Preparación para despliegue.

---

## Nota sobre el aprendizaje de Django

La estructura del proyecto fue planteada de manera modular para que las funcionalidades puedan localizarse fácilmente.

Cada aplicación tendrá responsabilidades específicas y seguirá una estructura similar:

```text
app/
├── migrations/
├── models.py
├── serializers.py
├── views.py
├── urls.py
└── tests.py
```

Esto permite trabajar cada módulo de forma independiente sin tener que concentrar toda la lógica del sistema en un único archivo.

A medida que avance el desarrollo se irá aprendiendo y aplicando la estructura de Django sobre el proyecto real, manteniendo una organización que permita que el código continúe siendo accesible y comprensible para el equipo.
