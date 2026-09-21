# cybercafe-api-backend

# CyberCafe API Backend

Backend del sistema de gestión integral para Cybercafé construido con FastAPI.

Este proyecto centraliza la lógica del negocio, la autenticación, los usuarios, la administración de equipos, inventario, ventas, alquileres y reportes mediante una API REST moderna y rápida.

La arquitectura está pensada para escalar de forma modular y mantener una separación clara entre configuración, autenticación, modelos, utilidades y endpoints.

---

## Tecnologías y stack

* Python 3.10+
* FastAPI
* Uvicorn
* Pydantic
* JWT / autenticación basada en tokens
* SQLAlchemy o conexión directa a base de datos (según implementación)
* MySQL / PostgreSQL (según entorno)
* Python-dotenv
* Git / GitHub

---

## Objetivo del backend

La API será responsable de:

* Gestionar usuarios y roles del sistema
* Controlar autenticación y autorización
* Administrar equipos, hardware y estados
* Registrar ventas, consumos y servicios
* Manejar alquileres y reservas
* Consultar reportes y métricas operativas
* Exponer endpoints para integración con frontend o aplicaciones cliente

---

## Requisitos previos

Antes de instalar el proyecto se debe contar con:

* Python instalado
* `pip` funcionando correctamente
* Un entorno virtual configurado
* Base de datos disponible y configurada
* Git instalado
* Visual Studio Code o editor equivalente

---

## 1. Crear el entorno virtual

Desde la raíz del proyecto:

```bash
python -m venv .venv
```

Activar el entorno virtual en Windows:

```bash
.venv\Scripts\activate
```

Si todo salió bien, la terminal mostrará algo similar a:

```text
(.venv) C:\ruta\cybercafe-api-backend>
```

---

## 2. Instalar dependencias

Instalar las dependencias del proyecto:

```bash
pip install -r requirements.txt
```

Si se agregan nuevas librerías, se recomienda mantener el archivo actualizado con:

```bash
pip freeze > requirements.txt
```

---

## 3. Variables de entorno

El proyecto utiliza un archivo `.env` para manejar configuraciones locales.

Se incluye un ejemplo en:

```text
.env-example
```

Ejemplo base:

```env
APP_NAME=cybercafe-api
DEBUG=true
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/cybercafe
SECRET_KEY=tu_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

> Copia `.env-example` como `.env` y ajusta los valores según tu entorno local.

---

## 4. Ejecutar la API

Se puede iniciar la aplicación con Uvicorn:

```bash
uvicorn main:app --reload
```

Esto levantará la API en:

```text
http://127.0.0.1:8000
```

La documentación Swagger queda disponible en:

```text
http://127.0.0.1:8000/docs
```

Y la documentación OpenAPI en:

```text
http://127.0.0.1:8000/redoc
```

---

## 5. Estructura del proyecto

La organización actual del backend es la siguiente:

```text
cybercafe-api-backend/
├── .env
├── .env-example
├── .gitignore
├── main.py
├── README.md
├── requirements.txt
├── config/
│   ├── db.py
│   ├── security.py
│   ├── security_dependencia.py
│   └── session_dependencia.py
├── lib/
│   └── pwd.py
├── models/
├── oauth/
│   └── oauth.py
├── routers/
└── .venv/
```

---

## 6. Descripción de módulos

### `main.py`

Archivo principal de la aplicación. Aquí se inicializa la instancia de FastAPI y se registran los routers principales.

### `config/`

Contiene la configuración de infraestructura y seguridad del proyecto.

* `db.py`: configuración de conexión a base de datos
* `security.py`: configuración central de autenticación y JWT
* `security_dependencia.py`: dependencias para proteger endpoints
* `session_dependencia.py`: manejo de sesión o dependencias relacionadas

### `models/`

Carpeta destinada a los modelos de datos del sistema.

Aquí se definirán entidades como:

* usuarios
* roles
* equipos
* inventario
* ventas
* alquileres
* reportes

### `oauth/`

Módulo para la lógica relacionada con autenticación OAuth o integración con proveedores de identidad.

### `lib/`

Contiene utilidades y helpers reutilizables.

* `pwd.py`: helpers relacionados con contraseñas, hashing o validaciones

### `routers/`

Carpeta para la definición de endpoints por dominio funcional.

Ejemplo:

* usuarios
* autenticación
* equipos
* ventas
* reportes

---

## 7. Convención de arquitectura

El proyecto sigue un enfoque modular de FastAPI:

* `main.py` para la creación de la app
* `config/` para infraestructura y seguridad
* `models/` para entidades del dominio
* `routers/` para endpoints por módulo
* `lib/` para utilidades compartidas
* `oauth/` para integración con autenticación externa

Esto permite mantener la aplicación organizada, reducir acoplamiento y facilitar el crecimiento del sistema.

---

## 8. Recomendaciones de desarrollo

* Mantener cada dominio funcional en su propio router
* Separar validaciones y lógica de negocio de los endpoints
* Usar `Depends` para autenticación y permisos
* Centralizar variables sensibles en `.env`
* Usar Pydantic para validación de datos
* Documentar cada endpoint con descripciones claras y respuestas esperadas

---

## 9. Flujo de trabajo sugerido

1. Crear o actualizar modelos en `models/`
2. Definir rutas en `routers/`
3. Configurar dependencias y seguridad en `config/`
4. Ejecutar la API localmente con `uvicorn`
5. Validar endpoints con Swagger
6. Realizar pruebas antes de integrar cambios a la rama principal

---

## 10. Estado del proyecto

El proyecto está en proceso de migración hacia una arquitectura basada en FastAPI, manteniendo una organización modular orientada al crecimiento del sistema y a la integración con frontend, administración y servicios del cybercafé.

---

## 11. Siguientes pasos recomendados

* Definir modelos base de usuarios, equipos y ventas
* Implementar autenticación JWT completa
* Crear routers por módulo funcional
* Añadir validaciones con Pydantic
* Preparar entorno de pruebas y base de datos
* Documentar endpoints y respuestas esperadas

Si quieres, también puedo dejarte una versión más pulida del README con badges, ejemplo de estructura de endpoints y un `docker-compose` base para FastAPI + MySQL.
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
