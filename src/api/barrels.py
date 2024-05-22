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

    print(sorted_barrels)
    barrels = []
    
    with db.engine.begin() as connection:
        total_ml = connection.execute(sqlalchemy.text("SELECT SUM(change_red + change_green + change_blue + change_black) FROM ml_ledger")).scalar_one()
        ml_capacity = connection.execute(sqlalchemy.text("SELECT ml_capacity FROM capacity")).scalar()
        ml_capacity = ml_capacity * 10000
        gold = connection.execute(sqlalchemy.text("SELECT SUM(change) FROM gold_ledger")).scalar()
        potion_capacity = connection.execute(sqlalchemy.text("SELECT potion_capacity FROM capacity")).scalar()
        day = connection.execute(sqlalchemy.text("SELECT day FROM weekday")).scalar_one()
        potion_type = connection.execute(sqlalchemy.text("SELECT SUM(red) AS red, SUM(green) AS green, SUM(blue) AS blue, SUM(dark) as dark FROM class_analytics WHERE day = :day "), {"day": day}).fetchone() 
        potion_capacity = potion_capacity * 50
        barrel_type = [min(1, potion_type.red), min(1, potion_type.green), min(1, potion_type.blue), min(1, potion_type.dark)]
       
        
        
        #check how many of the colors that are needed that day are available
        big_barrel_quantity = 0
        for barrel in sorted_barrels:
            if barrel.ml_per_barrel == sorted_barrels[0].ml_per_barrel: #checking if the barrel is the biggest barrel available
                #if barrel is the biggest, it checks if that day that color is bought
                if barrel.potion_type[0] == barrel_type[0] == 1:
                        big_barrel_quantity += 1
                elif barrel.potion_type[1] == barrel_type[1] == 1:
                        big_barrel_quantity += 1
                elif barrel.potion_type[2] == barrel_type[2] == 1:
                        big_barrel_quantity += 1
                elif barrel.potion_type[3] == barrel_type[3] == 1:
                        big_barrel_quantity += 1 
                else:
                    big_barrel_quantity += 0
                            


        biggest_barrel = sorted_barrels[0].price * big_barrel_quantity
        if biggest_barrel > 0:
            min_quantity = max(gold//biggest_barrel, 1)
            max_quantity =  ((ml_capacity - total_ml)//barrel.ml_per_barrel)//big_barrel_quantity
        else:
            min_quantity = 0

       #distribute the colors available properly
        for barrel in sorted_barrels:
            buy = False
            if barrel.potion_type[0]== barrel_type[0] == 1:
                buy = True 
                
            elif barrel.potion_type[1] == barrel_type[1] == 1:
                buy = True
            
            elif barrel.potion_type[2] == barrel_type[2] == 1:
                buy = True
           
            elif barrel.potion_type[3] == barrel_type[3] == 1:
                buy = True
     
            else:
                buy = False
            
            if buy:
                if barrel.ml_per_barrel == sorted_barrels[0].ml_per_barrel:
                     quantity = min(barrel.quantity, min_quantity, gold//barrel.price, max_quantity) 
                else:
                    quantity = min(barrel.quantity, gold//barrel.price) 
                if quantity > 0:
                    if (total_ml + quantity * barrel.ml_per_barrel) < ml_capacity:
                        barrels.append({"sku": barrel.sku, "quantity": quantity,})
                        total_ml += (quantity * barrel.ml_per_barrel)
                        gold -= barrel.price * quantity
                    else:
                        quantity = (ml_capacity - total_ml)//barrel.ml_per_barrel
                        if quantity > 0:
                            barrels.append({"sku": barrel.sku, "quantity": quantity,})
                            total_ml += (quantity * barrel.ml_per_barrel)
                            gold -= barrel.price * quantity
                         
                        
                

       #check how many big barrels are available
        big_barrel_quantity = 0
        for barrel in sorted_barrels:
            if barrel.ml_per_barrel == sorted_barrels[0].ml_per_barrel: #checking if the barrel is the biggest barrel available
                #if barrel is the biggest, it checks if that day that color is bought
                if barrel.potion_type[0] == 1:
                    big_barrel_quantity += 1
                elif barrel.potion_type[1] == 1:
                    big_barrel_quantity += 1
                elif barrel.potion_type[2] == 1:
                    big_barrel_quantity += 1
                elif barrel.potion_type[3] == 1:
                    big_barrel_quantity += 1 
                else:
                    big_barrel_quantity += 0
        
        biggest_barrel = sorted_barrels[0].price * big_barrel_quantity
        min_quantity = max(gold//biggest_barrel, 1)

        #buy as many of big barrels as there are available
        #if not big barrels buy as many as 2
        for barrel in sorted_barrels:
            if barrel.ml_per_barrel == sorted_barrels[0].ml_per_barrel: 
                quantity = min(barrel.quantity, gold // barrel.price, min_quantity) 
            else:
                quantity = min(barrel.quantity, gold // barrel.price, 2) 

            if quantity > 0:
                if (total_ml + quantity * barrel.ml_per_barrel) >= ml_capacity:
                    quantity = (ml_capacity - total_ml) // barrel.ml_per_barrel

                if quantity > 0:  # Only proceed if the quantity is positive
                    # Find the index of the item if it already exists in the list
                    for item in barrels:
                        if item['sku'] == barrel.sku:
                            max_quantity = barrel.quantity - item['quantity']
                            quantity = min(quantity, gold // barrel.price, min_quantity, max_quantity)
                            item['quantity'] += quantity
                            break
                    else:
                        # If the item does not exist, add it to the list
                        barrels.append({"sku": barrel.sku, "quantity": quantity})

                    total_ml += (quantity * barrel.ml_per_barrel)
                    gold -= barrel.price * quantity



    return barrels

