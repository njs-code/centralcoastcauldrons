import sqlalchemy
from src import database as db

# function to post an order to the database
def post_order(variety, order_id, gold_change, quantity):
    orders = db.get_table("orders")
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.insert(orders),
            [
                {"quantity":quantity,
                "gold_change":gold_change,
                "order_id":order_id, # cart/barrel order/bottle order id
                "variety":variety # Either Checkout, Barrel, Bottle, or Purge (/reset/)
                }
            ])

#verifies an order's ID has not already been processed 
def validate_order(order_id):
    orders = db.get_table("orders")
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.select(orders).where(orders.c.order_id==order_id))
        if result.rowcount == 0:
            return False
        else:
            return True