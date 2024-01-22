import os
import psycopg2
import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine

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


def get_engine():
    db_uri = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost:5432/{os.getenv('DB_NAME')}"
    engine = create_engine(db_uri)

    return engine
