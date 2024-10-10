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
    # Version 2.5.1:
    # stores catalog in barrels database
    # filters unaffordable barrels, sorts by volume desc
    # until budget is exhausted, it will buy barrels of largest colume
    # will only purchase 1 of each type+size, this is to attempt getting a diversity of barrel types

    with db.engine.begin() as connection:
        # clear barrels database
        connection.execute(sqlalchemy.text("DELETE FROM barrels"))
        budget = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        #populate barrels with catalog
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
        # select largest volume barrel type which we can afford
        affordable_barrels = connection.execute(sqlalchemy.text(f"SELECT * FROM barrels WHERE price <= {budget} ORDER BY volume DESC")).fetchall()
        print(affordable_barrels)
        request = []
        for barrel in affordable_barrels:
            if budget - barrel.price < 0:
                pass
            elif budget - barrel.price >= 0:
                request.append({
                    "sku": f"{barrel.sku}",
                    "quantity":1 
                })
                budget -= barrel.price
        if len(request) == 0:
            return []
        else:
            print("Barrels ordered: ")
            print(request)
            return request

