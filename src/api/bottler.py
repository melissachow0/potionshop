from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db



router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    red_ml = 0
    blue_ml = 0
    green_ml = 0
    dark_ml = 0

    with db.engine.begin() as connection:

        for potion in potions_delivered:
            red_ml += (potion.potion_type[0] * potion.quantity)
            green_ml += (potion.potion_type[1] * potion.quantity)
            blue_ml += (potion.potion_type[2] * potion.quantity)
            dark_ml += (potion.potion_type[3] * potion.quantity)

            connection.execute(sqlalchemy.text (
                """
                UPDATE potions
                SET quantity = potions.quantity + :quantity
                WHERE potions.red = :red 
                and potions.green = :green 
                and potions.blue = :blue
                and potions.dark = :dark
                """
            ), {"quantity": potion.quantity, "red": potion.potion_type[0], "green": potion.potion_type[1], "blue": potion.potion_type[2], "dark": potion.potion_type[3]})

            connection.execute(sqlalchemy.text("INSERT INTO potions_ledger (change, red, green,blue, black ) VALUES (:change, :red, :green, :blue, :black)"), 
                    [{"change": potion.quantity, "red": potion.potion_type[0], "green": potion.potion_type[1], "blue":potion.potion_type[2], "black": potion.potion_type[3] }])

        connection.execute(sqlalchemy.text("INSERT INTO ml_ledger (change_red, change_green, change_blue, change_black ) VALUES (:change_red, :change_green, :change_blue, :change_black)"), 
                    [{"change_red": -red_ml, "change_green":- green_ml, "change_blue": -blue_ml, "change_black": -dark_ml }])

   

    print(f"potions delivered: {potions_delivered} order_id: {order_id}")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.

    potions_available = []

    with db.engine.begin() as connection:
             total_potions = connection.execute(sqlalchemy.text( """
                SELECT SUM(quantity) 
                FROM potions 
                """
            )).scalar() 
             potion_capacity = connection.execute(sqlalchemy.text("SELECT potion_capacity FROM capacity")).scalar()
             potion_capacity = potion_capacity * 50
             # use .first() and also gather all these in one single call
             red_ml, green_ml, blue_ml, dark_ml = connection.execute(sqlalchemy.text("SELECT SUM(change_red), SUM(change_green), SUM(change_blue), SUM(change_black) FROM ml_ledger")).first()
             potions = connection.execute(sqlalchemy.text("SELECT * FROM potions WHERE quantity < max_quantity ORDER BY RANDOM()")).fetchall()
             total_ml = red_ml + green_ml + blue_ml + dark_ml
             total_ml = total_ml//100 #how many potions can be made with ml available
             
    potion_plan = {}
    for potion in potions:
        colors = []
        if potion.red > 0:
            colors.append(red_ml//potion.red)
        if potion.blue > 0:
            colors.append(blue_ml//potion.blue)
        if potion.green > 0:
            colors.append(green_ml//potion.green)
        if potion.dark > 0:
            colors.append(dark_ml//potion.dark)
        quantity = min(colors)
        if quantity > 0:
            potions_available.append(potion) #gathering how many types of potions can be made

    for potion in potions_available:
        colors = []
        if potion.red > 0:
            colors.append(red_ml//potion.red)
        if potion.blue > 0:
            colors.append(blue_ml//potion.blue)
        if potion.green > 0:
            colors.append(green_ml//potion.green)
        if potion.dark > 0:
            colors.append(dark_ml//potion.dark)
        available = min(colors)
        quantity = min(available, total_ml//len(potions_available)) #limiting the amount of potions that can be made depending on ml available and types that can be made to diversify potions

        if quantity > 0 and total_potions != potion_capacity:
            if (quantity + total_potions) < potion_capacity:
                red_ml -= (potion.red * quantity)
                blue_ml -= (potion.blue * quantity)
                green_ml -= (potion.green * quantity)
                dark_ml -= (potion.dark * quantity)
                potion_plan[potion.red, potion.green, potion.blue, potion.dark] = quantity
                total_potions += quantity
            else:
                potion_plan[potion.red, potion.green, potion.blue, potion.dark] = potion_capacity - total_potions
                total_potions = potion_capacity
    
    for potion in potions_available:
        colors = []
        if potion.red > 0:
            colors.append(red_ml//potion.red)
        if potion.blue > 0:
            colors.append(blue_ml//potion.blue)
        if potion.green > 0:
            colors.append(green_ml//potion.green)
        if potion.dark > 0:
            colors.append(dark_ml//potion.dark)
        quantity = min(colors)
        
        if quantity > 0 and total_potions != potion_capacity:
            if (quantity + total_potions) < potion_capacity:
                red_ml -= (potion.red * quantity)
                blue_ml -= (potion.blue * quantity)
                green_ml -= (potion.green * quantity)
                dark_ml -= (potion.dark * quantity)
                potion_plan[potion.red, potion.green, potion.blue, potion.dark] += quantity
                total_potions += quantity
            else:
                potion_plan[potion.red, potion.green, potion.blue, potion.dark] += (potion_capacity - total_potions)
                total_potions = potion_capacity

    potions_quantity = []
    key_value_pairs = potion_plan.items()
    for key, value in key_value_pairs:
        potions_quantity.append({
                        "potion_type": key,
                        "quantity": value,
                    })

                
    return potions_quantity #does it make sense to only offer as many as can be made or should the deliver potions focus on that logic
             
                 
            

if __name__ == "__main__":
    print(get_bottle_plan())