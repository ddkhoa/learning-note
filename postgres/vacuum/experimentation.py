import os
from time import sleep
from typing import Literal
import psycopg2
import datetime
from dotenv import load_dotenv

load_dotenv()


def print_log(message: str) -> None:
    current_timestamp = datetime.datetime.now(datetime.timezone.utc)
    formatted_timestamp = current_timestamp.strftime("%d-%m-%y %H:%M:%S.%fZ")
    print(f"[{formatted_timestamp}] {message}")


def connect_db():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
        print_log("Connected to db!")
        return connection
    except psycopg2.Error as e:
        print_log(f"Error connecting to database: {e}")
        exit(1)


def experimentation_vacuum(*, where_to_delete=Literal["middle", "end"]):
    print_log(
        f"Running experimentation of VACUUM command. Delete rows at the {where_to_delete} of the table."
    )
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS test;")
    cursor.execute("CREATE TABLE test (id int8);")
    cursor.execute("ALTER TABLE test SET (autovacuum_enabled = false);")
    cursor.execute("INSERT INTO test (SELECT * FROM GENERATE_SERIES(1, 100000));")
    connection.commit()
    print_log(f"Table size : {capture_table_size(cursor, 'test')}")

    delete_sql_middle = "DELETE FROM test WHERE (id >= 20000 AND id <= 45000) OR (id >= 70000 AND id <= 95000);"
    delete_sql_end = "DELETE FROM test WHERE id > 50000;"
    delete_sql = delete_sql_middle if where_to_delete == "middle" else delete_sql_end
    cursor.execute(delete_sql)
    connection.commit()
    print_log(f"Table size after delete: {capture_table_size(cursor, 'test')}")

    connection.set_isolation_level(0)
    cursor.execute("VACUUM test;")
    sleep(5)
    print_log(f"Table size after vacuum: {capture_table_size(cursor, 'test')}")

    cursor.execute("INSERT INTO test (SELECT * FROM GENERATE_SERIES(100001, 150000));")
    connection.commit()
    print_log(f"Table size after inserting 1: {capture_table_size(cursor, 'test')}")

    cursor.execute("INSERT INTO test (SELECT * FROM GENERATE_SERIES(150001, 160001));")
    connection.commit()
    print_log(f"Table size after inserting 2: {capture_table_size(cursor, 'test')}")


def experimentation_vacuum_index_cleanup_delete_rows(*, reinsert_same_data: bool):
    print_log(
        f"Running experimentation of VACUUM command with INDEX_CLEANUP. Delete rows then insert the {'same' if reinsert_same_data else 'different'} data."
    )
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS test;")
    cursor.execute("CREATE TABLE test (id int8);")
    cursor.execute("ALTER TABLE test SET (autovacuum_enabled = false);")
    cursor.execute("INSERT INTO test (SELECT * FROM GENERATE_SERIES(1, 100000));")
    cursor.execute("CREATE INDEX ON test USING BTREE(id);")
    connection.commit()
    print_log(f"Index size : {capture_index_size(cursor, 'test')}")

    delete_sql = "DELETE FROM test WHERE (id >= 20000 AND id <= 45000) OR (id >= 70000 AND id <= 95000);"
    cursor.execute(delete_sql)
    connection.commit()
    print_log(f"Index size after delete: {capture_index_size(cursor, 'test')}")

    connection.set_isolation_level(0)
    cursor.execute("VACUUM (INDEX_CLEANUP ON) test;")
    sleep(5)
    print_log(
        f"Index size after vacuum with index clean up: {capture_index_size(cursor, 'test')}"
    )

    if reinsert_same_data:
        cursor.execute(
            "INSERT INTO test (SELECT * FROM GENERATE_SERIES(20000, 45000));"
        )
        cursor.execute(
            "INSERT INTO test (SELECT * FROM GENERATE_SERIES(70000, 95000));"
        )
    else:
        cursor.execute(
            "INSERT INTO test (SELECT * FROM GENERATE_SERIES(100001, 150001));"
        )

    connection.commit()
    print_log(f"Index size after inserting: {capture_index_size(cursor, 'test')}")


def experimentation_vacuum_index_cleanup_update_rows():
    print_log(
        f"Running experimentation of VACUUM command with INDEX_CLEANUP. Modify rows."
    )
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS test;")
    cursor.execute("CREATE TABLE test (id int8);")
    cursor.execute("ALTER TABLE test SET (autovacuum_enabled = false);")
    cursor.execute("INSERT INTO test (SELECT * FROM GENERATE_SERIES(1, 100000));")
    cursor.execute("CREATE INDEX ON test USING BTREE(id);")
    connection.commit()
    print_log(f"Index size : {capture_index_size(cursor, 'test')}")

    update_sql = "UPDATE test SET id = id * 10 WHERE (id >= 20000 AND id <= 45000) OR (id >= 70000 AND id <= 95000);"
    cursor.execute(update_sql)
    connection.commit()
    print_log(f"Index size after update: {capture_index_size(cursor, 'test')}")

    connection.set_isolation_level(0)
    cursor.execute("VACUUM (INDEX_CLEANUP ON) test;")
    sleep(5)
    print_log(
        f"Index size after vacuum with index clean up: {capture_index_size(cursor, 'test')}"
    )


def experimentation_reindex():
    print_log(f"Running experimentation of REINDEX command.")
    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute("DROP TABLE IF EXISTS test;")
    cursor.execute("CREATE TABLE test (id int8);")
    cursor.execute("INSERT INTO test (SELECT * FROM GENERATE_SERIES(1, 100000));")
    cursor.execute("CREATE INDEX ON test USING BTREE(id);")
    connection.commit()
    print_log(f"Index size : {capture_index_size(cursor, 'test')}")

    delete_sql = "DELETE FROM test WHERE (id >= 20000 AND id <= 45000) OR (id >= 70000 AND id <= 95000);"
    cursor.execute(delete_sql)
    connection.commit()
    print_log(f"Index size after delete: {capture_index_size(cursor, 'test')}")

    connection.set_isolation_level(0)
    cursor.execute("REINDEX TABLE test;")
    sleep(5)
    print_log(f"Index size after reindex: {capture_index_size(cursor, 'test')}")

    cursor.execute("INSERT INTO test (SELECT * FROM GENERATE_SERIES(20000, 45000));")
    cursor.execute("INSERT INTO test (SELECT * FROM GENERATE_SERIES(70000, 95000));")
    connection.commit()
    print_log(f"Index size after inserting: {capture_index_size(cursor, 'test')}")


def capture_table_size(cursor, table_name: str):
    cursor.execute(f"SELECT pg_relation_size('{table_name}');")
    table_size = cursor.fetchone()
    return table_size


def capture_index_size(cursor, table_name: str):
    cursor.execute(f"SELECT pg_indexes_size('{table_name}');")
    table_size = cursor.fetchone()
    return table_size


experimentation_vacuum(where_to_delete="middle")
experimentation_vacuum(where_to_delete="end")

experimentation_vacuum_index_cleanup_delete_rows(reinsert_same_data=True)
experimentation_vacuum_index_cleanup_delete_rows(reinsert_same_data=False)
experimentation_vacuum_index_cleanup_update_rows()

experimentation_reindex()
