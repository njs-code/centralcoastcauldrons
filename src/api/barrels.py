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
    # Version 2.5:
    # stores catalog in barrels database
    # finds the potion in inventory with the smallest quantity 
    # requests whichever barrel of this liquid it can afford
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("DELETE FROM barrels"))

        for barrel in wholesale_catalog:
            sku = barrel.sku
            volume = barrel.ml_per_barrel
            type = barrel.potion_type
            for i in range(0, 4):
                type[i] = type[i] * 100
            price = barrel.price
            quantity = barrel.quantity
            sql_command = f"INSERT INTO barrels (sku, volume, type, price, quantity) VALUES ('{sku}',{volume},array{type}, {price}, {quantity})"
            connection.execute(sqlalchemy.text(sql_command))
        # find potion type with least quantity 
        # < ---- change this to return top two types?
        least_quantity_potion = connection.execute(sqlalchemy.text("SELECT * FROM potions WHERE quantity=(SELECT MIN(quantity) from potions)")).fetchall()[0].types
        # select matching barrel type which we can afford
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        requested_barrels = connection.execute(sqlalchemy.text(f"SELECT * FROM barrels WHERE type = array{least_quantity_potion} AND price <= {gold}")).fetchall()
        if len(requested_barrels) == 0:
            return []
        else:
            price = requested_barrels[0].price
            barrel_sku = requested_barrels[0].sku
            return [
                {
                    "sku": f"{barrel_sku}",
                    "quantity": 1,
                }
            ]

