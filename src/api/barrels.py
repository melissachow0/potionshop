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
                connection.execute(sqlalchemy.text("INSERT INTO barrels (order_id, sku, ml_per_barrel, price, quantity, price_per_unit) VALUES (:order_id, :sku, :ml_per_barrel, :price, :quantity, :unit)"), 
                [{"order_id": order_id, "sku": barrel.sku, "ml_per_barrel": barrel.ml_per_barrel, "price": barrel.price, "quantity": barrel.quantity, "unit": barrel.price/barrel.ml_per_barrel}])
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
                    gold -= (barrel.price * barrel.quantity)
                    connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = :gold"), {"gold": gold})
                

        connection.commit()

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    #have to add logic for capacity
    #check this logic again
    print(wholesale_catalog)
    barrels = []
    
    with db.engine.begin() as connection:
        total_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_green_ml + num_red_ml + num_blue_ml + num_dark_ml) FROM global_inventory")).scalar()
        ml_capacity = connection.execute(sqlalchemy.text("SELECT ml_capacity FROM capacity")).scalar()
        ml_capacity = ml_capacity * 10000
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

        #this code should prioritize buying medium barrels in order to bring price down

        for barrel in wholesale_catalog:
            sku = 0
            if barrel.potion_type[0]== 1:
                sku = "RED_POTION"
                barrel_sku = "MEDIUM_RED_BARREL"
            elif barrel.potion_type[1] == 1:
                sku = "GREEN_POTION"
                barrel_sku = "MEDIUM_GREEN_BARREL"
            elif barrel.potion_type[2] == 1:
                sku = "BLUE_POTION"
                barrel_sku = "MEDIUM_BLUE_BARREL"
            elif barrel.potion_type[3] == 1:
                sku = "BLACK_POTION"
                barrel_sku = "MEDIUM_DARK_BARREL"
            else:
                raise Exception("Invalid potion type")
            
            if sku:
                    potions = connection.execute(sqlalchemy.text("SELECT quantity FROM potions WHERE sku =:sku "),{"sku": sku}).scalar()

                    if potions < 5 and barrel.sku == barrel_sku:
                        # minimum between how much they offer, how much you can afford and 1
                        quantity = min(barrel.quantity, 1, gold//barrel.price) # will always be equal or less than 1
                        gold -= barrel.price * quantity
                        if quantity > 0 and (total_ml + quantity * barrel.ml_per_barrel) < ml_capacity:
                            barrels.append({"sku": barrel.sku, "quantity": quantity,})
                            total_ml += (quantity * barrel.ml_per_barrel)
    
        for barrel in wholesale_catalog:
            sku = 0
            if barrel.potion_type[0]== 1:
                sku = "RED_POTION"
                barrel_sku = "MEDIUM_RED_BARREL"
            elif barrel.potion_type[1] == 1:
                sku = "GREEN_POTION"
                barrel_sku = "MEDIUM_GREEN_BARREL"
            elif barrel.potion_type[2] == 1:
                sku = "BLUE_POTION"
                barrel_sku = "MEDIUM_BLUE_BARREL"
            elif barrel.potion_type[3] == 1:
                sku = "BLACK_POTION"
                barrel_sku = "MEDIUM_DARK_BARREL"
            else:
                raise Exception("Invalid potion type")
            
            if sku:
                    potions = connection.execute(sqlalchemy.text("SELECT quantity FROM potions WHERE sku =:sku "),{"sku": sku}).scalar()

                    if potions < 5 and barrel.sku != barrel_sku:
                        # minimum between how much they offer, how much you can afford and 1
                        quantity = min(barrel.quantity, 1, gold//barrel.price) # will always be equal or less than 1
                        gold -= barrel.price * quantity
                        if quantity > 0 and (total_ml + quantity * barrel.ml_per_barrel) < ml_capacity:
                            barrels.append({"sku": barrel.sku, "quantity": quantity,})
                            total_ml += (quantity * barrel.ml_per_barrel)

    return barrels

