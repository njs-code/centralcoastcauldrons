import os
import dotenv
import sqlalchemy 

def database_connection_url():
    dotenv.load_dotenv()

    return os.environ.get("POSTGRES_URI")

engine = sqlalchemy.create_engine(database_connection_url(), pool_pre_ping=True)

with engine.begin() as connection:
    result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
    for row in result:
        print(row)