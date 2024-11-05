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
                                     SELECT gold, capacity_budget
                                     FROM global_inventory
                                     FOR UPDATE
                                     """)).fetchall()[0]
        max_requests = min(result.capacity_budget, result.gold) // 1000
        ml_change = potion_change = 0
        #request one of each if possible
        if max_requests >= 1:
            potion_change = 1
            max_requests-=1
        if max_requests >= 1:
            ml_change = 1
        cost = (potion_change + ml_change)*1000
        request = {
                "potion_capacity": potion_change,
                "ml_capacity": ml_change
                }
        print(request)
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

    #post order to orders (transactions) 
    id = connection.execute(
        sqla.text(
            """INSERT INTO orders 
                (variety, quantity, gold_change, order_id)
                VALUES (:variety, :quantity, :gold_change, :order_id)
                RETURNING id
                """),
        [{"variety" : "Checkout", 
        "quantity":quantity,
        "gold_change":gold_change,
        "order_id":order_id}]).scalar_one()    
    #post to gold ledger
    connection.execute(
        sqla.text("""
                INSERT INTO ledger_gold
                (quantity, order_id)
                VALUES (:gold, :id)
                """),
                [{"id":id,
                "gold":-(1000*(new_ml+new_pot))}]
            )
    return "OK"
