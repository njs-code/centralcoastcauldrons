from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    # Version 2:
    # Retrieve number of red, green, blue potions from global_inventory 
    # post a set number of each?
    catalog = []
    with db.engine.begin() as connection:
        potion_list = connection.execute(sqlalchemy.text("""SELECT * 
                                                         FROM potions 
                                                         WHERE quantity > 0
                                                         ORDER BY quantity DESC, price DESC 
                                                         LIMIT 6""")).fetchall()
        for potion in potion_list:
            # select quantity of potion already in inventory 
            if potion.quantity < 1:
                continue
            listing = {
                "sku": potion.sku,
                "name": potion.name,
                "quantity": potion.quantity,
                "price": potion.price,
                "potion_type": potion.types,
            }
            catalog.append(listing)
    return catalog