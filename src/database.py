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

def get_num_potions():
    with engine.begin() as connection:
        num_potions = connection.execute(
            sqlalchemy.text(
                "SELECT SUM(quantity) FROM potions AS sum"
                )).scalar_one()
    return num_potions

def get_inv_volume():
    with engine.begin() as connection:
        return connection.execute(
            sqlalchemy.text(
                """SELECT SUM(red + green + blue + dark) 
                FROM global_inventory"""
                )).scalar_one()
    
def get_liquid_vol(color):
        with engine.begin() as connection:
            inv = connection.execute(
                sqlalchemy.text(
                    """SELECT *
                    FROM global_inventory"""
                    )).fetchall()[0]
            if color == "red":
                return inv.red
            elif color == "green":
                return inv.green
            elif color == "blue":
                return inv.blue
            elif color == "dark":
                return inv.dark

def get_gold():
    with engine.begin() as connection:
        return connection.execute(
            sqlalchemy.text(
                """SELECT gold
                FROM global_inventory"""
                )).scalar_one()
    
def get_budget():
    with engine.begin() as connection:
        budget = connection.execute(
            sqlalchemy.text(
                """SELECT budget
                FROM global_inventory"""
                )).scalar_one()
    return min(budget, get_gold())