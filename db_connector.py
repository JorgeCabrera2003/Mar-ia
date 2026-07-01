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

    def get_alertas_inventario(self) -> list[dict]:
        """
        Retorna insumos cuyo stock actual está por debajo del stock mínimo.
        Fuente: vista vw_alertas_inventario en goobv-sistema.
        """
        sql = "SELECT * FROM vw_alertas_inventario ORDER BY stock_actual ASC"
        return self._ejecutar_query(self._DB_SIS, sql)

    # ─── Intención: reporte_asistencia_diaria ────────────────────────────────

    def get_asistencia_diaria(self) -> list[dict]:
        """
        Retorna los registros de asistencia del día actual.
        Une asistencia con empleado y persona para mostrar nombres.
        """
        sql = """
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
            WHERE DATE(a.fecha) = CURDATE()
            ORDER BY a.fecha DESC
        """
        return self._ejecutar_query(self._DB_SIS, sql)

    # ─── Intención: reporte_reservas_hoy ─────────────────────────────────────

    def get_reservas_hoy(self) -> list[dict]:
        """
        Retorna las reservaciones con fecha igual a hoy.
        Incluye nombre del cliente, mesa y área.
        """
        sql = """
            SELECT
                CONCAT(p.nombre, ' ', p.apellido)   AS cliente,
                r.fecha,
                r.hora,
                r.cantidad_personas,
                r.estado,
                m.numero_mesa,
                a.nombre                            AS area
            FROM reservacion r
            INNER JOIN cliente   cl ON cl.cedula     = r.cedula
            INNER JOIN persona   p  ON p.cedula      = cl.cedula
            LEFT  JOIN asignacion_mesa am ON am.id_reservacion = r.id_reservacion
            LEFT  JOIN mesa      m  ON m.id_mesa     = am.id_mesa
            LEFT  JOIN area_mesa a  ON a.id_area     = m.id_area
            WHERE DATE(r.fecha) = CURDATE()
            ORDER BY r.hora ASC
        """
        return self._ejecutar_query(self._DB_SIS, sql)

    # ─── Extras: directorio y pedidos pendientes (disponibles para el futuro) ─

    def get_directorio_empleados(self) -> list[dict]:
        """Retorna el directorio completo de empleados activos."""
        sql = "SELECT * FROM vw_directorio_empleados"
        return self._ejecutar_query(self._DB_SIS, sql)

    def get_pedidos_pendientes(self) -> list[dict]:
        """Retorna pedidos con estado PENDIENTE o COCINANDO."""
        sql = """
            SELECT id_pedido, tipo_pedido, estado, fecha_pedido
            FROM pedido
            WHERE estado IN ('PENDIENTE', 'COCINANDO')
            ORDER BY fecha_pedido ASC
        """
        return self._ejecutar_query(self._DB_SIS, sql)

    def ping(self) -> bool:
        """Comprueba si la conexión a la BD de sistema está disponible."""
        conn = self._conectar(self._DB_SIS)
        if conn:
            conn.close()
            return True
        return False
