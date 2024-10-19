import sqlalchemy
from src import database as db
from src.api import info
#from api.carts import Customer

#this file will handle logging customers and visitors to the store

def log_checkout(cart_id):
    current_time = info.current_hour()
    current_day = info.current_day()
    with db.engine.begin() as connection:
        cart_info = connection.execute(
            sqlalchemy.text("""
        SELECT * 
        FROM carts
        INNER JOIN cart_items
            ON cart_items.cart_id=carts.cart_id
        WHERE carts.cart_id=:checkout_id
        """),
        [{"checkout_id":cart_id}]
        ).fetchall()
        for item in cart_info:
            character_class = item.character_class
            level = item.level
            name = item.name
            sku = item.item_sku
            quantity = item.quantity 
            cost = item.cost
            type = connection.execute(sqlalchemy.text("SELECT types from potions where sku=:sku"), [{"sku":sku}]).scalar_one()
            connection.execute(
                sqlalchemy.text("""
                    INSERT INTO checkout_log 
                    (name, type, price, quantity, level, time, day, character_class, cart_id)
                    VALUES (:name, :type, :price, :quantity, :level, :time, :day, :class, :cart_id)
                    """), [{"name":name, 
                            "type":type,
                            "price":cost, 
                            "quantity":quantity,
                            "level":level, 
                            "time":current_time, 
                            "day":current_day,
                            "class":character_class,
                            "cart_id":cart_id}]
            )
'''
def log_visits(new_visits: list[Customer]):
    with db.engine.begin() as connection:
        customers = db.get_table("visits")
        for customer in new_visits:
            visits = 0
            spent = 0
            fav_type = 0 
            fav_time = 0
            fav_day = 0
            connection.execute(
                sqlalchemy.insert(customers),
                [
                    {"name": customer.customer_name,
                    "class":customer.character_class,
                    "level":customer.level, # cart/barrel order/bottle order id
                    "num_visits":visits, 
                    "num_spent":
                    "fav_type":
                    "fav_time":
                    "fav_day":
                    }
                ])
'''
