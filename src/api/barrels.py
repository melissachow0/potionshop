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
            change_red = 0
            change_green = 0
            change_blue = 0
            change_black = 0

            if barrel.potion_type[0]== 1:
                num_ml = "change_red"
                change_red = barrel.ml_per_barrel * barrel.quantity
            elif barrel.potion_type[1] == 1:
                num_ml = "change_green"
                change_green = barrel.ml_per_barrel * barrel.quantity
            elif barrel.potion_type[2] == 1:
                num_ml = "change_blue"
                change_blue = barrel.ml_per_barrel * barrel.quantity
            elif barrel.potion_type[3] == 1:
                num_ml = "change_black"
                change_black = barrel.ml_per_barrel * barrel.quantity
            else:
                raise Exception("Invalid potion type")
            
            if num_ml:
                    ml = connection.execute(sqlalchemy.text(f"SELECT SUM({num_ml}) FROM ml_ledger"), {"num_ml": num_ml}).scalar() #ask about this
                    ml += (barrel.ml_per_barrel * barrel.quantity)
                    gold = connection.execute(sqlalchemy.text("SELECT SUM(change) FROM gold_ledger")).scalar()
                    gold -= (barrel.price * barrel.quantity)
                    connection.execute(sqlalchemy.text("INSERT INTO gold_ledger (change) VALUES (:change)"), 
                    [{"change": - (barrel.price * barrel.quantity) }])
                    connection.execute(sqlalchemy.text("INSERT INTO ml_ledger (change_red, change_green, change_blue, change_black ) VALUES (:change_red, :change_green, :change_blue, :change_black)"), 
                    [{"change_red": change_red, "change_green": change_green, "change_blue": change_blue, "change_black": change_black }])


                

        connection.commit()

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    sorted_barrels = sorted(wholesale_catalog, key=lambda x: x.ml_per_barrel,reverse=True)
    #have to add logic for capacity
    #check this logic again
    print(sorted_barrels)
    barrels = []
    
    with db.engine.begin() as connection:
        total_ml = connection.execute(sqlalchemy.text("SELECT SUM(change_red + change_green + change_blue + change_black) FROM ml_ledger")).scalar_one()
        ml_capacity = connection.execute(sqlalchemy.text("SELECT ml_capacity FROM capacity")).scalar()
        ml_capacity = ml_capacity * 10000
        gold = connection.execute(sqlalchemy.text("SELECT SUM(change) FROM gold_ledger")).scalar()
        potion_capacity = connection.execute(sqlalchemy.text("SELECT potion_capacity FROM capacity")).scalar()
        potion_capacity = potion_capacity * 50
        
        
        big_barrel_quantity = 0
        for barrel in sorted_barrels:
            if barrel.ml_per_barrel == sorted_barrels[0].ml_per_barrel:
                big_barrel_quantity += 1

        biggest_barrel = sorted_barrels[0].price * big_barrel_quantity
        min_quantity = max(gold//biggest_barrel, 1)


        #this code should prioritize buying medium barrels in order to bring price down

        for barrel in sorted_barrels:
            sku = 0
            if barrel.potion_type[0]== 1:
                sku = "RED_POTION"
    
            elif barrel.potion_type[1] == 1:
                sku = "GREEN_POTION"
            
            elif barrel.potion_type[2] == 1:
                sku = "BLUE_POTION"
           
            elif barrel.potion_type[3] == 1:
                sku = "BLACK_POTION"
     
            else:
                raise Exception("Invalid potion type")
            
            if sku:
                    potions = connection.execute(sqlalchemy.text("SELECT quantity FROM potions WHERE sku =:sku "),{"sku": sku}).scalar()

                    if potions < (potion_capacity//4):
                        # minimum between how much they offer, how much you can afford and 1
                        quantity = min(barrel.quantity, min_quantity, gold//barrel.price) # will always be equal or less than 1
                        gold -= barrel.price * quantity
                        if quantity > 0 and (total_ml + quantity * barrel.ml_per_barrel) < ml_capacity:
                            barrels.append({"sku": barrel.sku, "quantity": quantity,})
                            total_ml += (quantity * barrel.ml_per_barrel)


    return barrels

