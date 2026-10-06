# Local capture-to-dashboard demo

This demonstration uses the same `AssettoCorsaSource`, lap/sector trackers,
capture runner, SQL repositories and Parquet writer as the real capture path.
It generates a baseline lap followed by a slower lap with lower speed and later
throttle application in the first synthetic corner. It is a deterministic
software scenario, not a physics simulation or a calibrated model of Magione.

## Start without the game or Docker

From the repository root, activate the project environment. If necessary,
install it first with `python -m pip install -e ".[dev]"`.

```powershell
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "sqlite+pysqlite:///data/demo.sqlite"
python -m ac_race_engineer.demo_session --init-db
python -m uvicorn ac_race_engineer.api.app:create_local_app --factory --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run src/ac_race_engineer/dashboard/app.py --server.address 127.0.0.1
```

Open <http://127.0.0.1:8501>. The dashboard talks to the API; it does not need
direct database access. If using another API port, set `RACE_ENGINEER_API_URL`
in the dashboard terminal.

1. Open **Mis sesiones** and select the new session.
2. Choose lap 1 as reference and lap 2 as target.
3. Leave **Guardar en el historial** checked and AI explanations unchecked.
4. Click **Comparar mis vueltas** to see the comparison and coaching.
5. Open **Historial** to reopen the saved report. The session history mode also
   selects sessions by name rather than requiring a copied session ID.

Each demo run adds a new session; it does not delete previous sessions.
`--init-db` only creates missing SQLite tables. This helper is for the demo,
not a replacement for schema migrations on an existing production database.
Run all commands from the same repository root so relative Parquet paths resolve
consistently. Use **Actualizar sesiones** after another capture finishes; lists are
cached for up to five seconds to keep selection responsive.

## Use PostgreSQL instead

Set the same `DATABASE_URL` in the capture and API terminals. Then:

```powershell
docker compose up -d postgres
python -m alembic upgrade head
python -m ac_race_engineer.demo_session
```

Start the API using `create_local_app` as above. `--init-db` is intentionally
limited to SQLite. The real capture command writes to the same catalog and will
appear in **Mis sesiones** once completed lap events are committed.

## Spanish interface and session images

The dashboard presents labels, deterministic coaching and errors in Spanish.
New AI explanations are requested in Spanish. Charts explain units and the
meaning of positive/negative differences; lap and corner tables are optional
details rather than the primary workflow.

The bundled car illustration and circuit diagram are explicitly provisional.
The circuit diagram is not a Magione map and is not used to locate telemetry.
On the computer with Assetto Corsa installed, open **Imágenes del juego** in the
sidebar and enter the game's installation directory. Alternatively, set
`ASSETTO_CORSA_PATH` before starting the dashboard. Car previews are read from
the car's `ui` directory or a skin's `preview.jpg`; track images use `map.png`
or `ui/preview.png`. No game connection is needed for these local assets.

## API routes

| Route | Purpose |
| --- | --- |
| `GET /v1/sessions?limit=20` | Recent sessions, cars, tracks and lap/trace counts |
| `GET /v1/sessions/{session_id}/laps` | Completed laps and trace availability |
| `GET /v1/sessions/{session_id}/laps/{lap_number}/trace` | Samples for a recorded lap |
| `POST /v1/sessions/{session_id}/analyze` | Compare recorded laps and optionally save the report |

For the last route, supply `reference_lap_number` and `target_lap_number`.
`persist` defaults to `true`, `explain` to `false`, and `grid_points` to `201`.
Comparison is limited to laps from the same session. Missing sessions/laps
return 404; missing, corrupt, unsupported or inconsistent traces return 409;
unavailable/unmigrated databases return 503. A lap without a complete trace
remains visible but cannot be selected for comparison.

The `/health` route confirms that the API is responding; it does not check
database readiness. Storage errors are reported when loading sessions/history.

## Automated verification

```powershell
python -m pytest -q tests/test_captured_session_workflow.py
```

These tests capture actual synthetic frames into a temporary SQL database and
Parquet files, run the real analysis pipeline through FastAPI, reopen the saved
report, and exercise the Streamlit selection workflow. They also verify failure
responses and that damaged traces do not create a saved analysis.

The original constant `--fake` capture backend remains useful for low-level
reader checks; it does not traverse complete laps. Use `demo_session` for this
end-to-end demonstration.

## Modo conducción

Abre **Conducción** para recorrer dos vueltas simuladas sin necesitar el juego ni el servicio de análisis. Pulsa **Reproducir**, **Pausar** o **Reiniciar**; puedes avanzar a velocidad 1×, 2× o 4×. Los indicadores se actualizan cuatro veces por segundo. La primera vuelta coincide con la referencia; la segunda pierde tiempo en la primera curva. La diferencia compara el tiempo de ambas vueltas en el mismo punto del recorrido. La marcha es estimada y no procede del juego. Al cambiar a otra sección, la reproducción se pausa. Esta demostración no guarda sesiones ni representa una conexión en directo con Assetto Corsa.

El panel utiliza tema oscuro, acelerador verde, freno rojo y embrague azul claro. El embrague aparece como «Sin datos» cuando el archivo no contiene su telemetría. Las diferencias positivas se muestran en rojo, las negativas en verde y las prácticamente nulas en gris.

## Evolución de la sesión

En **Mis sesiones** puedes ver el mejor tiempo, el ritmo medio, la última vuelta y su diferencia respecto a la anterior registrada. El gráfico alterna entre tiempos y diferencia respecto al mejor tiempo. La regularidad se calcula como desviación estándar a partir de tres vueltas cronometradas. Se omiten tiempos no positivos, pero se conservan vueltas sin archivo de telemetría. No se excluyen vueltas de boxes ni penalizaciones porque esa información aún no está disponible.

## Reproducir vueltas guardadas

En **Conducción → Vueltas guardadas**, selecciona una sesión, una referencia y la vuelta que quieres revisar. Pulsa **Cargar vuelta** y después **Reproducir**. La reproducción permite pausar, reiniciar y avanzar a 1×, 2× o 4×. La diferencia se interpola en la misma posición del circuito y se oculta fuera del tramo cubierto por la referencia. Las nuevas capturas muestran la marcha y el embrague registrados; los archivos anteriores muestran esos indicadores sin datos. Se reproducen archivos guardados; no es una conexión en directo con el juego.

## Informes descargables

Después de comparar vueltas, pulsa **Descargar informe**. El archivo HTML se abre en cualquier navegador, sin necesitar la aplicación. Incluye vueltas, balance por curvas, consejos en español y explicación de IA si está disponible en español. Puedes imprimirlo o guardarlo como PDF desde el navegador. También está disponible al abrir un análisis en **Historial** y después de analizar **Importar datos**. El balance por curvas no equivale a la diferencia total de la vuelta.

Las descargas desde **Mis sesiones** e **Importar datos** incluyen también las gráficas de velocidad, acelerador y freno, y el resumen de muestras, separaciones y tramo compartido. Las gráficas SVG están dentro del HTML y no requieren internet. La referencia aparece azul discontinua; la vuelta analizada usa línea continua, con acelerador verde y freno rojo. Los informes abiertos desde Historial conservan el resumen original sin gráficas de telemetría, porque esa vista no carga las muestras.

Las nuevas capturas incluyen marcha y embrague en cada muestra. Los archivos anteriores, sin esas columnas opcionales, siguen siendo legibles y muestran «Sin datos». En reproducción, la marcha se conserva como valor discreto (R, N o número); el embrague se interpola entre muestras. La demostración integrada sigue mostrando su marcha estimada.

## Conexión en directo

Abre **Conducción → En directo**. Por defecto está activada **Probar conexión simulada**, con los estados En pista, En pausa, Esperando al juego y Desconectado. Desactiva esa opción para leer la memoria compartida del juego en el mismo ordenador Windows donde corre Streamlit. El panel muestra velocidad, marcha, tiempo y pedales; no guarda la sesión. Para registrar sesiones sigue usando el proceso de captura documentado. Cuando no hay datos, los indicadores se ocultan. Se detectan paquetes sin actualizar tras dos segundos (excepto durante pausa) y se reintenta la conexión cada dos segundos. Las repeticiones del juego se identifican por separado. La lectura real y la comparación de referencia en directo quedan pendientes de validar en el ordenador con Assetto Corsa.

### Referencia en directo

En la simulación se compara la segunda vuelta con la primera. Para el juego local, activa **Comparar con una vuelta guardada**, selecciona sesión y vuelta y pulsa **Usar como referencia**. La referencia se carga una vez; el panel calcula la diferencia en cada actualización sin volver a pedir el archivo. La diferencia solo se muestra para el mismo coche y circuito y dentro del tramo que cubre la referencia. No valida aún condiciones de pista, penalizaciones ni diferencias de configuración del coche.

## Sesión de práctica de seis vueltas

Ejecuta `python -m ac_race_engineer.demo_session --laps 6` con el mismo catálogo de la API para añadir una práctica más larga. Incluye la referencia, una vuelta lenta y varias mejoras con una pequeña variación de ritmo. Permite comprobar el gráfico de evolución, regularidad, selección del mejor tiempo y comparaciones. Es un escenario sintético, no un modelo físico del circuito. El parámetro `--laps` permite de 2 a 20 vueltas y conserva el comportamiento anterior de dos vueltas por defecto. El lanzador `--demo` genera seis vueltas; puedes cambiarlo con `--demo-laps`.

## Llevar vueltas a otro ordenador

Después de comparar una sesión en **Mis sesiones**, abre **Llevar estas vueltas a otro ordenador** y descarga los dos archivos de vuelta. En el otro ordenador abre **Importar datos → Archivos** y selecciona la referencia y la vuelta analizada. Los archivos conservan las muestras y los datos opcionales de marcha y embrague. Los números introducidos en la pantalla identifican las vueltas en el nuevo análisis. Si ambos archivos incluyen contexto, se exige el mismo coche y circuito. La importación no añade una sesión al catálogo; permite comparar y guardar el análisis en el historial. Para probar sin archivos, selecciona **Datos de ejemplo**. **Pegar JSON** conserva la entrada avanzada.

## Revisión de estabilidad

La revisión local incluye captura, almacenamiento, API, panel, importación, informes y simulación. Las pruebas de Spark y las que requieren un broker Kafka no forman parte de esta revisión local. La simulación conserva su posición al pausar o desconectar; el monitor espera nuevos paquetes al reanudar el juego y oculta estados desconocidos. La importación rechaza muestras incompletas, fuera de rango o no finitas antes de enviarlas al análisis. La comprobación final con Assetto Corsa continúa pendiente en el ordenador del juego.

La importación admite también listas con `lap_distance_m`, `throttle_pct`, `brake_pct` y `steering_deg`, y listas dentro de una clave de circuito. Si faltan los tiempos, hay que activar **Permitir tiempos estimados**: se aproxima el tiempo usando la distancia y la velocidad media entre muestras. Se usa una escala de distancia común para los dos archivos y se compara solo el tramo compartido. Los huecos grandes reducen la precisión. Estos análisis aproximados no se guardan en el historial y los informes indican la estimación.

## Reproducir los JSON comparados

Después de importar, **Qué datos estamos comparando** muestra el número de muestras de cada archivo, el tramo común y la mayor separación entre puntos. La cobertura se refiere a los extremos registrados, no a una vuelta completa verificada. Las separaciones mayores al 5 % del recorrido generan un aviso orientativo; no se asigna una puntuación de confianza ni se interpreta ese umbral como medida de precisión. Aumentar los puntos de comparación interpola el gráfico, pero no añade telemetría original.

Tras comparar dos archivos en **Importar datos**, abre **Conducción → Vueltas importadas**. Se reproduce la vuelta analizada y se usa la misma referencia. Los tiempos estimados conservan su aviso y los indicadores opcionales sin telemetría muestran **Sin datos**. Los archivos permanecen en la sesión del navegador; al recargarla tendrás que importarlos otra vez.

En las reproducciones puedes abrir **Buscar un momento de la vuelta** y mover **Saltar a un momento (segundos)**. El panel salta a ese instante y se pausa para revisar velocidad y pedales; **Reproducir** continúa desde ahí y **Reiniciar** vuelve al comienzo. La diferencia se oculta fuera del tramo cubierto por la referencia.

**Cómo estás girando** muestra el ángulo del volante y el de la referencia en la misma posición. Se interpolan los ángulos registrados, conservando su signo. No se deduce izquierda o derecha sin conocer la convención del archivo, ni se interpreta más giro como una mejora. Fuera del tramo compartido, el ángulo de referencia se oculta. Está disponible en demostración y reproducción de vueltas guardadas o importadas.

En las gráficas del análisis, **Volante** muestra el ángulo a lo largo del recorrido con una línea horizontal de cero. La referencia es azul discontinua; tu vuelta es continua, con acelerador verde, freno rojo y volante violeta. Estas gráficas están disponibles al comparar sesiones guardadas y archivos importados.

Abre **Centrar el análisis en un tramo** para elegir el inicio y el final de la zona visible. El tramo se conserva al cambiar de velocidad a pedales, volante o diferencia de tiempo; **Ver todo el recorrido** restablece la vista completa. La selección solo cambia la gráfica: no recalcula las recomendaciones ni reinicia la diferencia acumulada. Las líneas entre muestras siguen siendo interpoladas.
