import sqlalchemy
from src import database as db
from src.api import info

def day_potions():
    # get day
    day = info.current_day()
    with db.engine.begin() as connection:
        print(day)
        # joins calendar with potions inventory
        # selects relevent columns for bottle planning
        # sorts by priority
        result = connection.execute(
            sqlalchemy.text("""
                            WITH top_potions AS (
                                SELECT type, day, rank, day_avg
                                FROM calendar
                                WHERE day = :day)
                            SELECT sku, coalesce(rank,0) as rank, exp, types, quantity, name, Coalesce(day_avg, 0) as avg
                            FROM potions
                            LEFT JOIN top_potions
                                ON potions.types = top_potions.type
                            ORDER BY exp DESC, rank DESC
                            LIMIT 12"""),
                            [{"day":day}]).fetchall()
        return result


