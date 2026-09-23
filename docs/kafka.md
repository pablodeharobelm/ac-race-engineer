# Fase 6.11: Kafka

```text
SimulatorSource -> Kafka telemetry.raw -> Bronze Parquet con payload y offsets
                                               |
                                       Quality audit -> Silver -> ventanas
```

El productor Python usa `confluent-kafka`. El sobre JSON versión 1 contiene
`source`, `session_type`, `setup_id` y el `TelemetryFrame` existente en `frame`.
La clave es `session_id`: las muestras de una sesión comparten partición.
`flush()` solo termina correctamente tras confirmar todas las entregas; los
errores de entrega, colas llenas y timeouts se propagan.

## Arranque local con Docker

Requiere Docker con contenedores Linux. Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,kafka]"
docker compose -f compose.kafka.yaml up -d --wait
.\.venv\Scripts\python.exe -m ac_race_engineer.kafka_demo topic
.\.venv\Scripts\python.exe -m ac_race_engineer.kafka_demo produce --samples 100
.\.venv\Scripts\python.exe -m ac_race_engineer.kafka_demo consume --samples 5
.\.venv\Scripts\python.exe -m ac_race_engineer.kafka_demo stream --available-now
```

El broker usa Kafka 4.3.1, KRaft y un volumen persistente. El puerto publicado
solo escucha en `127.0.0.1:9092`. Es una configuración de desarrollo con un
broker, sin autenticación ni redundancia. El listener interno para contenedores
es `kafka:19092`.

Para detenerlo conservando datos:

```powershell
docker compose -f compose.kafka.yaml down
```

Para producir continuamente, ejecuta `produce --continuous` en una terminal y
`stream` en otra. Ctrl+C detiene cada proceso. Se puede indicar otro broker
con `--bootstrap host:puerto`, otro tópico con `--topic` y otro destino de Spark
con `--output`. No se instala ni arranca Docker automáticamente.

## Spark y Windows

Usa Java 21 y la `.venv` según [la guía Windows](spark-windows.md).
`create_spark_session(enable_kafka=True)` carga el conector Maven
`org.apache.spark:spark-sql-kafka-0-10_2.13` con la versión de PySpark instalada.
El primer arranque requiere acceso a Maven Central. Kafka debe habilitarse antes
de crear Spark, en un proceso Python nuevo; las sesiones batch siguen sin cargar
el conector ni depender de Kafka.

Kafka Bronze conserva el valor y la clave binarios originales, tópico, partición,
offset y timestamp del broker. El tiempo de evento viene de `frame.timestamp`.
JSON malformado, versiones desconocidas o metadatos incorrectos pasan a cuarentena;
no se pierden ni provocan el avance silencioso sin registro de sus offsets.

`KafkaTelemetryStream.run_available()` drena Kafka y luego las capas existentes.
`start()` mantiene las cuatro consultas activas. Los checkpoints y los sinks
Parquet nativos controlan el progreso, no los commits de un consumer group Python.
`startingOffsets=earliest` solo rige un arranque sin checkpoint. En reinicios se
recuperan los offsets guardados. `failOnDataLoss=true` hace visible la pérdida de
offsets por retención o eliminación de un tópico; no se oculta con un salto.

La idempotencia del productor cubre reintentos del cliente durante su sesión.
Reenviar una muestra desde otra ejecución puede crear otro registro Kafka;
Silver aplica la deduplicación temporal descrita en [streaming](streaming.md).
No se promete deduplicación infinita ni una transacción entre todos los sinks.
Las ventanas pendientes siguen necesitando eventos posteriores para cerrarse.

El consumidor de inspección tiene un grupo único y no guarda offsets. Cierra la
conexión al terminar, incluso ante mensajes malformados. No modifica el progreso
de Spark. Los mensajes válidos se validan con los modelos Pydantic actuales.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
# Integración real, en un proceso independiente:
$env:AC_KAFKA_BOOTSTRAP = "127.0.0.1:9092"
.\.venv\Scripts\python.exe -m pytest tests/test_kafka_integration.py -v
Remove-Item Env:AC_KAFKA_BOOTSTRAP
```

La integración crea un tópico de prueba único `telemetry.test.*`; en un broker
compartido se puede eliminar después de revisar el resultado. Sin la variable
de entorno, el test de integración queda omitido explícitamente y el resto de
tests no necesita un broker. Incluye productor/consumidor, offsets únicos,
recuperación, deduplicación, mensajes inválidos y analíticas de ventanas.

Referencias: [Kafka Quickstart](https://kafka.apache.org/quickstart/),
[conector Spark 4.2](https://spark.apache.org/docs/4.2.0/streaming/structured-streaming-kafka-integration.html),
[cliente Python](https://docs.confluent.io/kafka-clients/python/current/overview.html).

Validado con un broker Apache Kafka 4.3.1 real en Windows, Java 21, Python 3.13
y PySpark 4.2. La configuración Docker Compose se proporciona para reproducir
el entorno, pero no se ha ejecutado en esta máquina porque Docker no está instalado.
