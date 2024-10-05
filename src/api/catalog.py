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
        potion_list = [(100,0,0,0), (0,100,0,0)]
        for type in potion_list:
            # select quantity of potion already in inventory 
            potion = connection.execute(sqlalchemy.text(f"SELECT * FROM potions WHERE types=array{list(type)}")).fetchall()[0]
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
