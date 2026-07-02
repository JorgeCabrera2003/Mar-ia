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
    termino = "angel"
    condiciones_p = [
        f"(p.nombre LIKE '%{termino}%' OR p.apellido LIKE '%{termino}%' "
        f"OR CONCAT(p.nombre,' ',p.apellido) LIKE '%{termino}%')"
    ]
    where = "WHERE " + " AND ".join(condiciones_p)
    sql = f"""
        SELECT
            p.cedula,
            CONCAT(p.nombre, ' ', p.apellido)  AS nombre_completo,
            p.telefono,
            p.correo,
            CASE
                WHEN c.cedula IS NOT NULL AND e.cedula IS NOT NULL THEN 'Cliente y Empleado'
                WHEN c.cedula IS NOT NULL THEN 'Cliente'
                WHEN e.cedula IS NOT NULL THEN 'Empleado'
                ELSE 'Persona'
            END                                 AS rol
        FROM persona p
        LEFT JOIN cliente  c ON c.cedula = p.cedula
        LEFT JOIN empleado e ON e.cedula = p.cedula
        {where}
        ORDER BY p.apellido ASC
        LIMIT 50
    """
    print("SQL:", sql)
    try:
        cur.execute(sql)
        print("Resultado:", cur.fetchall())
    except Exception as e:
        print("ERROR:", e)
