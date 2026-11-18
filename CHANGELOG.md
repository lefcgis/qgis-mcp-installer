# Cambios

## 2.0.0 — 2026-11-18

Revisión completa tras reportes de que el instalador «no quedaba al 100 %» en
algunos equipos. Se reprodujeron los fallos en un Windows 11 con Smart App
Control activado y sin administrador, y se corrigió la causa de cada uno.

### Errores corregidos

- **El servidor MCP no arrancaba aunque el instalador decía «instalación
  completa».** El paso 6 configuraba Claude con `uv run --no-sync server.py`,
  que no usa el entorno creado en el paso 3: el servidor moría con
  `ModuleNotFoundError: No module named 'mcp'`. Ahora Claude ejecuta un
  intérprete propio con las librerías instaladas, por ruta absoluta.
- **Smart App Control bloqueaba el `python.exe` del entorno virtual** (es un
  lanzador sin firma). Ya no se crea ningún venv: se usa el `python.exe` real de
  la distribución y las librerías van a `env\site-packages`.
- **Dependía del Python que hubiera en el equipo.** Con el `.exe`, buscaba
  `python` en el PATH (que en Windows suele ser el alias de la Microsoft Store) o
  el Python de QGIS. Ahora descarga `uv` (hash fijado) y un CPython 3.12 propio.
- **Claude Desktop no se detectaba** cuando estaba instalado como paquete MSIX
  (la forma en que se distribuye hoy), y se descargaba un instalador de octubre
  de 2025 con un parámetro silencioso que no le correspondía. Ahora se detecta el
  MSIX y se usa el paquete oficial vigente.
- **QGIS se daba por instalado si quedaba una carpeta `QGIS x.y.z\bin` vacía**
  de una desinstalación anterior, y entonces nunca se instalaba. Ahora se exige
  el ejecutable.
- **La instalación de QGIS sin administrador fallaba a media descarga** cuando la
  carpeta raíz era larga (límite de 260 caracteres de Windows). Se acortó la
  carpeta de paquetes y se valida la longitud antes de empezar.
- **El MSI legítimo de QGIS se rechazaba** («Publisher inesperado»): el
  manifiesto esperaba la firma de «QGIS» y el MSI lo firma la OSGeo Foundation.
- **La instalación de QGIS sin administrador podía abortar con `WinError 740`**
  («requiere elevación»): Windows trataba `osgeo4w-setup.exe` como instalador
  que necesita elevar. Ahora se lanza con `RunAsInvoker`.
- **El plugin quedaba sin habilitar en equipos donde QGIS nunca se había
  abierto** (no existía `QGIS3.ini`). Ahora se crea el perfil con el plugin
  habilitado.
- **`QGIS3.ini` se reescribía entero con `configparser`**, que no entiende el
  formato INI de Qt y podía alterar otras claves. Ahora se edita una sola línea y
  el resto queda byte a byte, con respaldo.
- **Un `claude_desktop_config.json` guardado con BOM** (Bloc de notas,
  PowerShell) se trataba como inválido y se reemplazaba, perdiendo los demás
  servidores MCP. Ahora se lee correctamente.
- **Una descarga dañada quedaba en caché** y todos los reintentos fallaban con el
  mismo archivo. Ahora lo que no pasa la verificación se borra, y las descargas
  de ramas y de «latest» no se cachean.
- **El asistente se cancelaba al pulsar Enter** en «¿Continuar?» (el valor por
  defecto era No) y **la ventana del `.exe` se cerraba al terminar** sin dejar
  leer el resultado.
- El plugin iba al perfil `default` aunque el perfil activo fuera otro, y a
  `QGIS4` si existía esa carpeta aunque se usara QGIS 3. Ahora usa el perfil
  activo y cubre cada versión mayor presente.
- En la consola clásica de Windows los colores salían como `←[32m`.
- La verificación de firma fallaba si la ruta tenía un apóstrofo, y podía fallar
  al lanzar el instalador desde PowerShell 7.
- `--steps 9` terminaba en una excepción en vez de un mensaje claro.

### Nuevo

- **Paso 7 — Verificación:** arranca el servidor MCP como lo hará Claude Desktop
  (PATH mínimo, directorio neutro) y comprueba que responde y lista sus
  herramientas. Sin eso no hay «instalación completa».
- **`instalar.cmd`:** arranque sin Python y sin el `.exe`, solo con herramientas
  que trae Windows. Para equipos donde no se puede abrir el `.exe` sin firma.
- La configuración de Claude se escribe también en la copia virtualizada del
  paquete MSIX cuando existe.
- `--autostart`: el servidor del plugin arranca solo al abrir QGIS (opcional).
- `--uninstall`, `--force-install`, `--version`, rangos en `--steps` (`3-7`),
  `--profile auto`.
- Reintentos de descarga (3), comprobación de espacio libre antes de instalar
  QGIS, aviso si QGIS o Claude Desktop están abiertos.
- El log incluye la salida de los programas ejecutados y los datos del entorno.
- Pruebas unitarias (`tests/`) y CI en Windows limpio.
- QGIS 3.44.15 (antes 3.44.12).

### Cambios que conviene conocer

- La carpeta `venv\` de versiones anteriores ya no se usa; puede borrarse.
- El código de salida `2` significa «completado, pero queda algo por hacer a
  mano».

## 1.0.0, 1.1.0 y 1.2.0 — 2026-07-15

Primeras versiones públicas. No se llevó registro de cambios entre ellas.
