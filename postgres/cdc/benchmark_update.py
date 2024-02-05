import time
from typing import Literal, TypedDict

from common import connect_db, get_engine, print_log
import pandas as pd
from sqlalchemy import text


class Stats(TypedDict):
    current_time: float
    heap_size: float
    index_size: float
    n_live_tuples: float
    n_dead_tuples: float
    n_tuples_inserted: float
    n_tuples_updated: float
    n_tuples_hot_updated: float
    n_tuples_deleted: float


def capture_stats(
    connection, table_name: str, before_or_after: Literal["before", "after"]
) -> Stats:
    if before_or_after == "after":
        current_time = time.time()

    stats = connection.execute(
        text(
            f"""
        SELECT
            (pg_relation_size(relid)) AS "heap_size",
            (pg_indexes_size(relid)) AS "index_size",
            n_live_tup AS "n_live_tuples",
            n_dead_tup AS "n_dead_tuples",
            n_tup_ins AS "n_tuples_inserted",
            n_tup_upd AS "n_tuples_updated",
            n_tup_hot_upd AS "n_tuples_hot_updated",
            n_tup_del AS "n_tuples_deleted"
            FROM
            pg_stat_user_tables t
            WHERE
            t.relname = '{table_name}';
        """
        )
    )
    stats_dict = stats.mappings().all()[0]

    if before_or_after == "before":
        current_time = time.time()

    return {"current_time": current_time, **stats_dict}


def load_data_to_tmp_table(engine, tmp_table_name: str, file: str):
    df = pd.read_csv(file, parse_dates=[2])
    df.to_sql(
        tmp_table_name, con=engine, if_exists="replace", index=False, method="multi"
    )


def update_by_replace(connection, table_name: str, tmp_table_name: str):
    connection.execute(
        text(
            f"DELETE FROM {table_name} WHERE market_id = '84834db8-c1b4-4e09-90cd-8bae1b4a3f0c' AND date >= '2024-01-01' AND date <= '2024-01-31'"
        )
    )
    connection.execute(text(f"INSERT INTO {table_name} SELECT * FROM {tmp_table_name}"))
    connection.commit()


def update_incremental(connection, table_name: str, tmp_table_name: str):
    compare_table_name = f"{tmp_table_name}_compare"
    connection.execute(
        text(
            f"CREATE TEMPORARY TABLE {compare_table_name} (LIKE {table_name} INCLUDING ALL, fingerprint varchar);"
        )
    )
    connection.execute(
        text(
            f"INSERT INTO {compare_table_name} SELECT * FROM {table_name} WHERE date >= '2024-01-01' AND date <= '2024-01-31'"
        )
    )
    connection.execute(
        text(f"ALTER TABLE {tmp_table_name} ADD COLUMN fingerprint varchar;")
    )
    connection.execute(
        text(
            f"UPDATE {tmp_table_name} SET fingerprint = CONCAT(total_price,'-',nb_items)"
        )
    )
    connection.execute(
        text(
            f"UPDATE {compare_table_name} SET fingerprint = CONCAT(total_price,'-',nb_items)"
        )
    )

    connection.execute(
        text(
            f"""DELETE FROM {table_name} WHERE order_id IN (
                SELECT comp.order_id order_id FROM {compare_table_name} comp
                LEFT JOIN {tmp_table_name} tmp
                ON comp.order_id = tmp.order_id
                WHERE tmp.order_id IS NULL
            ) """
        )
    )
    connection.execute(
        text(
            f"""INSERT INTO {table_name} 
        SELECT tmp.market_id, tmp.order_id, tmp.date, tmp.total_price, tmp.nb_items FROM {tmp_table_name} tmp 
        LEFT JOIN {compare_table_name} comp 
        ON tmp.order_id = comp.order_id
        WHERE comp.order_id IS NULL 
        OR tmp.fingerprint != comp.fingerprint
        ON CONFLICT (order_id) DO UPDATE
        SET total_price = EXCLUDED.total_price, nb_items = EXCLUDED.nb_items;"""
        )
    )
    connection.commit()


def test_update_data(
    scenario: Literal["low_diff_ratio", "medium_diff_ratio", "high_diff_ratio"],
    method: Literal["replace", "incremental"],
):
    print_log(f"Test update data using {method} method")
    stats = []
    files = [
        f"./data/{scenario}/order_84834db8-c1b4-4e09-90cd-8bae1b4a3f0c_2024-01.csv",
    ] + [
        f"./data/{scenario}/order_84834db8-c1b4-4e09-90cd-8bae1b4a3f0c_2024-01_updated_{i}.csv"
        for i in range(1, 15)
    ]
    func = update_by_replace if method == "replace" else update_incremental
    engine = get_engine()
    connection = engine.connect()
    test_table = f"orders_test_{method}"
    clone_table(connection, "orders", test_table)

    try:
        for i in range(len(files)):
            print_log(f"Update data {i + 1}")
            tmp_table = f"_tmp_{test_table}_{i}"
            load_data_to_tmp_table(engine, tmp_table, files[i])

            before = capture_stats(connection, test_table, "before")
            if i == 0:
                stats.append(
                    {
                        "heap_size": before["heap_size"],
                        "index_size": before["index_size"],
                        "n_dead_tuples": before["n_dead_tuples"],
                    }
                )
            func(connection, test_table, tmp_table)
            after = capture_stats(connection, test_table, "after")

            stats.append(
                {
                    "exec_time": after["current_time"] - before["current_time"],
                    "heap_size": after["heap_size"],
                    "index_size": after["index_size"],
                    "n_dead_tuples": after["n_dead_tuples"],
                }
            )

        df_result = pd.DataFrame(stats)
        df_result.to_csv(f"result/{scenario}/result_update_data_{method}.csv")
    except Exception as e:
        print(e)
        connection.rollback()


def clone_table(connection, source_table, target_table):
    connection.execute(text(f"DROP TABLE IF EXISTS {target_table}"))
    connection.execute(text(f"CREATE TABLE {target_table} AS TABLE {source_table};"))
    connection.execute(text(f"ALTER TABLE {target_table} ADD PRIMARY KEY (order_id);"))
    connection.commit()
    connection.execute(text(f"ANALYZE {target_table};"))
    connection.commit()


test_update_data(scenario="low_diff_ratio", method="replace")
test_update_data(scenario="low_diff_ratio", method="incremental")
test_update_data(scenario="medium_diff_ratio", method="replace")
test_update_data(scenario="medium_diff_ratio", method="incremental")
test_update_data(scenario="high_diff_ratio", method="replace")
test_update_data(scenario="high_diff_ratio", method="incremental")
