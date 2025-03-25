# API de Servicios de Mutua para Clínica Hospitalaria

Una API REST desarrollada con FastAPI que representa los servicios que podría ofrecer una mutua (compañía de seguros) a una clínica hospitalaria.

## Estructura del Proyecto

El proyecto está organizado en tres archivos principales:

- `models.py`: Contiene todos los modelos SQLAlchemy (ORM) y esquemas Pydantic
- `database.py`: Maneja la conexión a la base de datos PostgreSQL y la inicialización de datos
- `main.py`: Contiene todos los endpoints de la API

## Funcionalidades

La API proporciona las siguientes funcionalidades:

1. **Autorizar tratamiento o servicio solicitado**
2. **Consultar historial de autorizaciones previas**
3. **Consultar estado de facturas asociadas**
4. **Solicitar informe de servicios utilizados**

## Requisitos

- Python 3.7+
- PostgreSQL
- Dependencias listadas en `requirements.txt`

## Configuración

### Variables de Entorno

La aplicación utiliza las siguientes variables de entorno (valores por defecto entre paréntesis):

- `DATABASE_URL`: URL de conexión a PostgreSQL ("postgresql://postgres:postgres@localhost/mutua_db")
- `SECRET_KEY`: Clave secreta para generación de tokens JWT
- `TST_USER`: Usuario de prueba para autenticación ("admin")
- `TST_PASSWORD`: Contraseña del usuario de prueba ("password")

### Base de Datos

La aplicación intentará conectarse a PostgreSQL usando la variable de entorno `DATABASE_URL`. 
Si PostgreSQL no está disponible, automáticamente utilizará SQLite como alternativa, creando un archivo `mutua.db` en el directorio actual.

### Instalación y Ejecución

1. Clonar el repositorio
2. Crear un entorno virtual:

```
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```
3. Instalar dependencias:
````
pip install -r requirements.txt
````
4. Iniciar la aplicación:
````
uvicorn main --reload
````
Si tienes PostgreSQL disponible, asegúrate de que está en ejecución y crea la base de datos:
````
createdb mutua_db
````
Si no tienes PostgreSQL, no te preocupes, la aplicación utilizará SQLite automáticamente.

La API estará disponible en `http://localhost:8000`

## Documentación de la API

La documentación interactiva estará disponible en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Autenticación

La API utiliza autenticación OAuth2 con JWT. Para obtener un token:

1. Accede a `http://localhost:8000/docs`
2. Haz clic en el botón "Authorize" en la parte superior derecha
3. Ingresa las credenciales configuradas (por defecto: admin/password)
4. Usa el token obtenido para las peticiones subsiguientes

## Notas

- Al iniciar la aplicación, se crean automáticamente las tablas en la base de datos y se inicializan datos de prueba
- En un entorno de producción, se recomienda utilizar una gestión más segura de secretos y configuraciones