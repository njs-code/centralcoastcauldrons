# file to handle the bottle and barrel planning logic 
from src import database as db
import sqlalchemy

# logic for barrel planning 
def get_barrel_plan():
    budget = db.get_budget()

    with db.engine.begin() as connection:
        inventory = connection.execute(
            sqlalchemy.text
            ("""SELECT ml_capacity, red, green, blue, dark, budget 
             FROM global_inventory"""))[0]
        budget = inventory.budget
        capacity = inventory.ml_capacity
        stock = inventory.red + inventory.green + inventory.blue + inventory.dark

        # select largest volume barrels which we can afford
        affordable_barrels = connection.execute(
            sqlalchemy.text(
                            """SELECT * 
                            FROM barrels 
                            WHERE price <= :budget 
                            ORDER BY volume DESC, type"""),
                            [{"budget":budget}]).fetchall()
        request = []
        # determine if each is still affordable, add to request
        for barrel in affordable_barrels:
            if (budget - barrel.price < 0) or (stock + barrel.volume > capacity):
                pass
            else:
                request.append({
                    "sku": f"{barrel.sku}",
                    "quantity":1 
                })
                budget -= barrel.price
        # return empty list if nothing
        if len(request) == 0:
            return []
        #print and return request
        else:
            print("Barrels ordered: ")
            print(request)
            return request

#load a catalog of barrels into database for storage
def load_barrel_catalog(wholesale_catalog):
    from src.api.barrels import Barrel
    with db.engine.begin() as connection:
        # clear barrels database
        connection.execute(sqlalchemy.text("TRUNCATE TABLE barrels"))

        #populate barrels with catalog
        for barrel in wholesale_catalog:
            sku = barrel.sku
            volume = barrel.ml_per_barrel
            type = barrel.potion_type
            for i in range(0, 4):
                type[i] = type[i] * 100
            price = barrel.price
            quantity = barrel.quantity
            connection.execute(
                sqlalchemy.text(
                    """INSERT INTO barrels (sku, volume, type, price, quantity) 
                    VALUES (:sku,:volume,(:type), :price, :quantity)"""
                    ), [{
                        "sku":sku,
                        "volume":volume,
                        "type":type,
                        "price":price,
                        "quantity":quantity,
                    }])

# logic for bottle planning          
def get_bottle_plan(potion_list : list):
    # get inventory liquids 
    red_inv = db.get_liquid_vol("red")
    green_inv = db.get_liquid_vol("green")
    blue_inv = db.get_liquid_vol("blue")
    dark_inv = db.get_liquid_vol("dark")
    #generate list of Potions (brew_num, request_num, etc)
    request_list = []
    while (len(potion_list) > 0):
        # check if enough inventory for another of each potion type 
        for potion in potion_list:
            type = potion.type
            # Check against inventory 
            if ((red_inv < type[0]) or
                (green_inv < type[1]) or
                (blue_inv < type[2]) or
                (dark_inv < type[3]) or
                # check if we've reached our cap
                (potion.request_num >= potion.brew_num)):
                # add to list if requesting any of potion
                if potion.request_num > 0:
                    request_list.append({
                    "potion_type": potion.type,
                    "quantity": potion.request_num
                    })
                potion_list.remove(potion)
            else:
                potion.request_num += 1
                red_inv -= type[0]
                green_inv -= type[1]
                blue_inv -= type[2]
                dark_inv -= type[3]
    return request_list

            