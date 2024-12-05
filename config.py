import os
from dotenv import load_dotenv

# Ladda in miljövariabler från .env-filen
load_dotenv()

class Config:
    # Azure SQL Database anslutningsinformation
    SQL_SERVER = os.getenv("AZURE_SQL_SERVER")
    SQL_DATABASE = os.getenv("AZURE_SQL_DATABASE")
    SQL_USERNAME = os.getenv("AZURE_SQL_USERNAME")
    SQL_PASSWORD = os.getenv("AZURE_SQL_PASSWORD")
    SQL_DRIVER = "{ODBC Driver 18 for SQL Server}"

    # Flask konfiguration
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")  # För sessionhantering och säkerhet
