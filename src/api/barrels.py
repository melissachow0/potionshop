from sqlite3 import IntegrityError
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db



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
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")
    #you can select a lot of items at once in one trip
    # never do SELECT * (be specific)
    with db.engine.begin() as connection:
        try:
            for barrel in barrels_delivered:
                connection.execute(sqlalchemy.text("INSERT INTO barrels (order_id, sku, ml_per_barrel, price, quantity) VALUES (:order_id, :sku, :ml_per_barrel, :price, :quantity)"), 
                [{"order_id": order_id, "sku": barrel.sku, "ml_per_barrel": barrel.ml_per_barrel, "price": barrel.price, "quantity": barrel.quantity}])
        except IntegrityError as e:
            return "OK"


    
        for barrel in barrels_delivered:
            num_ml = 0
            if barrel.potion_type[0]== 1:
                num_ml = "num_red_ml"
            elif barrel.potion_type[1] == 1:
                num_ml = "num_green_ml"
            elif barrel.potion_type[2] == 1:
                num_ml = "num_blue_ml"
            elif barrel.potion_type[3] == 1:
                num_ml = "num_dark_ml"
            else:
                raise Exception("Invalid potion type")
            
            if num_ml:
                    ml = connection.execute(sqlalchemy.text(f"SELECT {num_ml} FROM global_inventory")).scalar()
                    ml += (barrel.ml_per_barrel * barrel.quantity)
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET {num_ml} = :ml"), { "ml": ml})
                    gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
                    gold = gold - barrel.price
                    connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = :gold"), {"gold": gold})
                

        connection.commit()

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    #check this logic again
    print(wholesale_catalog)
    barrels = []
    
    with db.engine.begin() as connection:
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
 
        for barrel in wholesale_catalog:
            potions = 0
            if barrel.potion_type[0]== 1:
                potions = "num_red_potions"
            elif barrel.potion_type[1] == 1:
                potions = "num_green_potions"
            elif barrel.potion_type[2] == 1:
                potions = "num_blue_potions"
            elif barrel.potion_type[3] == 1:
                potions = "num_dark_potions"
            else:
                raise Exception("Invalid potion type")
            
            if potions:
                    potions = connection.execute(sqlalchemy.text(f"SELECT {potions} FROM global_inventory")).scalar()

                    if potions < 5:
                        # minimum between how much they offer, how much you can afford and 2
                        quantity = min(barrel.quantity, 2, gold//barrel.price) # will always be equal or less than 2
                        gold -= barrel.price * quantity
                        if quantity > 0:
                            barrels.append({"sku": barrel.sku, "quantity": quantity,})

    return barrels

