from fastapi import APIRouter
import sqlalchemy
from src import database as db




router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    count = 0
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT * FROM potions ORDER BY quantity DESC")).fetchall()
       

    catalog = []
    for potion in potions:
        if count >= 6: #maximum of six items can be display
            break
        if potion.quantity > 0:
            count += 1
            catalog.append({ "sku": potion.sku,
                "name": potion.name,
                "quantity": potion.quantity,
                "price": potion.price,
                "potion_type": [potion.red, potion.green , potion.blue, potion.dark],})

    return catalog
