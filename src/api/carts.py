from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db
from src import orders 
from src.api import info
from src import customers as clients

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "0",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):

    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    print(f"searching for {customer_name}, {potion_sku}, page: {search_page}, search: {search_orders}, sort: {sort_col}")
    metadata_obj = sqlalchemy.MetaData()
    ledger = sqlalchemy.Table("ledger_potions", metadata_obj, autoload_with=db.engine)
    
    #determine order type
    if sort_col == "customer_name":
        order_by = ledger.c.name
    elif sort_col == "item_sku":
        order_by = ledger.c.sku
    elif sort_col == "line_item_total":
        order_by = ledger.c.price
    elif sort_col == "timestamp":
        order_by = ledger.c.timestamp
    else:
        assert False

    #determine offset from page
    offset = int(search_page) * 5

    #collect relevant columns
    stmt = sqlalchemy.select(
        ledger.c.id,
        ledger.c.sku,
        ledger.c.name,
        ledger.c.price,
        ledger.c.timestamp
    ).limit(6).offset(offset)

    #filter out ledger bottle deliveries
    stmt = stmt.filter(ledger.c.name != "The Gnomes")

    #filter with name and sku
    if customer_name != "":
        stmt = stmt.where(ledger.c.name.ilike(f"%{customer_name}%"))
    if potion_sku != "":
        stmt = stmt.where(ledger.c.sku.ilike(f"%{potion_sku}%"))

    with db.engine.begin() as connection:
         #determine ordering
        if sort_order == "asc":
            result = connection.execute(stmt.order_by(order_by.asc())).fetchall()
        else:
            result = connection.execute(stmt.order_by(order_by.desc())).fetchall()
    
    json = []
    for row in result:
        #page size
        if len(json) >= 5:
            break
        json.append({
                "line_item_id": row.id,
                "item_sku": row.sku,
                "customer_name": row.name,
                "line_item_total": row.price,
                "timestamp": row.timestamp})
    #next page determined from limit 
    if len(result) > 5:
        next = 1 + int(search_page)
    else:
        next = ""
    #previous page determined from offset
    if (offset >= 5):
        previous = int(search_page) - 1
    else: 
        previous = ""

    return {
        "previous":str(previous),
        "next":str(next),
        "results":json
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    clients.log_visitors(customers)
    day = info.current_day()
    print("CURRENT DAY: ")
    print(day)
    print(customers)

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """

    with db.engine.begin() as connection:
        # Add row to carts table with id, name, and class
        client_class = new_cart.character_class
        client_name = new_cart.customer_name
        client_level = new_cart.level
        sql_to_execute = f"INSERT INTO carts (name, character_class, level) VALUES ('{client_name}','{client_class}', '{client_level}') RETURNING cart_id"
        cart_id = connection.execute(sqlalchemy.text(sql_to_execute)).scalar_one()
    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        #pull price, quantity from inventory for given potion 
        potion_data = connection.execute(
            sqlalchemy.text("""
                            SELECT price, quantity
                            FROM potions 
                            WHERE sku = :sku"""),
                            [{"sku":item_sku}]).fetchall()[0]
        price = potion_data.price
        inv_quantity = potion_data.price

        # check inventory quantity against cart
        cart_quantity = cart_item.quantity
        if inv_quantity >= cart_quantity:
            # subtract quantity from inventory
            connection.execute(
                sqlalchemy.text("""
                                UPDATE potions 
                                SET quantity = quantity - :cart
                                WHERE sku=:sku
                                """), 
                                [{"cart":cart_item.quantity, 
                                  "sku":item_sku}])
            # insert new cart_item row with sku, cart_id, quantity 
            connection.execute(
                sqlalchemy.text("""
                                INSERT INTO cart_items (cart_id, item_sku, quantity, cost) 
                                VALUES (:id, :sku, :quantity, :cost)
                                """), 
                                [{"id":cart_id, "sku":item_sku, "quantity":cart_quantity, "cost":price}])
            
            return "OK"
        else:
            return "Not enough potions in inventory."


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    #Version 2: 
    # checks out all rows of the given cart_id
    # determines total price from potions database (sku) * quantity
    # updates gold in global inventory
    # deletes rows from cart_items and carts 
    # carts and cart_items will be used to update customer database
    if (orders.validate_order(cart_id)) == False:
        with db.engine.begin() as connection:
            # select cart_item rows corresponding to cart_id
            items = connection.execute(
                sqlalchemy.text(
                    "SELECT * FROM cart_items WHERE cart_id = :id"),
                    [{"id":cart_id}]).fetchall()
            total_price = 0
            total_quantity = 0

            #post order to orders (transactions) 
            order_id = connection.execute(
                    sqlalchemy.text(
                        """INSERT INTO orders 
                            (variety, quantity, gold_change, order_id)
                            VALUES (:variety, :quantity, :gold_change, :order_id)
                            RETURNING id
                            """),
                    [{"variety" : "Checkout", 
                      "quantity":total_quantity,
                      "gold_change":total_price,
                      "order_id":cart_id}]).scalar_one()

            # for each item, total the price and retrieve relevant info
            for cart_item in items:
                item_sku = cart_item.item_sku 
                quantity = cart_item.quantity
                potion_info = connection.execute(
                    sqlalchemy.text(
                        "SELECT price, types FROM potions WHERE sku = :sku"),
                        [{"sku":item_sku}]
                        ).fetchall()[0]
                price = potion_info.price * quantity
                total_quantity += quantity
                total_price += price

                #post item to potion ledger
                name = connection.execute(
                    sqlalchemy.text("""SELECT name FROM carts WHERE cart_id = :id"""),
                    [{"id":cart_id}]
                ).scalar_one()
                connection.execute(
                    sqlalchemy.text(
                        """INSERT INTO ledger_potions
                                    (order_id, type, quantity, price, sku, name) 
                                    VALUES (:order_id, :type, :quantity, :price, :sku, (SELECT name FROM carts WHERE cart_id = :cart_id))"""),
                                    [{"order_id":order_id, 
                                      "type":potion_info.types, 
                                      "quantity":quantity,
                                      "price":price,
                                      "sku":item_sku,
                                      "cart_id":cart_id}])
            #post to gold ledger
            connection.execute(
                sqlalchemy.text("""
                                INSERT INTO ledger_gold
                                (quantity, order_id)
                                VALUES (:gold, :id)
                                """),
                                [{"id":order_id,
                                  "gold":total_price}]
            )
            #update inventory gold with price 
            connection.execute(
                sqlalchemy.text("""
                                UPDATE global_inventory SET
                                gold = gold + :price"""),
                                [{"price":total_price}])
            #log customer/item data
            clients.log_checkout(cart_id)
            # delete the client's row from cart_items and carts
            connection.execute(
                sqlalchemy.text("""
                                DELETE FROM cart_items 
                                WHERE cart_id = :id;
                                
                                DELETE FROM carts
                                WHERE cart_id = :id;"""),
                                [{"id":cart_id}])
        return_statement = {"total_potions_bought": total_quantity, "total_gold_paid": 
                total_price}
        print(return_statement)
        #orders.post_order(variety="Checkout",gold_change=total_price,order_id=cart_id,quantity=total_quantity)
        return return_statement