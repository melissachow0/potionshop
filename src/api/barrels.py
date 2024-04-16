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
  

    for barrel in barrels_delivered:
        with db.engine.begin() as connection:
            green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()
            green_ml = barrel.ml_per_barrel + green_ml
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :green_ml"), {"green_ml": green_ml})
            gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
            gold = gold - barrel.price
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = :gold"), {"gold": gold})

        connection.commit()

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    barrels = []
  
    
    for barrel in wholesale_catalog:
        if barrel.potion_type[0]== 100:
            potions = "num_red_potions"
        elif barrel.potion_type[1] == 100:
            potions = "num_green_potions"
        else:
            potions = "num_blue_potions"
    
        with db.engine.begin() as connection:
            potions = connection.execute(sqlalchemy.text(f"SELECT {potions} FROM global_inventory")).scalar()
            gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

            
        if potions < 10:
            quantity = gold//barrel.price
            while quantity > barrel.quantity:
                quantity -= 1
        else:
            quantity = 0
        barrels.append({"sku": barrel.sku, "quantity": quantity})

    return barrels

