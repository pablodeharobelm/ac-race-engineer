# Fase 6.10: Structured Streaming

La entrada es un directorio plano de archivos Bronze Parquet inmutables.
`TelemetryStreamPublisher` obtiene muestras del `TelemetrySource` existente,
reutiliza el formato Bronze y publica cada archivo mediante renombrado en el
mismo directorio. Spark nunca debe leer un archivo que todavía se está escribiendo.

```text
SimulatorSource -> Bronze por microbatches
                    |
                    v
              Quality audit (Parquet)
                    |
              válidos + watermark + deduplicación
                    |
                    v
                Silver (Parquet)
                    |
              watermark + ventanas por evento
                    |
                    v
            Analytics por ventana (Parquet)
```

Cada etapa tiene su consulta y checkpoint independiente. Se usan sinks Parquet
nativos, con su registro `_spark_metadata`, para recuperar escrituras sin
duplicarlas. Hay que conservar conjuntamente entradas inmutables, checkpoints
y salidas, y leer cada dataset por su directorio raíz, sin glob de `part-*`.
No se debe modificar una entrada publicada ni compartir un checkpoint entre
consultas. Los archivos nuevos deben tener nombres únicos.

## Uso en Windows

Configura Java/Hadoop y usa la `.venv` como indica [la guía Windows](spark-windows.md).

Demo acotada, sin esperas entre muestras:

```powershell
.\.venv\Scripts\python.exe -m ac_race_engineer.spark_streaming_demo --batches 3
```

Simulación continua, con muestreo a 20 Hz y microbatches:

```powershell
.\.venv\Scripts\python.exe -m ac_race_engineer.spark_streaming_demo --continuous --hz 20
```

Ctrl+C cierra las consultas y Spark. Al ejecutar la demo otra vez se inicia una
nueva sesión simulada, mientras los checkpoints conservan lo ya procesado.
Aquí "continua" describe la producción de muestras; el motor usa microbatches,
no el modo experimental Continuous Processing de Spark.

## API y semántica

`SparkTelemetryStream(spark, input_directory, schema, output_directory)` recibe
un esquema explícito `StructType` del contrato Bronze. `start()` arranca las
tres consultas y devuelve un objeto con `check()`, `drain()` y `stop()`.
`run_available()` procesa lo disponible por etapas y termina, conservando el
estado para otra ejecución. La clase nunca cierra la sesión Spark del llamador.

- Quality reutiliza `SparkSilverTelemetryProcessor.transform`, también usado
  por batch. Conserva todas las entradas y sus indicadores de calidad.
- `read_quarantine()` devuelve las filas inválidas del audit, incluidas aquellas
  sin timestamp. No entran en Silver ni en las analíticas.
- Silver deduplica por `(session_id, sample_index)` dentro del watermark
  (10 segundos por defecto). Esto limita el estado; no promete deduplicación
  ilimitada de claves reaparecidas fuera del horizonte conservado.
- Las filas demasiado antiguas pueden ser descartadas por las etapas con
  estado. Permanecen en el audit; ser tardía no marca por sí solo una fila
  como inválida. Los contadores de Spark están en el progreso de las consultas.
- Analytics agrupa ventanas de 10 segundos por sesión/coche/circuito y calcula
  muestras, velocidad y métricas de presión y temperatura. Solo emite ventanas
  cerradas por el watermark. Esperar tiempo de reloj no cierra ventanas: hacen
  falta eventos posteriores. La última ventana de un flujo detenido queda
  pendiente. No se insertan muestras ficticias para cerrarla.
- Estas analíticas son por ventana, no sustituyen al Gold de una fila por sesión.
  La paridad batch se mantiene para datos válidos aceptados, dentro del margen
  temporal y sin duplicados conflictivos.

La configuración de entrada, esquema, zona horaria, particiones de shuffle,
versiones, ventana y watermark se guarda junto a las salidas. Cambiarla requiere
otro directorio de salida y nuevos checkpoints. Una salida admite un único
productor por consulta; el control de nombres evita duplicar consultas en la
misma sesión Spark. No arranques procesos independientes sobre esa misma salida.

## Validación

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_spark_streaming.py tests/test_stream_publisher.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Los tests cubren paridad con pandas Silver, varios microbatches, duplicados entre
lotes, cuarentena de nulos, reinicio con checkpoint, eventos desordenados y
demasiado tardíos, cierre de ventanas, consultas activas y publicación atómica.

Referencia: [guía oficial Structured Streaming de Spark 4.2](https://spark.apache.org/docs/4.2.0/streaming/apis-on-dataframes-and-datasets.html).
Transporte Kafka: [fase 6.11](kafka.md).
