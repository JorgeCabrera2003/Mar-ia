"""
training_data.py — Dataset de Entrenamiento de Mar-ia
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Contiene las frases etiquetadas por intención.
Para agregar una nueva intención:
  1. Crea una nueva clave en TRAINING_DATA con ≥10 frases.
  2. Ejecuta: python entrenamiento.py
El modelo se regenera automáticamente.
"""

# ─── Dataset de frases por intención ─────────────────────────────────────────
# Clave  = nombre exacto de la intención
# Valor  = lista de frases de ejemplo del usuario (en español)

TRAINING_DATA: dict[str, list[str]] = {

    "reporte_inventario_bajo": [
        "dame el inventario bajo",
        "qué insumos están por agotarse",
        "mostrar alertas de inventario",
        "ver stock mínimo",
        "qué productos tienen poco stock",
        "insumos con stock crítico",
        "reporte de inventario bajo",
        "alertas de inventario",
        "qué se está acabando",
        "insumos agotados o por agotarse",
        "dame el stock bajo",
        "cuáles insumos están en rojo",
        "necesito saber qué falta en el almacén",
        "ver materiales con bajo nivel",
        "inventario crítico por favor",
        "los 5 insumos más críticos",
        "top 10 del inventario bajo",
        "cuáles insumos están agotados",
    ],

    "reporte_asistencia_diaria": [
        "asistencia de hoy",
        "quiénes faltaron hoy",
        "dame la asistencia del día",
        "reporte de asistencia diaria",
        "ver marcaciones de hoy",
        "quiénes llegaron tarde",
        "lista de empleados presentes",
        "control de asistencia",
        "quién marcó entrada hoy",
        "registros de entrada y salida de hoy",
        "quiénes están presentes hoy",
        "asistencia de los empleados",
        "faltas de hoy",
        "reporte de puntualidad de hoy",
        "ver el control de empleados de hoy",
        "asistencia de ayer",
        "quiénes faltaron ayer",
        "asistencia de esta semana",
        "faltas de la semana",
        "quiénes faltaron el 1 de julio",
        "asistencia del 30 de junio",
        "reporte de asistencia del mes",
    ],

    "reporte_reservas_hoy": [
        "reservas de hoy",
        "cuántas mesas reservadas hay",
        "ver las reservaciones del día",
        "dame las reservas de hoy",
        "reporte de reservaciones",
        "qué mesas están reservadas",
        "reservaciones para hoy",
        "clientes con reserva hoy",
        "lista de reservas del día",
        "cuántas reservaciones tenemos hoy",
        "ver agenda de reservas de hoy",
        "reservaciones activas hoy",
        "quiénes tienen mesa reservada hoy",
        "reporte de mesas reservadas",
        "dame el calendario de reservas de hoy",
        "las reservaciones del 1 de julio",
        "reservas de ayer",
        "reservas de esta semana",
        "reservas del 30 de junio",
        "reservaciones de mañana",
        "ver reservas de los últimos 7 días",
        "reservas confirmadas de hoy",
        "solo las reservas pendientes",
        "reservas del mes",
    ],

    "reporte_clientes": [
        "cuántos clientes hay registrados",
        "dame la lista de clientes",
        "ver todos los clientes",
        "mostrar clientes registrados",
        "reporte de clientes",
        "quiénes son nuestros clientes",
        "base de datos de clientes",
        "cuántos clientes tenemos",
        "lista de clientes del sistema",
        "clientes registrados en el sistema",
        "ver directorio de clientes",
        "información de los clientes",
        "dame los datos de los clientes",
        "total de clientes registrados",
        "reporte de cartera de clientes",
    ],

    "reporte_empleados": [
        "ver todos los empleados",
        "lista del personal",
        "directorio de empleados",
        "dame el listado de empleados",
        "quiénes trabajan aquí",
        "reporte de personal activo",
        "cuántos empleados hay",
        "mostrar el personal",
        "empleados registrados",
        "ver la nómina",
        "quiénes son los trabajadores",
        "directorio del personal",
        "lista de trabajadores activos",
        "datos de los empleados",
        "información del personal",
    ],

    "reporte_pedidos_pendientes": [
        "pedidos pendientes",
        "qué pedidos faltan por atender",
        "ver órdenes pendientes",
        "pedidos en cola",
        "cuántos pedidos hay pendientes",
        "órdenes sin procesar",
        "reporte de pedidos activos",
        "pedidos que se están cocinando",
        "qué hay en cocina",
        "ver comandas pendientes",
        "pedidos sin entregar",
        "estado de los pedidos",
        "cuántas órdenes están en proceso",
        "reporte de cocina",
        "ver pedidos en preparación",
    ],
}


def obtener_X_y() -> tuple[list[str], list[str]]:
    """
    Convierte TRAINING_DATA en X (textos) e y (etiquetas)
    para Scikit-Learn.
    """
    X, y = [], []
    for intencion, frases in TRAINING_DATA.items():
        for frase in frases:
            X.append(frase.lower().strip())
            y.append(intencion)
    return X, y


def listar_intenciones() -> list[str]:
    """Retorna la lista de intenciones registradas."""
    return list(TRAINING_DATA.keys())
