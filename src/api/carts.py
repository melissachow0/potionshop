from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db



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
    results = []
    if search_page == "":
        search_page = "0"
    
    
    with db.engine.begin() as connection:
        row_number = connection.execute(sqlalchemy.text("SELECT COUNT(*) FROM search_data")).scalar_one()
        if row_number > 0:
            query = """
                SELECT id AS line_item_id, created_at AS timestamp, change, sku AS item_sku, name AS customer_name
                FROM search_data 
                """
            params = {}

            if customer_name and potion_sku:
                query += "WHERE name LIKE :name AND sku LIKE :sku"
                params["name"] = customer_name
                params["sku"] = potion_sku + "%"
            elif customer_name:
                query += "WHERE name LIKE :name"
                params["name"] = customer_name + "%"
            elif potion_sku:
                query += "WHERE sku LIKE :sku"
                params["sku"] = potion_sku + "%"

            query += " ORDER BY {} {}".format(sort_col.value, sort_order.value)

            try:
                offset = int(search_page)
            except ValueError:
                offset = 0

            query += " OFFSET :offset ROWS FETCH NEXT 5 ROWS ONLY"
            params["offset"] = offset

            rows = connection.execute(sqlalchemy.text(query), params).fetchall()

            for row in rows:
                results.append(
                    {
                        "line_item_id": row.line_item_id,
                        "item_sku": row.item_sku,
                        "customer_name": row.customer_name,
                        "line_item_total": -row.change,
                        "timestamp": row.timestamp,
                    }
                )

        previous = max(int(search_page) - 5, 0) if search_page.isdigit() else 0
        next = max(min(int(search_page) + 5, row_number - 5), 0) if search_page.isdigit() else 5

    return {
        "previous": previous,
        "next": next,
        "results": results,
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
    with db.engine.begin() as connection:
        day = connection.execute(sqlalchemy.text("SELECT day FROM weekday")).scalar_one()
        customer_id = connection.execute(sqlalchemy.text("INSERT INTO customers (name, class, level, day) VALUES (:name, :class, :level, :day) RETURNING id"), {"name": new_cart.customer_name, "class": new_cart.character_class, "level": new_cart.level, "day": day}).scalar_one()
        cart_id = connection.execute(sqlalchemy.text("INSERT INTO carts (customer, checked_out, customer_id) VALUES (:customer_name, :checked_out, :customer_id) RETURNING id"), {"customer_name": new_cart.customer_name, "checked_out": False, "customer_id": customer_id}).scalar_one()

    return {"cart_id": cart_id}




class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        potion_id = connection.execute(sqlalchemy.text("SELECT id FROM potions WHERE sku = :sku"), {"sku": item_sku}).scalar_one()
        connection.execute(sqlalchemy.text("INSERT INTO cart_items (item_sku , quantity, cart_id, potion_id) VALUES (:sku , :quantity, :cart_id, :potion_id)"), {"sku": item_sku, "quantity": cart_item.quantity, "cart_id": cart_id, "potion_id": potion_id})


    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    # you need to add checkout logic
    total_paid = 0
    total_potions = 0
    with db.engine.begin() as connection:
        day = connection.execute(sqlalchemy.text("SELECT day FROM weekday")).scalar_one()
        rows = connection.execute(sqlalchemy.text("SELECT quantity, item_sku  FROM cart_items WHERE cart_id = :cart_id"), {"cart_id": cart_id}).fetchall()
        for row in rows:
            quantity, item_sku = row
            price, stock, red, green, blue, dark=  connection.execute(sqlalchemy.text("SELECT price, quantity, red, green, blue, dark FROM potions WHERE sku = :item_sku"), {"item_sku": item_sku }).first()

            if quantity <= stock:
                total_potions += quantity
                total_paid += (quantity * price)
                connection.execute(sqlalchemy.text (
                         """
                         UPDATE potions
                         SET quantity = potions.quantity - :quantity
                         WHERE potions.sku = :sku
                         """
                     ), {"quantity": quantity, "sku": item_sku})
                connection.execute(sqlalchemy.text("INSERT INTO potions_ledger (change, red, green,blue, black, day, customer_id) VALUES (:change, :red, :green, :blue, :black, :day,( SELECT customer_id FROM carts WHERE carts.id = :id ))"), 
                    [{"change": -quantity, "red": red, "green": green, "blue":blue, "black": dark, "day": day , "id": cart_id}])
                connection.execute(sqlalchemy.text("INSERT INTO gold_ledger (change) VALUES (:change)"), 
                    [{"change":  quantity * price }])
                connection.execute(sqlalchemy.text (
                        """
                        UPDATE carts
                        SET checked_out = True
                        WHERE carts.id = :id
                        """
                    ), {"id": cart_id})

            else:
                quantity = 0

    return {"total_potions_bought": total_potions, "total_gold_paid": total_paid}

# Have a table that saves potions that are bought on a certain day and then form those potions based on days.
# So if its Monday sort potions by most popular sold on Monday and check if it can be made
# Would you use ledger to keep track of days?