from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api import carts

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        #update inventory to 0 and gold to 100
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET red=0, green=0, dark=0, blue=0, gold=100, potion_capacity=50, ml_capacity=10000"))
        #update potion quantities to 0
        connection.execute(sqlalchemy.text("UPDATE potions SET quantity = 0, num_sold=0"))
        #clear all cart rows, if any
        connection.execute(sqlalchemy.text("TRUNCATE TABLE cart_items"))
        connection.execute(sqlalchemy.text("TRUNCATE TABLE orders"))
        connection.execute(sqlalchemy.text("INSERT INTO orders (variety, order_id, gold_change, quantity) VALUES ('Purge',000,100,0)"))
        
        #reset cart counter to 1
        carts.id_counter = 0

    return "OK"

