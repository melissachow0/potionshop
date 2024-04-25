from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT * FROM potions WHERE quantity > 0")).fetchall()
        total_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar() 
        + connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar() + connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM global_inventory")).scalar()+connection.execute(sqlalchemy.text("SELECT num_dark_ml FROM global_inventory")).scalar()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        total_potions = 0
        for potion in potions:
            total_potions += potion.quantity
    
    return {"number_of_potions": total_potions, "ml_in_barrels": total_ml, "gold": gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"
