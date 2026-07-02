"""
db_connector.py — Conector Dual a las Bases de Datos de SICGOV
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Principio de Ortogonalidad: cada método retorna una lista vacía
ante cualquier error de conexión o consulta. Mar-ia nunca lanza
excepciones hacia la capa de FastAPI.
"""

import os
import pymysql
import pymysql.cursors
from datetime import date
from dotenv import load_dotenv

load_dotenv()


class SICGOVConnector:
    """Gestor de conexiones duales a goobv-sistema y goobv-usuarios."""

    # ─── Configuración desde .env ─────────────────────────────────────────────
    _HOST     = os.getenv("DB_HOST", "127.0.0.1")
    _PORT     = int(os.getenv("DB_PORT", 8086))
    _USER     = os.getenv("DB_USER", "root")
    _PASS     = os.getenv("DB_PASS", "rootpassword")
    _DB_SIS   = os.getenv("DB_NAME_SYSTEM", "goobv-sistema")
    _DB_SEC   = os.getenv("DB_NAME_SECURITY", "goobv-usuarios")

    # ─── Fábrica de conexión ──────────────────────────────────────────────────

    def _conectar(self, database: str) -> pymysql.connections.Connection | None:
        """Crea y retorna una conexión PyMySQL. Retorna None si falla."""
        try:
            return pymysql.connect(
                host=self._HOST,
                port=self._PORT,
                user=self._USER,
                password=self._PASS,
                database=database,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=5,
                read_timeout=10,
            )
        except Exception as e:
            print(f"[Mar-ia][db_connector] Error de conexión a '{database}': {e}")
            return None

    def _ejecutar_query(self, database: str, sql: str, params: tuple | None = None) -> list[dict]:
        """
        Ejecuta una consulta SELECT y retorna lista de dicts.
        Siempre cierra la conexión. Ante cualquier error retorna [].
        """
        conn = self._conectar(database)
        if conn is None:
            return []
        try:
            with conn.cursor() as cur:
                if params:
                    cur.execute(sql, params)
                else:
                    cur.execute(sql)
                return cur.fetchall()
        except Exception as e:
            print(f"[Mar-ia][db_connector] Error ejecutando query: {e}")
            return []
        finally:
            conn.close()

    # ─── Intención: reporte_inventario_bajo ───────────────────────────────────

    def get_alertas_inventario(self, params=None) -> list[dict]:
        """
        Retorna insumos cuyo stock actual está por debajo del stock mínimo.
        Acepta params.limite para restringir cantidad de resultados.
        """
        limite = params.limite if params and params.limite else 50
        sql = f"SELECT * FROM vw_alertas_inventario ORDER BY stock_actual ASC LIMIT {int(limite)}"
        return self._ejecutar_query(self._DB_SIS, sql)

    # ─── Intención: reporte_asistencia_diaria ────────────────────────────────

    def get_asistencia_diaria(self, params=None) -> list[dict]:
        """
        Retorna registros de asistencia.
        Acepta params.fecha (un día) o params.fecha_inicio/fin (rango).
        """
        if params and params.es_rango:
            inicio, fin = params.rango_sql()
            cond = f"DATE(a.fecha) BETWEEN '{inicio}' AND '{fin}'"
        else:
            fecha = params.fecha_sql() if params else date.today().isoformat()
            cond  = f"DATE(a.fecha) = '{fecha}'"

        estado_cond = ""
        if params and params.estado:
            estado_cond = f"AND a.estado = '{params.estado}'"

        sql = f"""
            SELECT
                CONCAT(p.nombre, ' ', p.apellido)   AS empleado,
                a.tipo_marcacion,
                a.estado,
                a.fecha,
                c.descripcion                        AS cargo
            FROM asistencia a
            INNER JOIN empleado  e ON e.cedula = a.cedula
            INNER JOIN persona   p ON p.cedula = e.cedula
            LEFT  JOIN cargo     c ON c.id_cargo = e.id_cargo
            WHERE {cond} {estado_cond}
            ORDER BY a.fecha DESC
        """
        return self._ejecutar_query(self._DB_SIS, sql)

    # ─── Intención: reporte_reservas_hoy ─────────────────────────────────────

    def get_reservas_hoy(self, params=None) -> list[dict]:
        """
        Retorna reservaciones. Acepta:
          - params.fecha          → un día específico
          - params.fecha_inicio/fin → rango de fechas
          - params.estado         → filtrar por estado
          - params.limite         → máximo de resultados
        """
        if params and params.es_rango:
            inicio, fin = params.rango_sql()
            cond = f"DATE(r.fecha) BETWEEN '{inicio}' AND '{fin}'"
        else:
            fecha = params.fecha_sql() if params else date.today().isoformat()
            cond  = f"DATE(r.fecha) = '{fecha}'"

        estado_cond = ""
        if params and params.estado:
            estado_cond = f"AND r.estado = '{params.estado}'"

        limite = params.limite if params and params.limite else 100

        sql = f"""
            SELECT
                CONCAT(p.nombre, ' ', p.apellido)    AS cliente,
                r.fecha,
                r.hora,
                r.hora_fin,
                r.estado,
                IFNULL(m.numero_mesa, '—')            AS numero_mesa,
                IFNULL(a.nombre, '—')                 AS area
            FROM reservacion r
            INNER JOIN cliente        cl ON cl.cedula         = r.cedula_cliente
            INNER JOIN persona        p  ON p.cedula          = cl.cedula
            LEFT  JOIN asignacion_mesa am ON am.id_reservacion = r.id_reservacion
            LEFT  JOIN mesa            m  ON m.id_mesa         = am.id_mesa
            LEFT  JOIN area_mesa       a  ON a.id_area         = m.id_area
            WHERE {cond} {estado_cond}
            ORDER BY r.fecha ASC, r.hora ASC
            LIMIT {int(limite)}
        """
        return self._ejecutar_query(self._DB_SIS, sql)

    # ─── Extras: directorio y pedidos pendientes (disponibles para el futuro) ─

    def get_directorio_empleados(self, params=None) -> list[dict]:
        """Retorna empleados. Filtra por nombre, cédula o correo si se indica."""
        limite = params.limite if params and params.limite else 200

        condiciones = []
        if params and params.cedula:
            condiciones.append(f"cedula LIKE '%{params.cedula}%'")
        elif params and params.correo:
            condiciones.append(f"correo LIKE '%{params.correo}%'")
        elif params and params.telefono:
            condiciones.append(f"telefono LIKE '%{params.telefono}%'")
        elif params and params.nombre:
            termino = params.nombre.replace("'", "''")
            condiciones.append(
                f"(nombre LIKE '%{termino}%' OR apellido LIKE '%{termino}%' "
                f"OR CONCAT(nombre,' ',apellido) LIKE '%{termino}%')"
            )

        where = "WHERE " + " AND ".join(condiciones) if condiciones else ""
        sql   = f"SELECT * FROM vw_directorio_empleados {where} LIMIT {int(limite)}"
        return self._ejecutar_query(self._DB_SIS, sql)

    def buscar_persona(self, params=None) -> list[dict]:
        """
        Búsqueda cruzada de una persona en clientes Y empleados.
        Útil cuando el usuario pregunta ''¿existe Juan González?''
        sin especificar si es cliente o empleado.
        """
        condiciones_p = []
        if params and params.cedula:
            condiciones_p.append(f"p.cedula LIKE '%{params.cedula}%'")
        elif params and params.correo:
            condiciones_p.append(f"p.correo LIKE '%{params.correo}%'")
        elif params and params.telefono:
            condiciones_p.append(f"p.telefono LIKE '%{params.telefono}%'")
        elif params and params.nombre:
            termino = params.nombre.replace("'", "''")
            condiciones_p.append(
                f"(p.nombre LIKE '%{termino}%' OR p.apellido LIKE '%{termino}%' "
                f"OR CONCAT(p.nombre,' ',p.apellido) LIKE '%{termino}%')"
            )

        where = "WHERE " + " AND ".join(condiciones_p) if condiciones_p else "WHERE 1=1"

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
        return self._ejecutar_query(self._DB_SIS, sql)

    def get_clientes(self, params=None) -> list[dict]:
        """Retorna clientes. Filtra por nombre, cédula, correo o teléfono si se indica."""
        limite = params.limite if params and params.limite else 200

        condiciones = []
        if params and params.cedula:
            condiciones.append(f"p.cedula LIKE '%{params.cedula}%'")
        elif params and params.correo:
            condiciones.append(f"p.correo LIKE '%{params.correo}%'")
        elif params and params.telefono:
            condiciones.append(f"p.telefono LIKE '%{params.telefono}%'")
        elif params and params.nombre:
            termino = params.nombre.replace("'", "''")  # escapar comillas
            condiciones.append(
                f"(p.nombre LIKE '%{termino}%' OR p.apellido LIKE '%{termino}%' "
                f"OR CONCAT(p.nombre,' ',p.apellido) LIKE '%{termino}%')"
            )

        where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

        sql = f"""
            SELECT
                p.cedula,
                CONCAT(p.nombre, ' ', p.apellido) AS nombre_completo,
                p.telefono,
                p.correo,
                c.fecha_registro
            FROM cliente c
            INNER JOIN persona p ON p.cedula = c.cedula
            {where}
            ORDER BY p.apellido ASC
            LIMIT {int(limite)}
        """
        return self._ejecutar_query(self._DB_SIS, sql)

    def get_platillos(self, params=None) -> list[dict]:
        """
        Retorna los productos (platillos) del menú.
        Filtra por categoría, ingredientes, precio máximo y si permite extras (es_personalizable).
        """
        condiciones = ["p.estatus = 1"]
        if params:
            if params.categoria_prod:
                # Si viene "POSTRE" buscará en el enum tipo_producto o en la tabla categoría.
                cat = params.categoria_prod.replace("'", "''")
                condiciones.append(f"(p.tipo_producto LIKE '%{cat}%' OR c.nombre_categoria LIKE '%{cat}%')")
            
            if params.ingrediente:
                ing = params.ingrediente.replace("'", "''")
                condiciones.append(f"i.nombre_insumo LIKE '%{ing}%'")
                
            if params.precio_max is not None:
                condiciones.append(f"p.precio <= {params.precio_max}")
                
            if params.con_extras:
                condiciones.append("p.es_personalizable = 1")
                
        where = "WHERE " + " AND ".join(condiciones)
        limite = params.limite if params and params.limite else 50
        
        # Se requiere DISTINCT porque el JOIN con insumos puede multiplicar las filas
        sql = f"""
            SELECT DISTINCT
                p.nombre_producto AS nombre,
                COALESCE(c.nombre_categoria, p.tipo_producto) AS categoria,
                p.precio,
                IF(p.es_personalizable = 1, 'Sí', 'No') AS personalizable
            FROM producto p
            LEFT JOIN categoria_producto c ON c.id_categoria = p.id_categoria
            LEFT JOIN preparacion pr ON pr.id_producto = p.id_producto
            LEFT JOIN insumo i ON i.id_insumo = pr.id_insumo
            {where}
            ORDER BY p.precio ASC
            LIMIT {int(limite)}
        """
        return self._ejecutar_query(self._DB_SIS, sql)

    def get_pedidos_pendientes(self, params=None) -> list[dict]:
        """Retorna pedidos con estado PENDIENTE o COCINANDO."""
        estado_cond = ""
        if params and params.estado:
            estado_cond = f"AND estado = '{params.estado}'"
        limite = params.limite if params and params.limite else 50
        sql = f"""
            SELECT id_pedido, tipo_pedido, estado, fecha_pedido
            FROM pedido
            WHERE estado IN ('PENDIENTE', 'COCINANDO') {estado_cond}
            ORDER BY fecha_pedido ASC
            LIMIT {int(limite)}
        """
        return self._ejecutar_query(self._DB_SIS, sql)

    def ping(self) -> bool:
        """Comprueba si la conexión a la BD de sistema está disponible."""
        conn = self._conectar(self._DB_SIS)
        if conn:
            conn.close()
            return True
        return False
