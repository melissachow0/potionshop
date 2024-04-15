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
    if wholesale_catalog.potion_type[0] == 100:
        num_ml = "num_red_ml"
    elif wholesale_catalog.potion_type[1] == 100:
        num_ml = "num_green_ml"
    else:
        num_ml = "num_blue_ml"
    
    


    with db.engine.begin() as connection:
        green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar()
        print(green_potions)
        if green_potions < 10:
            quantity = 1
        else:
           quantity = 0

    return [
        {
            "sku": "SMALL_GREEN_BARREL",
            "quantity": quantity,
        }
    ]

