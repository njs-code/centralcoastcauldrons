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
    #Version 4: 
    # posts to barrel and gold ledgers
    # implements order_Id checking and loads order to database
    if (orders.validate_order(order_id)) == False:
        total_price = 0
        with db.engine.begin() as connection:
            red=green=blue=dark=total_quantity=0
            for barrel in barrels_delivered:
                #track for return statement
                total_quantity += barrel.quantity
                #determine color from SKU
                color = barrel.sku.split("_")[1].lower()
                #determine volume 
                volume = barrel.ml_per_barrel * barrel.quantity
                #track ml change
                if color == 'red':
                    red += volume
                elif color =='green':
                    green += volume
                elif color =='blue':
                    blue += volume
                elif color=='dark':
                    dark += volume
                #track price
                total_price += barrel.price

            #post transaction to orders
            id = connection.execute(
                    sqlalchemy.text(
                        """INSERT INTO orders 
                            (variety, quantity, gold_change, order_id)
                            VALUES (:variety, :quantity, :gold_change, :order_id)
                            RETURNING id
                            """),
                    [{"variety" : "Barrel", 
                      "quantity":total_quantity,
                      "gold_change":-total_price,
                      "order_id":order_id}]).scalar_one()
            
            #update  barrels ledger
            connection.execute(
                    sqlalchemy.text(
                        """INSERT INTO ledger_barrels 
                            (order_id, price, red_ml, green_ml, blue_ml, dark_ml)
                            VALUES (:order_id, :price, :red_ml, :green_ml, :blue_ml, :dark_ml)
                            """),
                    [{"order_id" : id, 
                      "price":total_price,
                      "red_ml":red,
                      "green_ml":green,
                      "blue_ml":blue,
                      "dark_ml":dark}])
            
            #post to gold ledger
            connection.execute(
                sqlalchemy.text("""
                                INSERT INTO ledger_gold
                                (quantity, order_id)
                                VALUES (:gold, :id)
                                """),
                                [{"id":id,
                                  "gold":-total_price}]
            )
            #update global inventory
            connection.execute(
                sqlalchemy.text(
                    """UPDATE global_inventory SET
                    red = red + :red, 
                    green = green + :green,
                    blue = blue + :blue,
                    dark = dark + :dark,
                    gold = gold - :price"""),
                    [{"red" : red, 
                      "green":green,
                      "blue":blue,
                      "dark":dark,
                      "price" : total_price}])
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

