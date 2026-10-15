import os
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "cibercafe_db")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")
DB_PORT = os.getenv("DB_PORT", "3306")

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
SERVER_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"

print("Connection to database at url")
engine = create_engine(DB_URL, echo=True)


def asegurar_base_de_datos():
    """Crea la base de datos en el servidor MySQL si no existe."""
    try:
        server_engine = create_engine(SERVER_URL)
        with server_engine.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                    f"CHARACTER SET {DB_CHARSET} COLLATE {DB_CHARSET}_unicode_ci;"
                )
            )
            conn.commit()
    except Exception as e:
        print(f"Aviso al verificar o crear la base de datos '{DB_NAME}': {e}")


def inicializar_datos_semilla():
    """Inserta los 3 roles con sus IDs fijos (1, 2, 3) y el usuario admin si no existen."""
    from models.rol import Rol
    from models.usuario import Usuario
    from librerias.pwd import get_password_hash

    roles_default = [
        {
            "rol_id": 1,
            "nombre": "Admin",
            "descripcion": (
                "Acceso completo al sistema, administracion de usuarios, equipos, "
                "productos, ventas, rentas, inventario, componentes y reportes."
            ),
        },
        {
            "rol_id": 2,
            "nombre": "Cajero",
            "descripcion": (
                "Atencion al cliente, registro de ventas de productos y "
                "gestion de la renta de computadoras."
            ),
        },
        {
            "rol_id": 3,
            "nombre": "Asistente",
            "descripcion": (
                "Control y revision fisica de los equipos, verificacion de componentes, "
                "cambio de disponibilidad y reporte de daños."
            ),
        },
    ]

    try:
        with Session(engine) as session:
            # 1. Crear roles fijos si no existen
            for rol_data in roles_default:
                rol_existente = session.exec(
                    select(Rol).where(
                        (Rol.rol_id == rol_data["rol_id"]) | (Rol.nombre == rol_data["nombre"])
                    )
                ).first()
                if not rol_existente:
                    session.add(Rol(**rol_data))
            session.commit()

            # 2. Crear usuario administrador por defecto (rol_id = 1)
            admin_user = session.exec(
                select(Usuario).where(Usuario.username == "admin")
            ).first()
            if not admin_user:
                default_admin_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
                admin_user = Usuario(
                    rol_id=1,
                    nombre="Administrador",
                    username="admin",
                    correo="admin@cybercafe.com",
                    password=get_password_hash(default_admin_pass),
                    is_superuser=True,
                    last_login=None,
                    activo=True,
                )
                session.add(admin_user)
                session.commit()
                print("Usuario administrador creado (usuario: admin, password: admin123)")
    except Exception as e:
        print(f"Aviso al inicializar datos semilla: {e}")


def crear_db_y_tablas():
    asegurar_base_de_datos()
    try:
        import models  # Registra todos los modelos en SQLModel.metadata
        SQLModel.metadata.create_all(engine)
        inicializar_datos_semilla()
    except Exception as e:
        print(f"Error en la bd: {e}")


def get_session():
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            print(f"Error en la session de la bd: {e}")
            raise