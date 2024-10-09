from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

id_counter = 0

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
    search_page: str = "",
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

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
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
    print(customers)

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    global id_counter
    id_counter += 1

    with db.engine.begin() as connection:
        # Add row to carts table with id, name, and class
        client_class = new_cart.character_class
        client_name = new_cart.customer_name
        client_level = new_cart.level
        sql_to_execute = f"INSERT INTO current_visitors (cart_id, name, class, level) VALUES ('{id_counter}','{client_name}','{client_class}', '{client_level}')"
        connection.execute(sqlalchemy.text(sql_to_execute))
    return {"cart_id": id_counter}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        # check inventory quantity against requested quantity
        inv_quantity = connection.execute(sqlalchemy.text(f"SELECT quantity FROM potions WHERE sku = '{item_sku}'")).scalar()
        cart_quantity = cart_item.quantity
        if inv_quantity >= cart_quantity:
            # subtract quantity from inventory
            connection.execute(sqlalchemy.text(f"UPDATE potions SET quantity = '{inv_quantity - cart_quantity}' WHERE sku='{item_sku}'"))
            # insert new cart_item row with sku, cart_id, quantity 
            sql_to_execute = f"INSERT INTO cart_items (cart_id, item_sku, quantity) VALUES ('{cart_id}','{item_sku}','{cart_quantity}')"
            connection.execute(sqlalchemy.text(sql_to_execute))
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
    # deletes rows from cart_items and current_visitors 
    # current_visitors and cart_items will be used to update customer database
    with db.engine.begin() as connection:
        # select cart_item rows corresponding to cart_id
        items = connection.execute(sqlalchemy.text(f"SELECT * FROM cart_items WHERE cart_id = {cart_id}")).fetchall()
        total_price = 0
        total_quantity = 0
        # for each item, total the price
        for cart_item in items:
            item_sku = cart_item.item_sku 
            quantity = cart_item.quantity
            price = connection.execute(sqlalchemy.text(f"SELECT price FROM potions WHERE sku = '{item_sku}'")).scalar() * quantity
            total_quantity += quantity
            total_price += price

        #update inventory gold with price 
        gold_inv = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        updated_gold = gold_inv + total_price
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {updated_gold}"))
        # delete the client's row from cart_items and current_visitors
        connection.execute(sqlalchemy.text(f"DELETE FROM cart_items WHERE cart_id = {cart_id}"))
        connection.execute(sqlalchemy.text(f"DELETE FROM current_visitors where cart_id = {cart_id}"))

    return_statement = {"total_potions_bought": total_quantity, "total_gold_paid": 
            total_price}
    print(return_statement)
    return return_statement