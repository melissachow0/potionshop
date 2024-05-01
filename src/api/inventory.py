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
        # total_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_green_ml + num_red_ml + num_blue_ml + num_dark_ml) FROM global_inventory")).scalar()
        # gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        # total_potions = connection.execute(sqlalchemy.text( """
        #         SELECT SUM(quantity) 
        #         FROM potions 
        #         """
        #     )).scalar()
        total_potions = connection.execute(sqlalchemy.text( """
               SELECT SUM(change) 
                FROM potions_ledger
                """
                                                           
            )).scalar()
        gold = connection.execute(sqlalchemy.text( """
               SELECT SUM(change) 
                FROM gold_ledger
                """
                                                           
            )).scalar()
        total_ml = connection.execute(sqlalchemy.text( """
               SELECT SUM(change_red + change_green + change_blue + change_black) 
                FROM ml_ledger
                """
                                                           
            )).scalar()
    
    
    
    return {"number_of_potions": total_potions, "ml_in_barrels": total_ml, "gold": gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    potion_quantity = 0
    ml_quantity = 0

    with db.engine.begin() as connection:
        ml_capacity, potion_capacity = connection.execute(sqlalchemy.text("SELECT ml_capacity, potion_capacity FROM capacity")).first()
        total_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_green_ml + num_red_ml + num_blue_ml + num_dark_ml) FROM global_inventory")).scalar()
        total_potions = connection.execute(sqlalchemy.text( """
                SELECT SUM(quantity) 
                FROM potions 
                """
            )).scalar()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

        if gold > 1000:
            ml_capacity = ml_capacity * 10000
            potion_capacity = potion_capacity * 50
            ml_threshold = total_ml/ml_capacity
            potion_threshold = total_potions/potion_capacity

    
            if potion_threshold > .8:
                potion_quantity = 1
                connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold - 1000"))
            elif ml_threshold > .8:
                ml_quantity = 1
                connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold - 1000"))
        

        


    return {
        "potion_capacity": potion_quantity,
        "ml_capacity": ml_quantity
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

    paid = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold - :paid"), {"paid": paid})
        connection.execute(sqlalchemy.text("""UPDATE capacity SET 
                                           ml_capacity = ml_capacity + :ml_bought,
                                           potion_capacity = potion_capacity + :potions_bought"""), [{"ml_bought":  capacity_purchase.ml_capacity, "potions_bought": capacity_purchase.potion_capacity}])


    return "OK"
