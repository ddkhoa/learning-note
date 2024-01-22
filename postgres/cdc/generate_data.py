from datetime import datetime, timedelta
import random
from typing import Literal, Optional
from uuid import uuid4
import pandas as pd

from common import connect_db, get_engine, print_log


ORDER_FIELDS = ["market_id", "order_id", "date", "total_price", "nb_items"]
MARKET_IDS = [
    "023d941d-e921-4e87-8719-8c98f12e9f07",
    "37a9d40b-316a-4603-8b88-aacae6743fda",
    "605750bf-219b-495b-a6bb-93792ae938c8",
    "645a5463-9504-4ba6-bfaa-ea9d16f98ee0",
    "84834db8-c1b4-4e09-90cd-8bae1b4a3f0c",
    "87f6d459-9ca0-4ede-bdab-b2ec46c254cd",
    "a9fafa01-d546-452a-8384-d11b8baba0c2",
    "b364418f-691f-4809-9cf3-539c0b42b1ce",
    "b8867a62-17bf-47ed-bc1c-1c8e9391b9ba",
    "fa315f2b-43b5-4584-a321-29f6454666bd",
]


def create_table():
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS orders (
            market_id varchar,
            order_id varchar PRIMARY KEY,
            date timestamp,
            total_price int8,
            nb_items int4
        );"""
    )

    connection.commit()


def load_data():
    for market_id in MARKET_IDS:
        load_df_to_db(generate_order(market_id, "2023-01"))
        load_df_to_db(generate_order(market_id, "2023-02"))
        load_df_to_db(generate_order(market_id, "2023-03"))
        load_df_to_db(generate_order(market_id, "2023-04"))
        load_df_to_db(generate_order(market_id, "2023-05"))
        load_df_to_db(generate_order(market_id, "2023-06"))
        load_df_to_db(generate_order(market_id, "2023-07"))
        load_df_to_db(generate_order(market_id, "2023-08"))
        load_df_to_db(generate_order(market_id, "2023-09"))
        load_df_to_db(generate_order(market_id, "2023-10"))
        load_df_to_db(generate_order(market_id, "2023-11"))
        load_df_to_db(generate_order(market_id, "2023-12"))


def load_df_to_db(df: pd.DataFrame) -> None:
    engine = get_engine()
    df.to_sql("orders", con=engine, if_exists="append", index=False, method="multi")


def generate_csv(
    scenario: Literal["low_diff_ratio", "medium_diff_ratio", "high_diff_ratio"],
    market_id: str,
    year_month: str,
    nb_versions: int,
    new_orders: float,
    changed_orders: float,
) -> None:
    df = generate_order(market_id, year_month)
    df.to_csv(f"data/{scenario}/order_{market_id}_{year_month}.csv", index=False)
    current_df = df.copy()

    for i in range(1, nb_versions):
        if i > 1:
            current_df = pd.read_csv(
                f"data/{scenario}/order_{market_id}_{year_month}_updated_{i-1}.csv",
                parse_dates=[2],
            )
        for _ in range(changed_orders):
            # we have a bug if use len(current_df.index)
            changed_rows = random.randrange(len(current_df.index))
            new_value = random.randint(100, 10000)
            print_log(
                f"Update price of rows {changed_rows} to {new_value}. Length current_df: {len(current_df.index)}"
            )
            current_df.loc[changed_rows, "total_price"] = new_value

        list_new_orders = []
        for _ in range(new_orders):
            list_new_orders.append(
                {
                    "market_id": market_id,
                    "order_id": uuid4(),
                    "date": end_of_month(
                        datetime.strptime(f"{year_month}-01", "%Y-%m-%d")
                    ),
                    "total_price": random.randint(100, 10000),
                    "nb_items": random.randint(1, 20),
                }
            )
        df_new_orders = pd.DataFrame(list_new_orders)

        current_df = pd.concat([current_df, df_new_orders])
        current_df.to_csv(
            f"data/{scenario}/order_{market_id}_{year_month}_updated_{i}.csv",
            index=False,
            date_format="%Y-%m-%d",
        )


def generate_order(
    market_id: str, year_month: str, nb_orders_per_day: Optional[int] = 3_000
) -> pd.DataFrame:
    start_date = datetime.strptime(f"{year_month}-01", "%Y-%m-%d")
    end_date = end_of_month(start_date)

    date = start_date
    data = []

    while date <= end_date:
        for _ in range(1, nb_orders_per_day + 1):
            data.append(
                {
                    "market_id": market_id,
                    "order_id": uuid4(),
                    "date": date,
                    "total_price": random.randint(100, 10000),
                    "nb_items": random.randint(1, 20),
                }
            )
        try:
            date = datetime(date.year, date.month, date.day + 1)
        except:
            break

    df = pd.DataFrame(data)
    return df


def end_of_month(date: datetime) -> datetime:
    if date.month < 12:
        first_day_of_next_month = datetime(date.year, date.month + 1, 1)
    else:
        first_day_of_next_month = datetime(date.year + 1, 1, 1)

    end_of_month_date = first_day_of_next_month - timedelta(days=1)

    return end_of_month_date


# create_table()
# load_data()

# low_diff_ratio: (500 + 90) / 93000= 0.006344
# generate_csv(
#     "low_diff_ratio", "84834db8-c1b4-4e09-90cd-8bae1b4a3f0c", "2024-01", 15, 500, 90
# )

# medium_diff_ratio: (10000 + 8600) / 93000 = 0.2
# generate_csv(
#     "medium_diff_ratio",
#     "84834db8-c1b4-4e09-90cd-8bae1b4a3f0c",
#     "2024-01",
#     15,
#     10000,
#     8600,
# )

# high_diff_ratio: (22000 + 47750) / 93000 = 0,75
generate_csv(
    "high_diff_ratio",
    "84834db8-c1b4-4e09-90cd-8bae1b4a3f0c",
    "2024-01",
    15,
    22000,
    47750,
)
