"""
main.py — Servidor FastAPI del Microservicio Mar-ia
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoints:
  GET  /health       → Estado del servicio y del modelo
  POST /classify     → Clasificación + datos + JSON contrato
  GET  /intenciones  → Intenciones disponibles en el modelo
  POST /retrain      → Reentrena el modelo (requiere token)

Principio de Ortogonalidad:
  Todos los handlers usan try/except y nunca propagan errores
  sin respuesta JSON. Si Mar-ia falla, devuelve el contrato
  de error y SICGOV continúa operando.
"""

import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from ml_engine      import MarIaEngine
from db_connector   import SICGOVConnector
from report_builder import construir_reporte, construir_reporte_error
from training_data  import obtener_X_y, listar_intenciones

load_dotenv()

# ─── Constantes de configuración ─────────────────────────────────────────────

API_TOKEN   = os.getenv("MARIA_API_TOKEN", "mar-ia-token-sicgov-2026")
MODEL_PATH  = os.getenv("MODEL_PATH", "models/mar_ia_model.pkl")
PORT        = int(os.getenv("MARIA_PORT", 8090))

# ─── Estado compartido de la aplicación ──────────────────────────────────────

engine    = MarIaEngine(model_path=MODEL_PATH)
connector = SICGOVConnector()


# ─── Ciclo de vida (lifespan) ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y limpieza al arrancar/detener el servidor."""
    print("\n╔══════════════════════════════════════════╗")
    print("║   Mar-ia — Microservicio IA · SICGOV    ║")
    print(f"║   Puerto : {PORT:<5}  Modelo : {'✅' if engine.esta_listo else '❌ Sin entrenar'}          ║")
    print("╚══════════════════════════════════════════╝\n")
    yield
    print("\n[Mar-ia] Servicio detenido.")


# ─── Aplicación FastAPI ───────────────────────────────────────────────────────

app = FastAPI(
    title       = "Mar-ia — Agente IA de SICGOV",
    description = "Clasificación de intenciones y orquestación de reportes PDF.",
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# ─── Archivos estáticos (Chat UI) ────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    """Redirige la raíz al chat UI."""
    return RedirectResponse(url="/static/index.html")


# ─── CORS — Acepta cualquier origen localhost (XAMPP, Laragon, PHP built-in) ──

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex  = r"http://localhost(:\d+)?",   # localhost:80, 8080, 8081, etc.
    allow_methods       = ["GET", "POST", "OPTIONS"],
    allow_headers       = ["*"],
    allow_credentials   = False,
)


# ─── Schemas de Request/Response ─────────────────────────────────────────────

class ClasificarRequest(BaseModel):
    cedula:  str = Field(..., example="V-12345678", description="Cédula del usuario de SICGOV")
    mensaje: str = Field(..., min_length=2, example="dame el inventario bajo")


class ReentrenarRequest(BaseModel):
    token: str = Field(..., description="Token de autorización (MARIA_API_TOKEN en .env)")


# ─── Dispatcher: intención → consulta SQL ────────────────────────────────────

INTENT_DISPATCHER: dict = {
    "reporte_inventario_bajo":   connector.get_alertas_inventario,
    "reporte_asistencia_diaria": connector.get_asistencia_diaria,
    "reporte_reservas_hoy":      connector.get_reservas_hoy,
}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    summary = "Estado del servicio",
    tags    = ["Sistema"],
)
def health_check():
    """
    Verifica que Mar-ia está operativa.
    Retorna el estado del modelo y la conectividad a la BD.
    """
    bd_conectada = connector.ping()
    return {
        "servicio":      "Mar-ia",
        "estado":        "operativo",
        "modelo_listo":  engine.esta_listo,
        "bd_conectada":  bd_conectada,
        "intenciones":   engine.obtener_clases() if engine.esta_listo else [],
        "version":       "1.0.0",
    }


@app.post(
    "/classify",
    summary = "Clasificar intención y obtener reporte",
    tags    = ["IA"],
)
def clasificar(body: ClasificarRequest):
    """
    Endpoint principal. Recibe el mensaje del usuario, clasifica la intención,
    consulta la BD y retorna el JSON contrato para ReportService.php.
    """
    try:
        # 1. Clasificar intención
        if not engine.esta_listo:
            return JSONResponse(
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
                content     = construir_reporte_error(
                    "El modelo de Mar-ia no está entrenado. "
                    "Ejecuta 'python entrenamiento.py' y reinicia el servidor."
                ),
            )

        intencion, confianza = engine.predecir(body.mensaje)

        # 2. Consultar BD según intención
        datos_crudos: list[dict] = []
        if intencion and intencion in INTENT_DISPATCHER:
            datos_crudos = INTENT_DISPATCHER[intencion]()

        # 3. Construir y retornar el contrato JSON
        reporte = construir_reporte(
            intencion    = intencion,
            confianza    = confianza,
            datos_crudos = datos_crudos,
            cedula       = body.cedula,
        )
        return JSONResponse(content=reporte, status_code=status.HTTP_200_OK)

    except Exception as e:
        print(f"[Mar-ia][main] Error inesperado en /classify: {e}")
        return JSONResponse(
            status_code = status.HTTP_200_OK,  # Ortogonal: siempre 200 hacia PHP
            content     = construir_reporte_error(f"Error interno de Mar-ia: {str(e)}"),
        )


@app.get(
    "/intenciones",
    summary = "Listar intenciones disponibles",
    tags    = ["IA"],
)
def listar():
    """Retorna las intenciones que el modelo actual puede reconocer."""
    return {
        "intenciones_modelo":       engine.obtener_clases(),
        "intenciones_entrenamiento": listar_intenciones(),
    }


@app.post(
    "/retrain",
    summary = "Reentrenar el modelo",
    tags    = ["Administración"],
)
def reentrenar(body: ReentrenarRequest):
    """
    Reentrena el modelo SVM con los datos actuales de training_data.py
    y guarda el nuevo .pkl. Requiere el token configurado en .env.
    """
    if body.token != API_TOKEN:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Token inválido.",
        )

    try:
        X, y = obtener_X_y()
        engine.entrenar(X, y)
        engine.guardar_modelo()
        return {
            "estado":      "ok",
            "mensaje":     "Modelo reentrenado y guardado exitosamente.",
            "intenciones": engine.obtener_clases(),
            "muestras":    len(X),
        }
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = f"Error durante el reentrenamiento: {str(e)}",
        )


# ─── Punto de entrada directo ─────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host    = os.getenv("MARIA_HOST", "0.0.0.0"),
        port    = PORT,
        reload  = True,
        log_level = "info",
    )
