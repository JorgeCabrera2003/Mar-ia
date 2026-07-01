"""
ml_engine.py — Motor de Clasificación SVM de Mar-ia
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Implementa el pipeline: TfidfVectorizer → SVM (kernel lineal).
La clase MarIaEngine sigue el Principio de Ortogonalidad:
  - Si el modelo .pkl no existe al cargar → predecir retorna None.
  - Nunca lanza excepciones hacia la capa FastAPI.
"""

import os
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
import numpy as np


class MarIaEngine:
    """Motor de clasificación de intenciones basado en TF-IDF + SVM lineal."""

    # Umbral mínimo de confianza para aceptar una clasificación
    CONFIANZA_MINIMA = 0.60

    def __init__(self, model_path: str = "models/mar_ia_model.pkl"):
        self._model_path = model_path
        self._pipeline: Pipeline | None = None
        self._listo = False
        self.cargar_modelo()

    # ─── Construcción del pipeline ────────────────────────────────────────────

    @staticmethod
    def _construir_pipeline() -> Pipeline:
        """
        Pipeline: TfidfVectorizer → CalibratedClassifierCV(LinearSVC)
        CalibratedClassifierCV nos da probabilidades reales (predict_proba),
        que LinearSVC no provee por defecto.
        """
        return Pipeline([
            ("tfidf", TfidfVectorizer(
                analyzer="char_wb",     # n-gramas de caracteres (robusto a typos)
                ngram_range=(2, 4),     # bigramas a cuatrigramas
                sublinear_tf=True,      # tf logarítmico → reduce dominancia de palabras frecuentes
                min_df=1,
            )),
            ("clf", CalibratedClassifierCV(
                LinearSVC(
                    C=1.0,
                    max_iter=2000,
                    class_weight="balanced",
                ),
                cv=3,
                method="sigmoid",
            )),
        ])

    # ─── Entrenamiento ────────────────────────────────────────────────────────

    def entrenar(self, X: list[str], y: list[str]) -> None:
        """
        Entrena el pipeline con los textos X y etiquetas y.
        Sobreescribe el modelo actual en memoria.
        """
        self._pipeline = self._construir_pipeline()
        self._pipeline.fit(X, y)
        self._listo = True

    # ─── Persistencia ─────────────────────────────────────────────────────────

    def guardar_modelo(self) -> None:
        """Serializa el pipeline a disco con joblib."""
        if not self._listo:
            raise RuntimeError("No hay modelo entrenado para guardar.")
        os.makedirs(os.path.dirname(self._model_path), exist_ok=True)
        joblib.dump(self._pipeline, self._model_path)
        print(f"[Mar-ia][ml_engine] Modelo guardado en: {self._model_path}")

    def cargar_modelo(self) -> bool:
        """
        Carga el modelo desde disco. Si no existe, continúa sin él.
        Retorna True si la carga fue exitosa.
        """
        if not os.path.exists(self._model_path):
            print(f"[Mar-ia][ml_engine] Modelo no encontrado en: {self._model_path}")
            print("[Mar-ia][ml_engine] Ejecuta 'python entrenamiento.py' para generar el modelo.")
            self._listo = False
            return False
        try:
            self._pipeline = joblib.load(self._model_path)
            self._listo = True
            print(f"[Mar-ia][ml_engine] Modelo cargado exitosamente desde: {self._model_path}")
            return True
        except Exception as e:
            print(f"[Mar-ia][ml_engine] Error al cargar el modelo: {e}")
            self._listo = False
            return False

    # ─── Inferencia ───────────────────────────────────────────────────────────

    def predecir(self, texto: str) -> tuple[str | None, float]:
        """
        Clasifica el texto del usuario.

        Retorna:
            (intencion, confianza) si confianza >= CONFIANZA_MINIMA
            (None, 0.0)            si el modelo no está listo o confianza baja
        """
        if not self._listo or self._pipeline is None:
            return None, 0.0

        try:
            texto_limpio = texto.lower().strip()
            proba_array  = self._pipeline.predict_proba([texto_limpio])[0]
            clases       = self._pipeline.classes_
            idx_max      = int(np.argmax(proba_array))
            confianza    = float(proba_array[idx_max])
            intencion    = str(clases[idx_max])

            if confianza < self.CONFIANZA_MINIMA:
                return None, confianza

            return intencion, round(confianza, 4)

        except Exception as e:
            print(f"[Mar-ia][ml_engine] Error en predicción: {e}")
            return None, 0.0

    @property
    def esta_listo(self) -> bool:
        """True si el modelo está cargado y operativo."""
        return self._listo

    def obtener_clases(self) -> list[str]:
        """Retorna la lista de intenciones que el modelo conoce."""
        if not self._listo or self._pipeline is None:
            return []
        return list(self._pipeline.classes_)
