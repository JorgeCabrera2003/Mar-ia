"""
data_cleaner.py — Módulo de Depuración de Datos de Mar-ia
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Limpia los datos crudos de la BD antes de enviarlos al motor
de reportes de PHP. No lanza excepciones: ante cualquier valor
inesperado, sustituye con un valor seguro por defecto.
"""

from datetime import datetime, date, timedelta
import re


# ─── Formateadores individuales ───────────────────────────────────────────────

def _formatear_valor(valor) -> str:
    """
    Convierte un valor de BD a string limpio:
    - None / vacío   → "—"
    - timedelta      → hora en formato 12h (TIME de MySQL)
    - datetime       → "DD/MM/YYYY HH:MM AM/PM"
    - date           → "DD/MM/YYYY"
    - float/decimal  → sin ceros redundantes
    - resto          → str().strip()
    """
    try:
        if valor is None:
            return "—"
        if isinstance(valor, timedelta):
            total_seg = int(valor.total_seconds())
            horas, rem = divmod(total_seg, 3600)
            minutos    = rem // 60
            periodo    = "AM" if horas < 12 else "PM"
            hora_12    = horas % 12 or 12
            return f"{hora_12}:{minutos:02d} {periodo}"
        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y %I:%M %p")
        if isinstance(valor, date):
            return valor.strftime("%d/%m/%Y")
            
        if isinstance(valor, float):
            cadena = f"{valor:.4f}"
        else:
            cadena = str(valor).strip()
            
        if '.' in cadena and re.match(r'^-?\d+\.\d+$', cadena):
            cadena = cadena.rstrip('0').rstrip('.')
            
        return cadena if cadena != "" else "—"
    except Exception:
        return "—"


def _formatear_estado_inventario(stock_actual, stock_minimo) -> str:
    """Clasifica el nivel de alerta del inventario."""
    try:
        actual  = float(stock_actual)
        minimo  = float(stock_minimo)
        if actual == 0:
            return "AGOTADO"
        if actual <= minimo * 0.5:
            return "CRÍTICO"
        if actual <= minimo:
            return "BAJO"
        return "OK"
    except Exception:
        return "—"


# ─── Limpiadores por intención ────────────────────────────────────────────────

def limpiar_inventario(filas: list[dict]) -> list[list]:
    """
    Transforma filas de vw_alertas_inventario en lista de listas para el reporte.
    Columnas: Insumo, Stock Actual, Stock Mínimo, Unidad, Estado
    """
    resultado = []
    for fila in filas:
        try:
            estado = _formatear_estado_inventario(
                fila.get("stock_actual"), fila.get("stock_minimo")
            )
            resultado.append([
                _formatear_valor(fila.get("nombre_insumo") or fila.get("nombre")),
                _formatear_valor(fila.get("stock_actual")),
                _formatear_valor(fila.get("stock_minimo")),
                _formatear_valor(fila.get("unidad_medida") or fila.get("unidad") or fila.get("simbolo")),
                estado,
            ])
        except Exception:
            continue
    return resultado


def limpiar_asistencia(filas: list[dict]) -> list[list]:
    """
    Transforma filas de asistencia diaria en lista de listas para el reporte.
    Columnas: Empleado, Cargo, Marcación, Estado, Hora
    """
    resultado = []
    for fila in filas:
        try:
            # La fecha puede venir como datetime completo; extraemos solo la hora
            fecha_raw = fila.get("fecha")
            if isinstance(fecha_raw, datetime):
                hora_str = fecha_raw.strftime("%I:%M %p")
            else:
                hora_str = _formatear_valor(fecha_raw)

            resultado.append([
                _formatear_valor(fila.get("empleado")),
                _formatear_valor(fila.get("cargo")),
                _formatear_valor(fila.get("tipo_marcacion")),
                _formatear_valor(fila.get("estado")),
                hora_str,
            ])
        except Exception:
            continue
    return resultado


def limpiar_reservas(filas: list[dict]) -> list[list]:
    """
    Transforma filas de reservaciones en lista de listas para el reporte.
    Columnas: Cliente, Mesa, Área, Hora Inicio, Hora Fin, Estado
    """
    resultado = []
    for fila in filas:
        try:
            resultado.append([
                _formatear_valor(fila.get("cliente")),
                _formatear_valor(fila.get("numero_mesa")),
                _formatear_valor(fila.get("area")),
                _formatear_valor(fila.get("hora")),
                _formatear_valor(fila.get("hora_fin")),
                _formatear_valor(fila.get("estado")),
            ])
        except Exception:
            continue
    return resultado


# ─── Dispatcher público ───────────────────────────────────────────────────────

LIMPIADORES = {
    "reporte_inventario_bajo":      limpiar_inventario,
    "reporte_asistencia_diaria":    limpiar_asistencia,
    "reporte_reservas_hoy":         limpiar_reservas,
}


def limpiar_datos(intencion: str, filas: list[dict]) -> list[list]:
    """
    Selecciona el limpiador correcto según la intención y lo aplica.
    Si la intención no tiene limpiador registrado, usa un limpiador genérico.
    """
    limpiador = LIMPIADORES.get(intencion)
    if limpiador:
        return limpiador(filas)

    # Limpiador genérico: convierte cada fila dict en lista de strings
    resultado = []
    for fila in filas:
        try:
            resultado.append([_formatear_valor(v) for v in fila.values()])
        except Exception:
            continue
    return resultado
