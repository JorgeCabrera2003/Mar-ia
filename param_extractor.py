"""
param_extractor.py — Extractor de Parámetros de Consulta en Lenguaje Natural
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analiza el texto libre del usuario y extrae parámetros estructurados
(fecha, rango, estado, límite, nombre, cédula) para que las consultas
SQL sean dinámicas y específicas.

Fechas:
  "reservas de hoy"           → fecha=hoy
  "reservas de ayer"          → fecha=ayer
  "del 1 de julio"            → fecha=2026-07-01
  "esta semana"               → rango=(lunes, domingo)
  "este mes"                  → rango=(1ro mes, último día)

Personas:
  "busca el cliente Angel"    → nombre="Angel"
  "está registrado Quiñónez"  → nombre="Quiñónez"
  "datos de V-46145027"       → cedula="V-46145027"
  "empleado con correo x@y"   → correo="x@y"
  "teléfono 0414-1234567"     → telefono="0414-1234567"
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

# Palabras que NO son nombres de persona (stop-words de dominio)
_STOP_WORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "en", "con", "que", "es", "son", "hay",
    "está", "esta", "estan", "están", "si", "no", "me",
    "registrado", "registrada", "registrados",
    "busca", "buscar", "busco", "busque",
    "encuentra", "encontrar",
    "cliente", "clientes", "empleado", "empleados",
    "persona", "personas", "trabajador", "trabajadores",
    "nombre", "datos", "información", "info", "perfil",
    "dame", "dime", "muestra", "muestrame", "ver", "lista",
    "como", "cómo", "cuándo", "cuando", "cuanto", "cuánto",
    "tiene", "tienen", "su", "sus", "mi", "mis",
    "existe", "existir", "hay", "haber",
    "quien", "quién", "cual", "cuál",
    "para", "por", "sobre", "desde", "hasta",
    "reporte", "reportes", "informe",
    "hoy", "ayer", "mañana", "semana", "mes", "año",
    "numero", "número", "cedula", "cédula", "telefono", "teléfono",
    "correo", "email", "mail",
}

# Prefijos que indican que lo siguiente es el nombre buscado
_TRIGGER_NOMBRE = [
    r'(?:cliente|empleado|persona|trabajador)\s+(?:llamad[oa]?\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
    r'(?:busca|encuentra|dame\s+(?:los\s+datos|info(?:rmación)?)\s+de)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
    r'(?:se\s+llama|apellido|nombre)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
    r'(?:registrado|registrada)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
    r'(?:el|la)\s+(?:cliente|empleado|persona)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
]


# ─── Dataclass de parámetros extraídos ───────────────────────────────────────

@dataclass
class QueryParams:
    # Temporales
    fecha:        date | None = None
    fecha_inicio: date | None = None
    fecha_fin:    date | None = None
    es_rango:     bool        = False
    descripcion:  str         = ""
    # Filtros
    limite:       int  | None = None
    estado:       str  | None = None
    # Entidades de persona
    nombre:       str  | None = None    # Nombre/apellido libre
    cedula:       str  | None = None    # Ej: V-12345678
    correo:       str  | None = None    # Ej: juan@mail.com
    telefono:     str  | None = None    # Ej: 0414-1234567
    # Filtros de menú (platillos)
    categoria_prod: str | None = None
    ingrediente:    str | None = None
    precio_max:     float | None = None
    con_extras:     bool = False

    def fecha_sql(self) -> str:
        if self.fecha:
            return self.fecha.isoformat()
        return date.today().isoformat()

    def rango_sql(self) -> tuple[str, str]:
        hoy = date.today()
        inicio = self.fecha_inicio or hoy
        fin    = self.fecha_fin    or hoy
        return inicio.isoformat(), fin.isoformat()

    def tiene_entidad_persona(self) -> bool:
        """True si el usuario buscó a alguien específico."""
        return bool(self.nombre or self.cedula or self.correo or self.telefono)

    def descripcion_persona(self) -> str:
        """Descripción legible de la entidad buscada."""
        partes = []
        if self.nombre:   partes.append(f'nombre "{self.nombre}"')
        if self.cedula:   partes.append(f'cédula {self.cedula}')
        if self.correo:   partes.append(f'correo {self.correo}')
        if self.telefono: partes.append(f'teléfono {self.telefono}')
        return ", ".join(partes) if partes else "todos"

    def descripcion_platillos(self) -> str:
        filtros = []
        if self.categoria_prod: filtros.append(f"categoría: {self.categoria_prod.title()}")
        if self.ingrediente:    filtros.append(f"ingrediente: {self.ingrediente}")
        if self.precio_max:     filtros.append(f"precio < {self.precio_max}")
        if self.con_extras:     filtros.append("con extras")
        return "Filtros de menú: " + (", ".join(filtros) if filtros else "Todos los platillos")


# ─── Extractores de entidades de persona ─────────────────────────────────────

def _extraer_cedula(texto: str) -> str | None:
    """
    Extrae número de cédula venezolana o RIF.
    Formatos: V-12345678, v12345678, E-1234567, J-123456789
    """
    match = re.search(r'\b([VEJvej])-?(\d{5,10})\b', texto)
    if match:
        prefijo = match.group(1).upper()
        numero  = match.group(2)
        return f"{prefijo}-{numero}"
    return None


def _extraer_correo(texto: str) -> str | None:
    """Extrae dirección de correo electrónico."""
    match = re.search(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', texto, re.IGNORECASE)
    return match.group(0) if match else None


def _extraer_telefono(texto: str) -> str | None:
    """
    Extrae número de teléfono venezolano.
    Formatos: 0414-1234567, 04141234567, +58 414 1234567
    """
    match = re.search(r'(?:\+?58\s?)?0?4(?:1[246]|2[46])\d[-\s]?\d{3}[-\s]?\d{4}', texto)
    return match.group(0).strip() if match else None


def _extraer_nombre(texto_original: str) -> str | None:
    """
    Extrae nombre o apellido de persona del texto.
    Estrategia:
      1. Busca patrones con trigger keywords (cliente X, empleado X).
      2. Busca palabras capitalizadas que no sean stop-words.
    """
    # Estrategia 1: Trigger keywords explícitos
    for patron in _TRIGGER_NOMBRE:
        match = re.search(patron, texto_original, re.IGNORECASE)
        if match:
            candidato = match.group(1).strip()
            # Validar que no sea sólo stop-words
            palabras = [w for w in candidato.split() if w.lower() not in _STOP_WORDS]
            if palabras:
                return " ".join(palabras)

    # Estrategia 2: Palabras capitalizadas en medio de la oración
    # (probablemente un nombre propio)
    palabras_cap = re.findall(
        r'(?<!\.\s)(?<!\n)\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})\b',
        texto_original
    )
    candidatos = [p for p in palabras_cap if p.lower() not in _STOP_WORDS]

    if candidatos:
        return " ".join(candidatos)  # une si hay nombre + apellido

    return None


# ─── Extractores de menú (platillos) ─────────────────────────────────────────

def _extraer_precio_max(texto: str) -> float | None:
    match = re.search(r'(?:menor|menos|menores|bajo|hasta|m[aá]ximo)\s+(?:a|de|que)?\s*\$?(\d+(?:\.\d{1,2})?)', texto, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None

def _extraer_categoria_prod(texto: str) -> str | None:
    categorias = [
        "postre", "barra", "cocina", "retail", "bebida", 
        "perros calientes", "hamburguesa", "taco", "pepito", 
        "entrada", "mexicanisimo", "pizzas"
    ]
    for cat in categorias:
        if cat in texto.lower():
            if cat == "bebida": return "BARRA"
            return cat.upper()
    return None

def _extraer_ingrediente(texto: str) -> str | None:
    # Ej: "con pollo", "lleva queso", "tiene carne", "de chocolate"
    match = re.search(r'(?:con|lleva|tiene|de)\s+([a-záéíóúñ]+)', texto, re.IGNORECASE)
    if match:
        ingrediente = match.group(1).strip()
        omitir = _STOP_WORDS.union({"extras", "precio", "dolares", "categoria", "platillo", "plato"})
        if ingrediente.lower() not in omitir:
            return ingrediente
    return None

def _extraer_con_extras(texto: str) -> bool:
    return bool(re.search(r'(?:con|permit|teng|agreg)\w*\s+extras?|personalizab', texto, re.IGNORECASE))


# ─── Extractores temporales ───────────────────────────────────────────────────

def _extraer_fecha_especifica(texto: str) -> date | None:
    hoy = date.today()
    patron_mes = r'(?:del?\s+|el\s+)?(\d{1,2})\s+de\s+([a-záéíóú]+)'
    match = re.search(patron_mes, texto)
    if match:
        dia     = int(match.group(1))
        mes_str = match.group(2).lower()
        mes     = MESES.get(mes_str)
        if mes and 1 <= dia <= 31:
            try:
                return date(hoy.year, mes, dia)
            except ValueError:
                pass
    patron_num = r'(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{4}))?'
    match_num = re.search(patron_num, texto)
    if match_num:
        try:
            dia = int(match_num.group(1))
            mes = int(match_num.group(2))
            año = int(match_num.group(3)) if match_num.group(3) else hoy.year
            return date(año, mes, dia)
        except ValueError:
            pass
    return None


def _rango_semana(hoy: date) -> tuple[date, date]:
    lunes   = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)
    return lunes, domingo


def _rango_mes(hoy: date, mes: int | None = None) -> tuple[date, date]:
    import calendar
    m          = mes or hoy.month
    ultimo_dia = calendar.monthrange(hoy.year, m)[1]
    return date(hoy.year, m, 1), date(hoy.year, m, ultimo_dia)


# ─── Función principal ────────────────────────────────────────────────────────

def extraer_params(texto: str) -> QueryParams:
    """
    Analiza el texto y retorna un QueryParams completo con:
      - Entidades de persona: nombre, cédula, correo, teléfono
      - Filtros: límite, estado
      - Temporal: fecha específica, rango, relativo

    Args:
        texto: Mensaje libre del usuario en español.

    Returns:
        QueryParams completamente poblado.
    """
    t   = texto.lower().strip()
    hoy = date.today()
    p   = QueryParams()

    # ── Entidades de persona ───────────────────────────────────────────────────
    p.cedula   = _extraer_cedula(texto)
    p.correo   = _extraer_correo(texto)
    p.telefono = _extraer_telefono(texto)

    # Extraer nombre solo si no hay cédula/correo/tel (evita falsos positivos)
    if not (p.cedula or p.correo or p.telefono):
        p.nombre = _extraer_nombre(texto)

    # ── Entidades de Menú (Platillos) ─────────────────────────────────────────
    p.categoria_prod = _extraer_categoria_prod(texto)
    p.precio_max = _extraer_precio_max(texto)
    p.ingrediente = _extraer_ingrediente(texto)
    p.con_extras = _extraer_con_extras(texto)

    # ── Límite numérico ────────────────────────────────────────────────────────
    limite_match = re.search(
        r'(?:top|los\s+(?:últimos?|primeros?)|las\s+(?:últimas?|primeras?)|últimos?|primeros?)\s+(\d+)',
        t
    )
    if limite_match:
        p.limite = int(limite_match.group(1))

    # ── Estado ────────────────────────────────────────────────────────────────
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
        inicio, fin = _rango_semana(hoy)
        p.fecha_inicio, p.fecha_fin, p.es_rango = inicio, fin, True
        p.descripcion = f"Semana del {inicio.strftime('%d/%m')} al {fin.strftime('%d/%m/%Y')}"
        return p

    if re.search(r'\bsemana\s+pasada\b|\bla\s+semana\s+anterior\b', t):
        inicio, fin = _rango_semana(hoy - timedelta(weeks=1))
        p.fecha_inicio, p.fecha_fin, p.es_rango = inicio, fin, True
        p.descripcion = f"Semana pasada ({inicio.strftime('%d/%m')} al {fin.strftime('%d/%m/%Y')})"
        return p

    if re.search(r'\beste\s+mes\b|\bdel\s+mes\b|\bel\s+mes\b', t):
        inicio, fin = _rango_mes(hoy)
        p.fecha_inicio, p.fecha_fin, p.es_rango = inicio, fin, True
        p.descripcion = inicio.strftime("Mes de %B %Y")
        return p

    if re.search(r'\bmes\s+pasado\b|\bel\s+mes\s+anterior\b', t):
        mes_ant = hoy.month - 1 if hoy.month > 1 else 12
        inicio, fin = _rango_mes(hoy, mes_ant)
        p.fecha_inicio, p.fecha_fin, p.es_rango = inicio, fin, True
        p.descripcion = inicio.strftime("Mes pasado (%B %Y)")
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

    hace_match = re.search(r'hace\s+(\d+)\s+días?', t)
    if hace_match:
        n = int(hace_match.group(1))
        p.fecha       = hoy - timedelta(days=n)
        p.descripcion = f"Hace {n} días " + p.fecha.strftime("(%d/%m/%Y)")
        return p

    # ── Fecha específica ──────────────────────────────────────────────────────
    fecha_esp = _extraer_fecha_especifica(t)
    if fecha_esp:
        p.fecha       = fecha_esp
        p.descripcion = fecha_esp.strftime("%d/%m/%Y")
        return p

    # ── Default: hoy ──────────────────────────────────────────────────────────
    p.fecha       = hoy
    p.descripcion = "Hoy " + hoy.strftime("(%d/%m/%Y)")
    return p
