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
        green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory"))


    return [
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": green_potions,
                "price": 55,
                "potion_type": [0, 0, 100, 0],
            }
        ]
