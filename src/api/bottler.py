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
    
    for potion in potions_delivered:
        num_potions = 0
        num_ml = 0
        if potion.potion_type[0]== 100:
            num_potions = "num_red_potions"
            num_ml = "num_red_ml"
        elif potion.potion_type[1] == 100:
            num_potions = "num_green_potions"
            num_ml = "num_green_ml"
        elif potion.potion_type[2] == 100:
            num_potions = "num_blue_potions"
            num_ml = "num_blue_ml"
        if num_potions:
            with db.engine.begin() as connection:
                ml = connection.execute(sqlalchemy.text(f"SELECT {num_ml} FROM global_inventory")).scalar()
                if ml >= (potion.quantity * 100):
                    bottles = connection.execute(sqlalchemy.text(f"SELECT {num_potions} FROM global_inventory")).scalar()
                    bottles = potion.quantity + bottles
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET {num_potions} = :num"), {"num": bottles})
                    ml = ml - (potion.quantity * 100)
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET {num_ml} = :num"), {"num": ml})
            
                    
        


        

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
             quantity_green = green_ml//100
             quantity_blue = blue_ml//100
             quantity_red = red_ml//100
    potions = []
    if quantity_blue > 0:
        potions.append({
                "potion_type": [0, 0, 100, 0], # Blue potions
                "quantity": quantity_blue,
            })
    if quantity_red > 0:
        potions.append({
                 "potion_type": [100, 0, 0, 0], # Red potions
                 "qunatiy": quantity_red,
            })
    if quantity_green > 0:
        potions.append(
            {
                "potion_type": [0, 100, 0, 0], # Green potions
                "quantity": quantity_green,
            }
        )
    return potions
             
                 
            

if __name__ == "__main__":
    print(get_bottle_plan())