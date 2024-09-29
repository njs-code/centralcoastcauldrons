from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db


router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    #Version 1:  
    # Update num_green_ml and gold based on barrels delivered. 
    total_price = 0
    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            if barrel.sku == 'SMALL_GREEN_BARREL':
                #calculate total ml of order 
                green_ml = barrel.ml_per_barrel * barrel.quantity
                inv_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()
                #update num_green_ml to inventory ml + delivered ml 
                sql_to_execute = f"UPDATE global_inventory SET num_green_ml = '{green_ml + inv_ml}'"
                connection.execute(sqlalchemy.text(sql_to_execute))
            #keep track of price
            total_price += barrel.price
            print(total_price)
        #update global_inventory gold based on price 
        inv_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        sql_to_execute = f"UPDATE global_inventory SET gold = '{inv_gold - total_price}'"
        connection.execute(sqlalchemy.text(sql_to_execute))
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    #Version 1: 
    # Take num_green_potions and find out if more than 10 
    # Request a small green barrel if <10 green potions
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).fetchall()
        num_green_potions = result[0].num_green_potions
        num_green_ml = result[0].num_green_ml
        if num_green_potions < 10:
            return [
                { }
            ]
        else:
            return [
                {
                    "sku": "SMALL_GREEN_BARREL",
                    "quantity": 1,
                }
            ]

