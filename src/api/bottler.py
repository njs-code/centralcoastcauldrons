from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    # Version 1:
    # take potions_delivered and UPDATE num_green_potions accordingly
    with db.engine.begin() as connection:
        global_inventory = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).fetchall()

        for potion in potions_delivered:
            if potion.potion_type == [0, 100, 0, 0]:
                #calculate ml green liquid spent
                    #eventually:
                    # red_liquid_spent += potion_type[0] * potion.quantity 
                    # green_liquid_spent += potion_type[1] * potion.quantity 
                ml_spent = potion.quantity * 100

                #update num_green_ml in inventory 
                green_ml_inv = global_inventory[0].num_green_ml
                green_potions_inv = global_inventory[0].num_green_potions
                update_ml = green_ml_inv - ml_spent
                print(f"Spent: {ml_spent}, Inventory: {green_ml_inv}, Update: {update_ml}")
                connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = '{update_ml}'"))
                
                #update num_green_potions based on quantity delivered 
                update_quantity = green_potions_inv + potion.quantity
                sql_to_execute = f"UPDATE global_inventory SET num_green_potions = '{update_quantity}'"
                connection.execute(sqlalchemy.text(sql_to_execute))
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Version 1: take num_green_ml and divide by 100 
    # request to brew this many potions 
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).fetchall()
        num_green_ml = result[0].num_green_ml
        brew_num = num_green_ml // 100
    return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": brew_num,
            }
        ]

if __name__ == "__main__":
    print(get_bottle_plan())