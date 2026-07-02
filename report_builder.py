"""
report_builder.py — Constructor del JSON Contrato para ReportService.php
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Transforma la intención + datos limpios en la estructura JSON exacta
que espera el motor de reportes de PHP (ReportService).
"""

from datetime import datetime
from data_cleaner import limpiar_datos


# ─── Configuración de columnas por intención ──────────────────────────────────

REPORTE_CONFIG: dict[str, dict] = {
    "reporte_inventario_bajo": {
        "titulo":   "Reporte de Inventario Bajo",
        "columnas": ["Insumo", "Stock Actual", "Stock Mínimo", "Unidad", "Estado"],
    },
    "reporte_asistencia_diaria": {
        "titulo":   "Reporte de Asistencia Diaria",
        "columnas": ["Empleado", "Cargo", "Marcación", "Estado", "Hora"],
    },
    "reporte_reservas_hoy": {
        "titulo":   "Reporte de Reservaciones del Día",
        "columnas": ["Cliente", "Mesa", "Área", "Hora Inicio", "Hora Fin", "Estado"],
    },
    "reporte_clientes": {
        "titulo":   "Reporte de Clientes Registrados",
        "columnas": ["Cédula", "Nombre Completo", "Teléfono", "Correo", "Fecha Registro"],
    },
    "reporte_empleados": {
        "titulo":   "Directorio de Empleados Activos",
        "columnas": [],
    },
    "reporte_pedidos_pendientes": {
        "titulo":   "Reporte de Pedidos Pendientes",
        "columnas": ["ID Pedido", "Tipo", "Estado", "Fecha"],
    },
    "buscar_persona": {
        "titulo":   "Resultado de Búsqueda de Persona",
        "columnas": ["Cédula", "Nombre Completo", "Teléfono", "Correo", "Rol"],
    },
    "reporte_platillos": {
        "titulo":   "Reporte de Menú (Platillos)",
        "columnas": ["Producto", "Categoría", "Precio", "Personalizable"],
    },
}


# ─── Función principal ────────────────────────────────────────────────────────

def construir_reporte(
    intencion:  str | None,
    confianza:  float,
    datos_crudos: list[dict],
    cedula:     str = "Sistema",
    periodo:    str = "",
) -> dict:
    """
    Construye el contrato JSON completo para ReportService.php.

    Args:
        intencion    : Intención clasificada por el motor ML (o None).
        confianza    : Nivel de confianza de la clasificación (0.0 - 1.0).
        datos_crudos : Filas de la BD sin procesar.
        cedula       : Cédula del usuario que realiza la consulta.

    Returns:
        dict con las claves: intencion, confianza, metadata,
        documento_config, error.
    """
    ahora = datetime.now()

    # ── Caso: intención no reconocida ─────────────────────────────────────────
    if intencion is None:
        return {
            "intencion":       None,
            "confianza":       round(confianza, 4),
            "metadata":        {},
            "documento_config": {"columnas": [], "filas": []},
            "error": (
                "No entendí tu consulta. Prueba con: "
                "'inventario bajo', 'asistencia de hoy', 'reservas de hoy', "
                "'lista de clientes', 'empleados' o 'pedidos pendientes'."
            ),
        }

    # ── Recuperar config de columnas y título ─────────────────────────────────
    config = REPORTE_CONFIG.get(intencion, {
        "titulo":   intencion.replace("_", " ").title(),
        "columnas": [],
    })

    # ── Limpiar filas ─────────────────────────────────────────────────────────
    filas_limpias = limpiar_datos(intencion, datos_crudos)

    # ── Construir respuesta ───────────────────────────────────────────────────
    return {
        "intencion": intencion,
        "confianza": round(confianza, 4),
        "metadata": {
            "titulo":        config["titulo"],
            "generado_por":  "Mar-ia",
            "fecha":         ahora.strftime("%d/%m/%Y"),
            "hora":          ahora.strftime("%I:%M %p"),
            "usuario":       cedula,
            "periodo":       periodo or ahora.strftime("%d/%m/%Y"),
            "total_filas":   len(filas_limpias),
        },
        "documento_config": {
            "columnas": config["columnas"],
            "filas":    filas_limpias,
        },
        "error": None,
    }


def construir_reporte_error(mensaje: str) -> dict:
    """Retorna un contrato de error estructurado ante fallos inesperados."""
    return {
        "intencion":       None,
        "confianza":       0.0,
        "metadata":        {},
        "documento_config": {"columnas": [], "filas": []},
        "error":           mensaje,
    }
