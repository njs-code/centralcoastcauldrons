from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src import orders 
from src import planner

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
    # Version 2:
    # for each potion:
    #   subtract volume spent from global inventory
    #   update number of potion in potions 
    if (orders.validate_order(order_id)) == False:
        with db.engine.begin() as connection:
            red_spent = green_spent = blue_spent = dark_spent = 0

            for potion in potions_delivered:
                #calculate ml used of each liquid
                red_spent += potion.potion_type[0] * potion.quantity 
                green_spent += potion.potion_type[1] * potion.quantity 
                blue_spent += potion.potion_type[2] * potion.quantity 
                dark_spent += potion.potion_type[3] * potion.quantity 

                #update number of potion in inventory 
                type = potion.potion_type
                num_potions_inv = connection.execute(sqlalchemy.text(f"SELECT quantity FROM potions WHERE types = array{type}")).scalar()
                update_quantity = num_potions_inv + potion.quantity
                sql_to_execute = f"UPDATE potions SET quantity = '{update_quantity}' WHERE types=array{type}"
                connection.execute(sqlalchemy.text(sql_to_execute))
            # update inventory volumes
            global_inventory = connection.execute(sqlalchemy.text(f"SELECT * FROM global_inventory")).fetchall()[0]
            red_inv = global_inventory.red - red_spent
            green_inv = global_inventory.green - green_spent
            blue_inv = global_inventory.blue - blue_spent
            dark_inv = global_inventory.dark - dark_spent
            connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET red={red_inv}, green={green_inv}, blue={blue_inv}, dark={dark_inv}"))
        orders.post_order(variety="Bottles",gold_change=0,order_id=order_id,quantity=update_quantity)
        print(f"potions delievered: {potions_delivered} order_id: {order_id}")
        return "OK"

class Potion():
    def __init__(self, brew_num, request_num, sku, type, quantity):
        self.brew_num = brew_num
        self.request_num = request_num
        self.sku = sku
        self.type = type
        self.quantity = quantity
    
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    # Version 2: 
    # 1) Bottle plan first requires a list of potions to brew, with desired quantities 
    # 2) The goal quantity is the desired amount of potion - quantity already in inventory 
    # 3) The actually quantity requested is the max potions of this type we can brew given the quantity of liquid in inventory 
    potion_list = []
    with db.engine.begin() as connection:
        potions = connection.execute(
            sqlalchemy.text(
                "SELECT * FROM potions")).fetchall()
        for potion in potions:
            potion_list.append(Potion(
                sku=potion.sku,
                type = potion.types,
                quantity = potion.quantity,
                brew_num = potion.desired_amount,
                request_num = 0
                ))
    request =  planner.get_bottle_plan(potion_list)
    print(request)
    return request

if __name__ == "__main__":
    print(get_bottle_plan())