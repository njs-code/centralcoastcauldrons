from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src import orders, planner, calendar

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
            red_spent = green_spent = blue_spent = dark_spent = total_quantity = 0

            for potion in potions_delivered:
                #calculate ml used of each liquid
                red_spent += potion.potion_type[0] * potion.quantity 
                green_spent += potion.potion_type[1] * potion.quantity 
                blue_spent += potion.potion_type[2] * potion.quantity 
                dark_spent += potion.potion_type[3] * potion.quantity 

                #update number of potion in inventory 
                type = potion.potion_type
                update = potion.quantity
                total_quantity += update
                connection.execute(
                    sqlalchemy.text("""
                                    UPDATE potions SET
                                    quantity = quantity + :update
                                    WHERE types = :type"""),
                                    [{"update":update,
                                      "type":type}])
            # update inventory volumes
            connection.execute(
                sqlalchemy.text("""UPDATE global_inventory SET
                                red = red - :red,
                                green = green - :green,
                                blue = blue - :blue,
                                dark = dark - :dark
                                """),
                                [{"red":red_spent,
                                  "green": green_spent,
                                  "blue":blue_spent,
                                  "dark":dark_spent}])
        orders.post_order(variety="Bottles",gold_change=0,order_id=order_id,quantity=total_quantity)
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
    # Version 3: 
    # 1) Calls calendar to get list of potions for the day
    # 2) Builds a list of Potion objects
    # 3) Sends to planner to filter based on inventory
    # 4) Returns result
    potion_list = []
    with db.engine.begin() as connection:
        potions = calendar.day_potions()
        print("Calendar Returned: ")
        for potion in potions:
            print(potion)
            potion_list.append(Potion(
                sku=potion.sku,
                type = potion.types,
                quantity = potion.quantity,
                brew_num = potion.avg + 5,
                request_num = 0
                ))
    request =  planner.get_bottle_plan(potion_list)
    print(request)
    return request

if __name__ == "__main__":
    print(get_bottle_plan())