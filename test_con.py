from src.database.connection import get_connection



conn = get_connection()

print("✅ Connected to PostgreSQL")

conn.close()