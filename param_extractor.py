"""
param_extractor.py — Extractor de Parámetros de Consulta en Lenguaje Natural
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analiza el texto libre del usuario y extrae parámetros estructurados
(fecha, rango, estado, límite) para que las consultas SQL sean dinámicas.

Ejemplos reconocidos:
  "reservas de hoy"           → fecha=hoy
  "reservas de ayer"          → fecha=ayer
  "del 1 de julio"            → fecha=2026-07-01
  "esta semana"               → rango=(lunes, domingo)
  "este mes"                  → rango=(1ro mes, último día)
  "las últimas 5"             → limite=5
  "solo las confirmadas"      → estado='CONFIRMADA'
"""

import re
from datetime import date, timedelta
from dataclasses import dataclass, field


# ─── Diccionarios de lenguaje natural ────────────────────────────────────────

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
    "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
}

ESTADOS_RESERVA = {
    "pendiente":   "PENDIENTE",
    "confirmada":  "CONFIRMADA",
    "cancelada":   "CANCELADA",
    "completada":  "COMPLETADA",
}

ESTADOS_ASISTENCIA = {
    "presente":    "PRESENTE",
    "ausente":     "AUSENTE",
    "tardanza":    "TARDANZA",
    "permiso":     "PERMISO",
}


# ─── Dataclass de parámetros extraídos ───────────────────────────────────────

@dataclass
class QueryParams:
    fecha:        date | None = None          # Fecha específica
    fecha_inicio: date | None = None          # Inicio de rango
    fecha_fin:    date | None = None          # Fin de rango
    es_rango:     bool        = False         # True si es consulta por rango
    limite:       int | None  = None          # TOP N resultados
    estado:       str | None  = None          # Filtro de estado
    descripcion:  str         = ""            # Descripción legible del periodo

    def fecha_sql(self) -> str:
        """Devuelve la fecha para usar en SQL (como string ISO)."""
        if self.fecha:
            return self.fecha.isoformat()
        return date.today().isoformat()

    def rango_sql(self) -> tuple[str, str]:
        """Devuelve (inicio, fin) para usar en BETWEEN."""
        hoy = date.today()
        inicio = self.fecha_inicio or hoy
        fin    = self.fecha_fin    or hoy
        return inicio.isoformat(), fin.isoformat()


# ─── Funciones de extracción ──────────────────────────────────────────────────

def _extraer_fecha_especifica(texto: str) -> date | None:
    """
    Intenta extraer una fecha concreta del texto.
    Patrones: "el 5 de julio", "del 1 de enero", "15/06", "15-06-2026"
    """
    hoy = date.today()

    # Patrón: "N de [mes]" o "del N de [mes]" o "el N de [mes]"
    patron_mes = r'(?:del?\s+|el\s+)?(\d{1,2})\s+de\s+([a-záéíóú]+)'
    match = re.search(patron_mes, texto)
    if match:
        dia     = int(match.group(1))
        mes_str = match.group(2).lower()
        mes     = MESES.get(mes_str)
        if mes and 1 <= dia <= 31:
            año = hoy.year
            # Si la fecha ya pasó este año y sería en el futuro → mantener año
            try:
                return date(año, mes, dia)
            except ValueError:
                pass

    # Patrón: DD/MM o DD-MM o DD/MM/YYYY
    patron_num = r'(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{4}))?'
    match_num = re.search(patron_num, texto)
    if match_num:
        dia = int(match_num.group(1))
        mes = int(match_num.group(2))
        año = int(match_num.group(3)) if match_num.group(3) else hoy.year
        try:
            return date(año, mes, dia)
        except ValueError:
            pass

    return None


def _extraer_rango_semana(hoy: date) -> tuple[date, date]:
    """Retorna (lunes, domingo) de la semana actual."""
    lunes  = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)
    return lunes, domingo


def _extraer_rango_mes(hoy: date, mes: int | None = None) -> tuple[date, date]:
    """Retorna (primer día, último día) del mes dado o del actual."""
    import calendar
    m   = mes or hoy.month
    año = hoy.year
    ultimo_dia = calendar.monthrange(año, m)[1]
    return date(año, m, 1), date(año, m, ultimo_dia)


def extraer_params(texto: str) -> QueryParams:
    """
    Función principal. Analiza el texto y retorna un QueryParams completo.

    Args:
        texto: Mensaje libre del usuario en español.

    Returns:
        QueryParams con todos los parámetros detectados.
    """
    t   = texto.lower().strip()
    hoy = date.today()
    p   = QueryParams()

    # ── Límite numérico ("las 5 primeras", "top 10") ──────────────────────────
    limite_match = re.search(
        r'(?:top|los\s+(?:últimos?|primeros?)|las\s+(?:últimas?|primeras?)|últimos?|primeros?)\s+(\d+)',
        t
    )
    if limite_match:
        p.limite = int(limite_match.group(1))

    # ── Estado de reserva / asistencia ────────────────────────────────────────
    for kw, val in ESTADOS_RESERVA.items():
        if kw in t:
            p.estado = val
            break
    if not p.estado:
        for kw, val in ESTADOS_ASISTENCIA.items():
            if kw in t:
                p.estado = val
                break

    # ── Rangos temporales ─────────────────────────────────────────────────────

    if re.search(r'\besta\s+semana\b|\bla\s+semana\b', t):
        inicio, fin = _extraer_rango_semana(hoy)
        p.fecha_inicio = inicio
        p.fecha_fin    = fin
        p.es_rango     = True
        p.descripcion  = f"Semana del {inicio.strftime('%d/%m')} al {fin.strftime('%d/%m/%Y')}"
        return p

    if re.search(r'\bsemana\s+pasada\b|\bla\s+semana\s+anterior\b', t):
        inicio, fin = _extraer_rango_semana(hoy - timedelta(weeks=1))
        p.fecha_inicio = inicio
        p.fecha_fin    = fin
        p.es_rango     = True
        p.descripcion  = f"Semana pasada ({inicio.strftime('%d/%m')} al {fin.strftime('%d/%m/%Y')})"
        return p

    if re.search(r'\beste\s+mes\b|\bdel\s+mes\b|\bel\s+mes\b', t):
        inicio, fin = _extraer_rango_mes(hoy)
        p.fecha_inicio = inicio
        p.fecha_fin    = fin
        p.es_rango     = True
        p.descripcion  = inicio.strftime("Mes de %B %Y")
        return p

    if re.search(r'\bmes\s+pasado\b|\bel\s+mes\s+anterior\b', t):
        mes_ant = hoy.month - 1 if hoy.month > 1 else 12
        inicio, fin = _extraer_rango_mes(hoy, mes_ant)
        p.fecha_inicio = inicio
        p.fecha_fin    = fin
        p.es_rango     = True
        p.descripcion  = inicio.strftime("Mes pasado (%B %Y)")
        return p

    # ── Fechas relativas ──────────────────────────────────────────────────────

    if re.search(r'\bayer\b', t):
        p.fecha       = hoy - timedelta(days=1)
        p.descripcion = "Ayer " + p.fecha.strftime("(%d/%m/%Y)")
        return p

    if re.search(r'\bmañana\b', t):
        p.fecha       = hoy + timedelta(days=1)
        p.descripcion = "Mañana " + p.fecha.strftime("(%d/%m/%Y)")
        return p

    if re.search(r'\bhace\s+(\d+)\s+días?\b', t):
        n_match = re.search(r'hace\s+(\d+)\s+días?', t)
        n = int(n_match.group(1))
        p.fecha       = hoy - timedelta(days=n)
        p.descripcion = f"Hace {n} días " + p.fecha.strftime("(%d/%m/%Y)")
        return p

    # ── Fecha específica (N de mes) ───────────────────────────────────────────
    fecha_especifica = _extraer_fecha_especifica(t)
    if fecha_especifica:
        p.fecha       = fecha_especifica
        p.descripcion = fecha_especifica.strftime("%d/%m/%Y")
        return p

    # ── Default: hoy ──────────────────────────────────────────────────────────
    p.fecha       = hoy
    p.descripcion = "Hoy " + hoy.strftime("(%d/%m/%Y)")
    return p
