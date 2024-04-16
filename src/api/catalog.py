from fastapi import APIRouter
import sqlalchemy
from src import database as db




router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar_one()
        blue_potions = connection.execute(sqlalchemy.text("SELECT num_blue_potions FROM global_inventory")).scalar_one()
        red_potions = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory")).scalar_one()




    return [
            {
                "sku": "GREEN_POTION",
                "name": "green potion",
                "quantity": green_potions,
                "price": 46,
                "potion_type": [0, 100 , 0 , 0],
            },
            {
                "sku": "RED_POTION",
                "name": "red potion",
                "quantity": red_potions,
                "price": 40,
                "potion_type": [100, 0 , 0 , 0],
            },
            {
                "sku": "BLUE_POTION",
                "name": "blue potion",
                "quantity": blue_potions,
                "price": 45,
                "potion_type": [0, 0 , 100 , 0],
            }
        ]
