from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    # Version 1:
    # Connects to global_inventory database
    # returns a catalog offering only a green potion, and the quantity from global_inventory 
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar()
        num_green_potions = result
    if num_green_potions < 1:
        return []
    return [
            {
                "sku": "GREEN_POTION_0",
                "name": "Pure Green Potion",
                "quantity": num_green_potions,
                "price": 50,
                "potion_type": [0, 0, 100, 0],
            }
        ]
