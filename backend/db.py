import os
import oracledb
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_db_connection():
    connection = oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PWD"),
        dsn=os.getenv("ORACLE_DSN")
    )
    return connection
