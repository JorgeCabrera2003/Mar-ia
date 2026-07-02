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

    def _ejecutar_query(self, database: str, sql: str, params: tuple = ()) -> list[dict]:
        """
        Ejecuta una consulta SELECT y retorna lista de dicts.
        Siempre cierra la conexión. Ante cualquier error retorna [].
        """
        conn = self._conectar(database)
        if conn is None:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
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
        """Retorna el directorio completo de empleados activos."""
        limite = params.limite if params and params.limite else 200
        sql    = f"SELECT * FROM vw_directorio_empleados LIMIT {int(limite)}"
        return self._ejecutar_query(self._DB_SIS, sql)

    def get_clientes(self, params=None) -> list[dict]:
        """Retorna la lista de clientes registrados en el sistema."""
        limite = params.limite if params and params.limite else 200
        sql = f"""
            SELECT
                p.cedula,
                CONCAT(p.nombre, ' ', p.apellido) AS nombre_completo,
                p.telefono,
                p.correo,
                c.fecha_registro
            FROM cliente c
            INNER JOIN persona p ON p.cedula = c.cedula
            ORDER BY p.apellido ASC
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
