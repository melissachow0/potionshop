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

    
        connection.execute(sqlalchemy.text(
            """
                UPDATE global_inventory SET
                num_red_ml = num_red_ml - :red_ml,
                num_green_ml = num_green_ml - :green_ml,
                num_blue_ml = num_blue_ml - :blue_ml,
                num_dark_ml = num_dark_ml - :dark_ml
            """
        ), [{"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml}])
   

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

    with db.engine.begin() as connection:
             green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()
             blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM global_inventory")).scalar()
             red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar()
             dark_ml = connection.execute(sqlalchemy.text("SELECT num_dark_ml FROM global_inventory")).scalar()
             potions = connection.execute(sqlalchemy.text("SELECT * FROM potions ORDER BY RANDOM()")).fetchall()
             
    potion_plan = []
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
            red_ml -= (potion.red * quantity)
            blue_ml -= (potion.blue * quantity)
            green_ml -= (potion.green * quantity)
            dark_ml -= (potion.dark * quantity)
            potion_plan.append({
                    "potion_type": [potion.red, potion.green, potion.blue, potion.dark],
                    "quantity": quantity,
                } )
    return potion_plan
             
                 
            

if __name__ == "__main__":
    print(get_bottle_plan())