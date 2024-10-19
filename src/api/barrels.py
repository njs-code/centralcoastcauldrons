from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src import orders 
from src import planner

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
    #Version 2: 
    #Uses sku, volume, and quantity to update global inventory for each barrel
    #v3
    # implements order_Id checking and loads order to database
    if (orders.validate_order(order_id)) == False:
        total_price = 0
        with db.engine.begin() as connection:
            total_quantity=0
            for barrel in barrels_delivered:
                total_quantity += barrel.quantity
                #determine color from SKU
                color = barrel.sku.split("_")[1].lower()
                #determine volume 
                volume = barrel.ml_per_barrel * barrel.quantity
                #select volume of liquid already in inventory 
                inv_volume = connection.execute(sqlalchemy.text(f"SELECT {color} FROM global_inventory")).scalar()
                #update inventory volume to add new barrel's volume
                sql_to_execute = f"UPDATE global_inventory SET {color} = '{volume + inv_volume}'"
                connection.execute(sqlalchemy.text(sql_to_execute))
                #keep track of price
                total_price += barrel.price
            #update global_inventory gold based on price 
            inv_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
            sql_to_execute = f"UPDATE global_inventory SET gold = '{inv_gold - total_price}'"
            connection.execute(sqlalchemy.text(sql_to_execute))
        orders.post_order(variety="Barrel", gold_change=-(total_price),order_id=order_id,quantity=total_quantity)
        print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")
        return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    #Version 3:
    # load catalog to database 
    # filters unaffordable barrels, sorts by largest available volume
    # until budget is exhausted, it will buy barrels of largest volume
    print(wholesale_catalog)    
    planner.load_barrel_catalog(wholesale_catalog)    
    request = planner.get_barrel_plan()
    return request

