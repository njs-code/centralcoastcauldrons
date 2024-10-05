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
    #Version 2: 
    #Uses sku, volume, and quantity to update global inventory for each barrel
    total_price = 0
    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
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
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")
    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    # Version 2:
    # finds the potion in inventory with the smallest quantity 
    # requests a barrel of this liquid 
    with db.engine.begin() as connection:
        # find potion with least quantity 
        least_quantity_potion = connection.execute(sqlalchemy.text("SELECT * FROM potions WHERE quantity=(SELECT MIN(quantity) from potions)")).fetchall()[0]
        # determine price, sku from barrels database
        color = least_quantity_potion.sku.split("_")[1]
        requested_barrel = connection.execute(sqlalchemy.text(f"SELECT * FROM barrels WHERE liquid_type = '{color}'")).fetchall()[0]
        price = requested_barrel.small_price
        barrel_sku = requested_barrel.small_sku
        # determine gold amount 
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        if price > gold:
            return []
        return [
                {
                    "sku": {barrel_sku},
                    "quantity": 1,
                }
            ]

