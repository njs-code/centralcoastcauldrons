import os
import dotenv
from pydantic import BaseModel
import sqlalchemy

def database_connection_url():
    dotenv.load_dotenv()
    return os.environ.get("POSTGRES_URI")

engine = sqlalchemy.create_engine(database_connection_url(), pool_pre_ping=True)

def get_table(table_name):
    metadata_obj = sqlalchemy.MetaData()
    return sqlalchemy.Table(table_name, metadata_obj, autoload_with=engine)