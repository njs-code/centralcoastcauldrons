from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy as sqla
from src import database as db
from src import orders

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    gold = db.get_gold()
    num_potions = db.get_num_potions()
    inv_vol = db.get_inv_volume()
    return {"number_of_potions": num_potions, "ml_in_barrels": inv_vol, "gold": gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqla.text("""
                                     SELECT gold, budget
                                     FROM global_inventory
                                     FOR UPDATE
                                     """)).fetchall()[0]
        max_requests = (result.gold - result.budget) // 1000
        ml_change = potion_change = 0
        #request one of each if possible
        if max_requests > 1:
            potion_change = 1
            max_requests-=1
        if max_requests > 1:
            ml_change = 1
        cost = (potion_change + ml_change)*1000
        request = {
                "potion_capacity": potion_change,
                "ml_capacity": ml_change
                }
        print(request)
        connection.execute(sqla.text("""UPDATE global_inventory 
                                        SET gold = gold - :cost"""), 
                                        [{"cost":cost}])
        return request

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    new_ml = capacity_purchase.ml_capacity
    new_pot = capacity_purchase.potion_capacity
    with db.engine.begin() as connection:
        connection.execute(sqla.text("""UPDATE global_inventory SET 
                                     potion_capacity = (potion_capacity + :pot_change), 
                                     ml_capacity = (ml_capacity + :ml_change)"""), 
                                     [{"ml_change" : (new_ml*10000), 
                                       "pot_change" : (new_pot*50)}])
    quantity = new_ml + new_pot
    gold_change = quantity * 1000
    orders.post_order(variety="Capacity", order_id=order_id, gold_change=gold_change, quantity=quantity)
    return "OK"
