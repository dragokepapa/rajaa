import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    OWNER_ID = int(os.getenv("OWNER_ID"))   # ← Bahut important

    MAX_PLAYERS = 4
    MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", 5))

    DB_NAME = "raja_mantri.db"