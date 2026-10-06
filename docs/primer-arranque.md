# Primera prueba en el ordenador con Assetto Corsa

Copia o clona el proyecto en el ordenador del juego. El entorno `.venv` debe crearse allí; no copies el de otro ordenador. Necesitas Python 3.11 o superior compatible con las dependencias del proyecto.

Desde la carpeta del proyecto, prepara el entorno una vez:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/python.exe -m ac_race_engineer.local_launcher --check
```

Haz doble clic en **iniciar-aplicacion.bat**. Abre la dirección que aparece. El lanzador inicia los dos servicios, usa `data/local.sqlite` y conserva las sesiones existentes. No necesita Docker ni PostgreSQL. Si un puerto está ocupado, no detiene ningún proceso ajeno: cierra el arranque anterior o ejecuta:

```powershell
.venv/Scripts/python.exe -m ac_race_engineer.local_launcher --api-port 8001 --panel-port 8502
```

Para añadir una sesión simulada y comprobar el análisis antes de entrar al juego:

```powershell
.venv/Scripts/python.exe -m ac_race_engineer.local_launcher --demo
```

Cada uso de `--demo` añade una sesión simulada de seis vueltas. Puedes elegir de 2 a 20 con `--demo-laps`, por ejemplo `--demo --demo-laps 8`. La base local del lanzador es distinta de `data/demo.sqlite`, usada en las pruebas anteriores. No mueve ni elimina datos. Los registros de arranque están en `data/logs`. Este arranque usa el catálogo SQLite local; para un despliegue PostgreSQL usa el procedimiento habitual de migraciones.

## Probar el juego

1. Inicia Assetto Corsa y entra en una sesión.
2. En la aplicación abre **Conducción → En directo** y desactiva **Probar conexión simulada**.
3. Comprueba velocidad, marcha, pedales y tiempo. Prueba pausa, vuelta a pista y cierre del juego: los indicadores deben ocultarse si se pierde la lectura.
4. Configura la carpeta del juego en **Imágenes del juego** para usar sus imágenes.
5. El panel en directo no registra sesiones. Para capturar vueltas usa el proceso de captura, con `DATABASE_URL` apuntando a `sqlite+pysqlite:///data/local.sqlite`, desde la misma carpeta del proyecto. Consulta las opciones con `.venv/Scripts/python.exe -m ac_race_engineer.assetto_corsa_capture --help`.
6. Después de registrar dos vueltas completas, abre **Mis sesiones → Actualizar sesiones**. Compara las vueltas y prueba la reproducción.

La marcha y el embrague reales, la pausa y la reconexión aún deben validarse con el juego. La comparación en directo requiere una referencia del mismo coche y circuito; todavía no filtra penalizaciones, boxes ni condiciones de pista.

Para cerrar, escribe **salir** y pulsa Intro, o pulsa **Ctrl+C**, en la ventana del lanzador. Solo detiene los servicios que él ha iniciado; conserva los datos. Si cierras la ventana por la fuerza, puede quedar algún proceso activo.
