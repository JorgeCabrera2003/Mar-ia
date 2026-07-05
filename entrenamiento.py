"""
entrenamiento.py — Script de Entrenamiento del Modelo Mar-ia
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uso:
    python entrenamiento.py

Entrena el pipeline TF-IDF + SVM con los datos de training_data.py,
evalúa con validación cruzada (5-fold) e imprime las métricas.
Guarda el modelo en models/mar_ia_model.pkl listo para carga rápida.
"""

import sys
import os
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report
import numpy as np

# Agrega el directorio actual al path para imports relativos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from training_data import obtener_X_y, listar_intenciones
from ml_engine import MarIaEngine


# ─── Banner ───────────────────────────────────────────────────────────────────

BANNER = """
------------------------------------------------------
          Mar-ia -- Entrenamiento del Modelo           
          SICGOV . TF-IDF + SVM (kernel lineal)       
------------------------------------------------------
"""

print(BANNER)


# ─── Cargar datos ─────────────────────────────────────────────────────────────

X, y = obtener_X_y()
intenciones = listar_intenciones()

print(f"  Total de muestras  : {len(X)}")
print(f"  Intenciones        : {len(intenciones)}")
for intent in intenciones:
    count = y.count(intent)
    print(f"     - {intent:<35} ({count} frases)")
print()


# ─── Validación cruzada ───────────────────────────────────────────────────────

print("  Ejecutando validación cruzada (5-fold)...")

engine = MarIaEngine.__new__(MarIaEngine)
engine._model_path = "models/mar_ia_model.pkl"
engine._pipeline   = None
engine._listo      = False
pipeline_tmp       = MarIaEngine._construir_pipeline()

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(pipeline_tmp, X, y, cv=cv, scoring="accuracy")

print(f"\n  Precisión por fold : {[f'{s:.2%}' for s in scores]}")
print(f"  Precisión media    : {scores.mean():.2%} ± {scores.std():.2%}")

if scores.mean() < 0.85:
    print("\n  Precisión menor a 85%. Considera agregar más frases de entrenamiento.")
else:
    print("\n  Precisión aceptable. Procediendo al entrenamiento final.")


# ─── Entrenamiento final sobre todos los datos ────────────────────────────────

print("\n  Entrenando modelo final con todos los datos...")

engine.entrenar(X, y)

# ─── Reporte por clase ────────────────────────────────────────────────────────

y_pred = engine._pipeline.predict(X)
print("\n  Reporte de clasificación (sobre datos de entrenamiento):\n")
print(classification_report(y, y_pred, target_names=intenciones))


# ─── Prueba rápida de inferencia ──────────────────────────────────────────────

PRUEBAS = [
    "dame el inventario bajo",
    "quiénes faltaron hoy",
    "ver las reservaciones de hoy",
    "cuántas mesas hay reservadas",
    "stock crítico de insumos",
    "asistencia del personal",
]

print("  Prueba de inferencia:")
for frase in PRUEBAS:
    intencion, confianza = engine.predecir(frase)
    estado = "OK" if intencion else "NO"
    print(f"     {estado} '{frase}'")
    print(f"        -> Intención : {intencion or 'No clasificada'}")
    print(f"        -> Confianza : {confianza:.2%}")
print()


# ─── Guardar modelo ───────────────────────────────────────────────────────────

engine.guardar_modelo()
print("\n  Modelo guardado exitosamente.")
print("     Ahora puedes iniciar el servidor con:")
print("     uvicorn main:app --host 0.0.0.0 --port 8090 --reload\n")
