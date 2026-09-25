import os
from sqlmodel import SQLModel, Session, create_engine
from dotenv import load_dotenv
load_dotenv()

DB_HOST= os.getenv("DB_HOST")
DB_NAME=os.getenv("DB_NAME")
DB_USER=os.getenv("DB_USER")
DB_PASSWORD=os.getenv("DB_PASSWORD")
DB_CHARSET=os.getenv("DB_CHARSET")
DB_PORT=os.getenv("DB_PORT")

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"Connection to database at {DB_URL}")
engine = create_engine(DB_URL, echo=True)

def crear_db_y_tablas():
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        print(f"Error en la bd: {e}")
def get_session():
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            print(f"Erro en la session de la bd: {e}")
            raise