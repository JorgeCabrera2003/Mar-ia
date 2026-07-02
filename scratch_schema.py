import os
from dotenv import load_dotenv
import pymysql

load_dotenv("/home/gobdesarrollo/proyectos/mar-ia/.env")
conn = pymysql.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", 8086)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASS", "rootpassword"),
    database=os.getenv("DB_NAME_SYSTEM", "goobv-sistema"),
    cursorclass=pymysql.cursors.DictCursor
)
with conn.cursor() as cur:
    for t in ["producto", "categoria_producto", "preparacion", "insumo"]:
        cur.execute(f"DESCRIBE {t}")
        print(f"\n--- Schema for {t} ---")
        for col in cur.fetchall():
            print(f"{col['Field']} ({col['Type']})")
            
    cur.execute("SELECT * FROM producto LIMIT 2")
    print("\nSample producto:", cur.fetchall())
