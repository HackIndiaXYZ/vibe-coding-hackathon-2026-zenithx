import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGODB_URI")

try:
    client = MongoClient(MONGO_URI)
    client.admin.command("ping")  # verify connection
    print("✅ MongoDB connected")
except Exception as e:
    print("❌ MongoDB error:", e)