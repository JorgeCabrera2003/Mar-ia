# 🧠 **Mar-ia - Microservicio de IA para SICGOV**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.6-F7931E.svg)](https://scikit-learn.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v2.0.0--active-success.svg)](#)

## 📌 Tabla de Contenidos
1. [¿Qué es Mar-ia?](#-qué-es-mar-ia)
2. [Conceptos Clave de la Inteligencia Artificial](#-conceptos-clave-de-la-inteligencia-artificial)
3. [Flujo de Datos (Cómo funciona)](#-flujo-de-datos-cómo-funciona)
4. [Estructura del Proyecto y Archivos](#-estructura-del-proyecto-y-archivos)
5. [Guía de Instalación Paso a Paso](#-guía-de-instalación-paso-a-paso)
6. [Cómo Entrenar a Mar-ia (Para Desarrolladores)](#-cómo-entrenar-a-mar-ia-para-desarrolladores)
7. [Librerías y Tecnologías Utilizadas](#-librerías-y-tecnologías-utilizadas)
8. [Capacidades Actuales (Intenciones)](#-capacidades-actuales-intenciones)
9. [Integración con SICGOV (PHP)](#-integración-con-sicgov-php)

---

## 🤖 ¿Qué es Mar-ia?

**Mar-ia** es un microservicio de Inteligencia Artificial diseñado específicamente para integrarse con **SICGOV (Sistema de Información Complementario Good Vibes)**. Actúa como el "cerebro" analítico del restaurante, permitiendo a los administradores hacer preguntas en lenguaje natural (ej. *"¿Qué insumos están bajos de stock?"* o *"Dame las reservas de hoy"*) y recibir reportes en PDF estructurados en cuestión de segundos.

Mar-ia no es un simple buscador de palabras clave. Utiliza **Machine Learning (Aprendizaje Automático)** para entender la *intención* real detrás de lo que escribe el usuario, extrayendo parámetros complejos (fechas, nombres, cédulas) y convirtiéndolos dinámicamente en consultas a la base de datos de SICGOV.

---

## 🧠 Conceptos Clave de la Inteligencia Artificial

Para que cualquier miembro del equipo pueda entender y mejorar a Mar-ia, aquí están los conceptos fundamentales de cómo "piensa":

- **Procesamiento de Lenguaje Natural (NLP):** Es la rama de la IA que ayuda a las computadoras a entender, interpretar y manipular el lenguaje humano.
- **TF-IDF (Term Frequency - Inverse Document Frequency):** Es una técnica matemática que Mar-ia usa para convertir las oraciones de texto en números. Le da mucha importancia a palabras clave (como "inventario" o "reservas") y le quita peso a palabras comunes (como "el", "la", "de").
- **Support Vector Machine (SVM - LinearSVC):** Es el algoritmo matemático principal de Mar-ia. Imagina que traza una línea invisible en un espacio tridimensional para separar las frases que significan "quiero el inventario" de las frases que significan "quiero las reservas".
- **Calibración de Probabilidad:** SVM por defecto no dice "estoy 90% seguro". Para lograr esto, Mar-ia usa un *CalibratedClassifierCV* que ajusta las predicciones para que el sistema pueda decir "Estoy 95% seguro de que el usuario quiere este reporte", permitiendo ignorar peticiones confusas.
- **Microservicio API:** Mar-ia vive en su propio servidor separado de PHP. Esto se llama arquitectura orientada a microservicios. Si Mar-ia se apaga, el sistema principal SICGOV sigue funcionando sin problemas (ortogonalidad).

---

## 🔄 Flujo de Datos (Cómo funciona)

El ciclo de vida de una consulta desde que el usuario escribe hasta que recibe el PDF es el siguiente:

1. **Entrada (Usuario):** El administrador de SICGOV escribe: *"Muestrame las reservas para mañana en la terraza"*.
2. **Petición (PHP → Python):** El backend de PHP envía esa frase al endpoint `/classify` de Mar-ia mediante cURL.
3. **Clasificación (Motor ML):** El modelo `mar_ia_model.pkl` analiza el texto, usa TF-IDF y SVM para clasificar la intención como `reporte_reservas_hoy`.
4. **Extracción (Parámetros):** El archivo `param_extractor.py` analiza el texto y se da cuenta de que dice *"mañana"* (calcula la fecha de mañana) y *"terraza"* (filtro de área).
5. **Consulta a BD (SQL):** Mar-ia se conecta a la base de datos de SICGOV, arma un `SELECT` dinámico con las fechas y áreas extraídas, y obtiene los registros puros.
6. **Limpieza (Data Cleaner):** Los datos puros se pasan por `data_cleaner.py` para darle formato a las fechas, quitar ceros redundantes a los decimales y acomodar valores nulos.
7. **Respuesta JSON:** Mar-ia empaqueta un JSON perfecto con las columnas, las filas limpias y metadatos, y lo devuelve a PHP.
8. **Renderizado (PHP):** SICGOV recibe el JSON, genera el PDF usando su librería `TCPDF` y se lo muestra al usuario.

---

## 📁 Estructura del Proyecto y Archivos

Cada archivo en Mar-ia tiene un propósito único. Esta guía es vital para que el equipo pueda continuar el desarrollo:

- **`main.py`**: El corazón del servidor web. Aquí se definen los endpoints (las URLs como `/classify`) usando FastAPI. Es lo que mantiene a Mar-ia escuchando peticiones.
- **`entrenamiento.py`**: El script que toma las frases de ejemplo, entrena matemáticamente a la IA y guarda el cerebro resultante en un archivo físico `.pkl`.
- **`training_data.py`**: **El diccionario de Mar-ia.** Aquí es donde el equipo escribe las frases de ejemplo (ej. *"dame las reservas"*, *"muestrame la agenda"*) para enseñar a la IA a reconocer nuevas intenciones.
- **`model_service.py`**: Se encarga de cargar el modelo `.pkl` en la memoria RAM y usarlo para predecir qué significa una frase nueva.
- **`param_extractor.py`**: Módulo avanzado de NLP. Extrae inteligencia de la frase (nombres propios, cédulas, cálculos de fechas como "la semana pasada", límites numéricos).
- **`db_connector.py`**: Contiene la lógica para conectarse a MySQL (Base de datos de SICGOV) y ejecuta las consultas SQL correspondientes a la intención detectada.
- **`data_cleaner.py`**: Un filtro de belleza. Toma los datos feos de la base de datos (con demasiados decimales, fechas en formatos raros) y los deja perfectos y limpios para el reporte final.
- **`report_builder.py`**: Ensambla el paquete final. Toma los datos limpios, les pone títulos bonitos a las columnas y crea la estructura JSON exacta que SICGOV espera.
- **`iniciar_ia.bat`**: Script de Windows para levantar el servidor de IA con un solo doble clic, ideal para entornos de desarrollo locales.

---

## 🚀 Guía de Instalación Paso a Paso

Diseñado para que cualquier persona, sin importar su experiencia en Python, pueda instalar Mar-ia.

### 1. Clonar el repositorio
Abre tu terminal (Git Bash o CMD) y descarga el proyecto desde GitHub:
```bash
git clone https://github.com/JorgeCabrera2003/Mar-ia.git
cd Mar-ia
```

### 2. Crear un Entorno Virtual (VENV)
**¿Por qué hacemos esto?** Un entorno virtual es como una "burbuja" aislada para el proyecto. Evita que las librerías de Mar-ia hagan conflicto con otros proyectos de Python que tengas en tu computadora.
```bash
python -m venv venv
```
*(Esto creará una carpeta llamada `venv` que contiene un Python limpio).*

### 3. Activar el Entorno Virtual
- **En Windows:**
  ```cmd
  venv\Scripts\activate
  ```
- **En Linux / Mac:**
  ```bash
  source venv/bin/activate
  ```
*(Sabrás que funcionó porque tu terminal dirá `(venv)` al principio de la línea).*

### 4. Instalar Dependencias
Le decimos a Python que instale exactamente las versiones de las librerías que Mar-ia necesita para pensar:
```bash
pip install -r requirements.txt
```

### 5. Entrenar el Cerebro por Primera Vez
Antes de iniciar, Mar-ia necesita estudiar sus datos de entrenamiento para generar su modelo matemático:
```bash
python entrenamiento.py
```
*(Verás un mensaje diciendo que el modelo se guardó con éxito en `models/mar_ia_model.pkl`).*

### 6. Iniciar el Servidor
Para encender a Mar-ia y dejarla escuchando peticiones en el puerto 8090:
```bash
uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```
🔥 **Atajo para Windows:** Si estás en Windows, simplemente dale doble clic al archivo `iniciar_ia.bat`. Este hará los pasos 3 y 6 automáticamente por ti.

---

## 🎓 Cómo Entrenar a Mar-ia (Para Desarrolladores)

Si creaste un nuevo módulo en SICGOV (por ejemplo, "Reporte de Empleados") y quieres que Mar-ia lo entienda, sigue este flujo:

### Paso 1: Añadir datos de entrenamiento
Abre `training_data.py`. Vas a crear una nueva "intención" y le vas a dar al menos 10 a 15 formas en las que un humano pediría ese reporte.
```python
"reporte_empleados": [
    "dame la lista de empleados",
    "quienes trabajan aqui",
    "muestrame el personal activo",
    "directorio de trabajadores",
    # ... añade variaciones de palabras y sinónimos
]
```

### Paso 2: Configurar las columnas
Abre `report_builder.py`. Busca el diccionario `REPORTE_CONFIG` y dile cómo se llamará el PDF y qué columnas tendrá:
```python
"reporte_empleados": {
    "titulo": "Directorio de Empleados Activos",
    "columnas": ["Cédula", "Nombre", "Cargo", "Teléfono"],
},
```

### Paso 3: Conectar a la Base de Datos
Abre `db_connector.py`. Crea una función SQL que traiga exactamente esas columnas de la base de datos y regístrala en el diccionario `DISPATCHER` al final del archivo.

### Paso 4: Reentrenar el modelo
Para que Mar-ia aprenda tus nuevas frases, debes borrar su memoria anterior y compilar una nueva. En tu terminal, con el entorno virtual activado, corre:
```bash
python entrenamiento.py
```
¡Listo! Mar-ia ahora es más inteligente y conoce tu nuevo reporte.

---

## 📚 Librerías y Tecnologías Utilizadas

Para garantizar estabilidad y rendimiento, Mar-ia usa un ecosistema de librerías modernas de la industria.

| Librería | Versión | Licencia | ¿Por qué se usó? (Propósito) |
|----------|---------|----------|------------------------------|
| **FastAPI** | `0.115.6` | MIT | Framework web extremadamente rápido. Crea la API REST y maneja las peticiones HTTP que envía PHP. Elegido por su velocidad superior a Flask o Django. |
| **Uvicorn** | `0.32.1` | BSD | Servidor web asíncrono (ASGI). Es el "motor" que ejecuta a FastAPI para que pueda manejar múltiples peticiones al mismo tiempo sin colapsar. |
| **Scikit-Learn** | `1.6.1` | BSD | La librería principal de Machine Learning. Contiene los algoritmos matemáticos (SVM, TF-IDF) que dotan de inteligencia a Mar-ia. |
| **NumPy** | `2.2.1` | BSD | Usada bajo el capó por Scikit-Learn para hacer cálculos de matrices y álgebra lineal a velocidades de lenguaje C. |
| **PyMySQL** | `1.1.1` | MIT | Driver para conectarse de forma nativa desde Python a la base de datos MariaDB/MySQL de SICGOV, permitiendo ejecutar `SELECTs` directos. |
| **Joblib** | `1.4.2` | BSD | Serializador. Toma el cerebro entrenado de Mar-ia (que vive en RAM) y lo guarda en un archivo `.pkl` en el disco duro, y viceversa. Es más eficiente que `pickle`. |
| **Pydantic** | `2.10.4` | MIT | Validador de datos. Asegura que los JSON que PHP le envía a Mar-ia tengan la estructura correcta (ej. que la cédula sea un string válido) antes de procesarlos. |
| **Python-dotenv** | `1.0.1` | BSD | Permite que Mar-ia lea variables de entorno desde un archivo `.env` para no dejar contraseñas de bases de datos expuestas en el código fuente. |

---

## 🌟 Capacidades Actuales (Intenciones)

En la versión **v2.0.0**, Mar-ia es capaz de procesar de forma nativa las siguientes intenciones:

- **Inventario:** `"dame el inventario bajo"` → Lee de `vw_alertas_inventario`.
- **Asistencia:** `"asistencia de hoy"` → Cruza datos de marcación diaria con la tabla de empleados.
- **Reservaciones:** `"reservas de mañana"` → Gestiona la agenda. Es capaz de aplicar filtros temporales avanzados gracias al `param_extractor.py`.
- **Clientes:** `"reporte de clientes"` → Listado de clientes registrados en la plataforma.
- **Menú y Platillos:** `"muestrame el menu"` → Catálogo de productos y categorías.
- **Pedidos en Curso:** `"pedidos pendientes en cocina"` → Status de órdenes del restaurante.
- **Búsqueda Dinámica:** `"busca a la persona V-12345678"` → Rastrea cédulas inteligentemente en todo el sistema.

---

## 🔌 Integración con SICGOV (PHP)

El diseño de Mar-ia asegura que si el servidor de IA llega a fallar, el sistema SICGOV principal **no se cae** (Ortogonalidad). 

En SICGOV, se realiza una petición cURL en `ReporteController.php` con un **timeout estricto de 5 segundos**. Si Mar-ia no responde, PHP asume el control y devuelve un mensaje de error elegante al frontend en lugar de bloquear el servidor.

**Contrato JSON que Mar-ia devuelve:**
```json
{
  "intencion": "reporte_inventario_bajo",
  "confianza": 0.9204,
  "metadata": {
    "titulo": "Reporte de Inventario General",
    "generado_por": "Mar-ia",
    "fecha": "04/07/2026",
    "hora": "12:32 PM",
    "usuario": "V-12345678",
    "total_filas": 27
  },
  "documento_config": {
    "columnas": ["Insumo", "Stock Actual", "Stock Mínimo", "Unidad", "Estado"],
    "filas": [
      ["Guisantes", "4", "1", "Kilogramo", "OK"],
      ["Carne de res", "15.8", "3.107", "Kilogramo", "OK"]
    ]
  },
  "error": null
}
```
*(Nota: Gracias al módulo de depuración, los valores decimales como `15.80000000` son limpiados inteligentemente a `15.8` antes de ser devueltos a PHP).*
