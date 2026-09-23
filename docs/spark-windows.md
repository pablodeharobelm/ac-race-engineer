# Spark local en Windows

Entorno validado: Python 3.13, PySpark 4.2 y Java 21, usando `.venv`.
Antes de ejecutar los tests, abre PowerShell en el repositorio:

```powershell
$env:JAVA_HOME = [Environment]::GetEnvironmentVariable("JAVA_HOME", "User")
if (-not $env:JAVA_HOME) {
    $env:JAVA_HOME = [Environment]::GetEnvironmentVariable("JAVA_HOME", "Machine")
}
# Ajusta esta ruta a tu instalación de Hadoop para Windows.
$env:HADOOP_HOME = "C:\hadoop"
$env:PATH = "$env:JAVA_HOME\bin;$env:HADOOP_HOME\bin;$env:PATH"
& "$env:JAVA_HOME\bin\java.exe" -version
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Hadoop requiere `bin/winutils.exe` y `bin/hadoop.dll`. Una aplicación abierta
antes de configurar JAVA_HOME puede conservar un entorno antiguo: reiníciala
o carga las variables como arriba. La fábrica de sesiones usa el ejecutable
Python activo también para los workers.

## Fase 6.8: Spark Gold

Gold calcula la huella de Silver dentro de Spark; Python no recorre ni abre
los archivos `part-*`, cuyas rutas temporales pueden ser largas en Windows.
La huella incluye el esquema y valores con campos nulos explícitos, conserva
duplicados y no depende del orden de filas, columnas o particiones. Es una
huella para detectar cambios, no una firma criptográfica del dataset.

Las columnas Gold siguen el contrato pandas, incluido `maximum_lateral_g`.
El consumo de combustible usa el orden `(timestamp, sample_index)`.
Los tests comparan el conjunto de columnas y todas las métricas numéricas.
Los tiempos de procesamiento de pandas y Spark son independientes.
