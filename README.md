# Mar-ia — Microservicio IA para SICGOV

**Mar-ia** es un agente inteligente basado en SVM que clasifica intenciones del usuario y orquesta la generación de reportes PDF para el sistema SICGOV.

## Stack

| Componente | Tecnología |
|---|---|
| Servidor API | FastAPI + Uvicorn |
| Motor ML | Scikit-Learn (TF-IDF + LinearSVC calibrado) |
| Base de Datos | PyMySQL → goobv-sistema / goobv-usuarios |
| Serialización | Joblib (.pkl) |

---

## Instalación

```bash
# Clonar / ubicarse en el proyecto
cd /home/gobdesarrollo/proyectos/mar-ia

# Crear entorno virtual
python3 -m venv venv

# Instalar dependencias
venv/bin/pip install -r requirements.txt

# Entrenar el modelo (genera models/mar_ia_model.pkl)
venv/bin/python entrenamiento.py

# Iniciar el servidor
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

---

## Endpoints

| Método | URL | Descripción |
|---|---|---|
| `GET` | `http://localhost:8090/health` | Estado del servicio y BD |
| `POST` | `http://localhost:8090/classify` | Clasificar + obtener JSON reporte |
| `GET` | `http://localhost:8090/intenciones` | Intenciones disponibles |
| `POST` | `http://localhost:8090/retrain` | Reentrenar modelo (requiere token) |
| `GET` | `http://localhost:8090/docs` | Documentación Swagger interactiva |

---

## Contrato JSON de `/classify`

**Request:**
```json
{
  "cedula": "V-12345678",
  "mensaje": "dame el inventario bajo"
}
```

**Response exitosa:**
```json
{
  "intencion": "reporte_inventario_bajo",
  "confianza": 0.9204,
  "metadata": {
    "titulo": "Reporte de Inventario Bajo",
    "generado_por": "Mar-ia",
    "fecha": "01/07/2026",
    "hora": "01:01 PM",
    "usuario": "V-12345678",
    "total_filas": 2
  },
  "documento_config": {
    "columnas": ["Insumo", "Stock Actual", "Stock Mínimo", "Unidad", "Estado"],
    "filas": [
      ["Leche", "1.36", "4.89", "L", "CRÍTICO"]
    ]
  },
  "error": null
}
```

---

## Integración en PHP — ReporteController.php

Agrega este bloque dentro del método que maneja la petición AJAX de reporte IA en SICGOV:

```php
/**
 * Llamada a Mar-ia (ORTOGONAL: si falla, SICGOV no se detiene)
 * Tiempo máximo de espera: 5 segundos
 */
private function consultarMarIa(string $cedula, string $mensaje): array
{
    $url     = "http://localhost:8090/classify";
    $payload = json_encode([
        'cedula'  => $cedula,
        'mensaje' => $mensaje,
    ]);

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $payload,
        CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
        CURLOPT_TIMEOUT        => 5,
        CURLOPT_CONNECTTIMEOUT => 3,
    ]);

    $respuesta = curl_exec($ch);
    $error     = curl_error($ch);
    curl_close($ch);

    if ($error || !$respuesta) {
        // Mar-ia no disponible — retornar estructura vacía segura
        return [
            'intencion'        => null,
            'confianza'        => 0.0,
            'metadata'         => [],
            'documento_config' => ['columnas' => [], 'filas' => []],
            'error'            => 'Mar-ia no disponible.',
        ];
    }

    return json_decode($respuesta, true) ?? [];
}
```

**Llamada desde el controlador:**
```php
case 'reporte_ia':
    $cedula   = $_SESSION['user']['cedula'];
    $mensaje  = $_POST['consulta_ia'] ?? '';
    $marIa    = $this->consultarMarIa($cedula, $mensaje);

    if ($marIa['error'] === null && !empty($marIa['documento_config']['filas'])) {
        // Pasar a ReportService para generar el PDF
        $pdf = ReportService::generarDesdeMarIa($marIa);
        echo json_encode(['resultado' => 200, 'datos' => $marIa, 'pdf' => $pdf]);
    } else {
        echo json_encode(['resultado' => 400, 'mensaje' => $marIa['error'] ?? 'Sin datos']);
    }
    break;
```

---

## Agregar nuevas intenciones

1. Abre `training_data.py`
2. Agrega la nueva clave con ≥10 frases de ejemplo:
   ```python
   "reporte_pedidos_pendientes": [
       "pedidos pendientes",
       "qué pedidos están en cocina",
       ...
   ]
   ```
3. Registra el conector en `db_connector.py` y el dispatcher en `main.py`
4. Agrega las columnas en `report_builder.py`
5. Reentrena:
   ```bash
   venv/bin/python entrenamiento.py
   # O vía API (requiere token):
   curl -X POST http://localhost:8090/retrain \
     -H "Content-Type: application/json" \
     -d '{"token":"mar-ia-token-sicgov-2026"}'
   ```

---

## Intenciones disponibles (v1.0)

| Intención | Trigger ejemplo | Fuente SQL |
|---|---|---|
| `reporte_inventario_bajo` | "dame el inventario bajo" | `vw_alertas_inventario` |
| `reporte_asistencia_diaria` | "asistencia de hoy" | `asistencia JOIN empleado` |
| `reporte_reservas_hoy` | "reservas de hoy" | `reservacion JOIN cliente` |
