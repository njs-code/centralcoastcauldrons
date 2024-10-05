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
    # Version 2:
    # for each potion:
    #   subtract volume spent from global inventory
    #   update number of potion in potions 
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
        red_inv = global_inventory.red + red_spent
        green_inv = global_inventory.green + green_spent
        blue_inv = global_inventory.blue + blue_spent
        dark_inv = global_inventory.dark + dark_spent
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET red={red_inv}, green={green_inv}, blue={blue_inv}, dark={dark_inv}"))
        
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    # Version 2: 
    # 1) Bottle plan first requires a list of potions to brew, with desired quantities 
    # 2) The goal quantity is the desired amount of potion - quantity already in inventory 
    # 3) The actually quantity requested is the max potions of this type we can brew given the quantity of liquid in inventory 
    with db.engine.begin() as connection:
        # select volumes of liquids in inventory 
        global_inventory = connection.execute(sqlalchemy.text("SELECT red, green, blue, dark FROM global_inventory")).fetchall()[0]
        red_inv = global_inventory.red 
        green_inv = global_inventory.green
        blue_inv = global_inventory.blue
        dark_inv = global_inventory.dark

        # list to return later
        plan = []
        
        # potion list to brew. 
        # Format is: {type : desired_quantity}
        potion_list = {(100,0,0,0) : 5, (0,100,0,0) : 5, (0,0,100,0) : 5}

        for type, desired_amount in potion_list.items():
            # select quantity of potion already in inventory 
            inv_potion_quantity = connection.execute(sqlalchemy.text(f"SELECT quantity FROM potions WHERE types=array{list(type)}")).fetchall()[0].quantity
            # determine how much of this potion we want to brew
            brew_num = desired_amount - inv_potion_quantity

            # determine how much we can actually make with inventory volume
            final_quantity = 0
            for index in range(0, brew_num):
                # if not enough in inventory, break
                if red_inv < type[0]:
                    break
                # subtract from inventory
                red_inv -= type[0] 

                if green_inv < type[1]:
                    break
                green_inv -= type[1] 

                if blue_inv < type[2]:
                    break
                blue_inv -= type[2] 

                if dark_inv < type[3]:
                    break
                dark_inv -= type[3]  
                final_quantity += 1

            # if we can't make any of this potion, proceed to next potion type
            if final_quantity == 0:
                continue
                
            #otherwise add to plan
            request = {
                "potion_type": type,
                "quantity": final_quantity,
            }
            plan.append(request)
        return plan

if __name__ == "__main__":
    print(get_bottle_plan())