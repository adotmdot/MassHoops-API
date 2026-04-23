from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase


def build_sql_database():
    """
    Create a simple local SQLite database connection
    """
    engine = create_engine("sqlite:///basketball.db")

    return SQLDatabase(engine)