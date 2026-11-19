# Pruebas

Este documento tiene tres partes: **cómo probar el instalador en un equipo nuevo**
(lo que hay que hacer), **qué se probó en la versión 2.1.0** (la vigente) y, como
historial, **qué se probó en la 2.0.0**.

## Parte 1 — Probarlo en un equipo nuevo

Tiempo: 20 a 30 minutos, casi todo de espera mientras se instala QGIS.

### Antes de empezar, anota

| Dato | Cómo verlo |
|---|---|
| Versión de Windows | `winver` |
| ¿La cuenta es administradora? | Configuración → Cuentas → Tu información |
| ¿Smart App Control activo? | Seguridad de Windows → Control de aplicaciones y navegador → Smart App Control |
| ¿Hay antivirus de terceros? | Seguridad de Windows → Protección antivirus |
| ¿Ya tiene QGIS / Claude Desktop / Python? | Menú Inicio |
| ¿El nombre de usuario tiene tildes o espacios? | `echo %USERPROFILE%` |

Estos seis datos explican casi cualquier diferencia entre un equipo y otro.

### Pasos

1. **Plan en seco** (no instala nada). Abre una consola en la carpeta del
   instalador:

   ```
   qgis-mcp-installer.exe --dry-run
   ```

   Si Windows no deja abrir el `.exe`, anótalo y usa `instalar.cmd --dry-run`.
   Revisa que las rutas que muestra sean las esperadas.

2. **Instalación real.** Doble clic en `qgis-mcp-installer.exe` (o en
   `instalar.cmd`). Enter en cada pregunta para aceptar el valor por defecto.

3. **Lee el RESUMEN.** Lo esperado:

   | Marca | Significado |
   |---|---|
   | `[✓]` en los 7 pasos + «Instalación completa y verificada» | Todo listo |
   | `[!]` en el paso 1 | Claude Desktop hay que instalarlo a mano: no hubo internet para `downloads.claude.ai`, o el instalador oficial no dejó la aplicación. Instálalo desde <https://claude.com/download>; no hace falta repetir el instalador. (Desde la 2.1.0 ya **no** depende de ser administrador) |
   | `[✗]` en cualquier paso | Falló. Guarda el log (ruta al final de la pantalla) |

4. **Prueba de uso** (la única que no puede automatizarse):

   1. Abre QGIS → Complementos → QGIS MCP → **Start Server**. La primera vez el
      plugin muestra una ventana «Welcome to QGIS MCP»: ciérrala.
   2. Cierra Claude Desktop por completo (bandeja → Salir) y ábrelo.
   3. En Claude, escribe: «haz ping a QGIS». Debe responder que QGIS contestó.
   4. Pide algo real: «¿qué capas hay en el proyecto de QGIS?».

5. **Si algo falla**, guarda y envía:
   - el archivo de `C:\Users\<usuario>\qgis-mcp\logs\` de esa ejecución,
   - los seis datos de la tabla inicial,
   - una captura del RESUMEN.

### Comprobaciones rápidas después

```
qgis-mcp-installer.exe --steps 7          :: vuelve a verificar; debe dar 0
qgis-mcp-installer.exe --steps 3-7        :: repetir no debe romper nada
qgis-mcp-installer.exe --uninstall        :: quita plugin y entrada de Claude
```

## Parte 2 — Qué se probó en la versión 2.1.0

Equipo de prueba (2026-11-18): el mismo de la 2.0.0 — Windows 11 Pro 10.0.26200,
cuenta **sin administrador**, **Smart App Control activado**, Python 3.12 del
usuario. Claude Desktop no estaba instalado (se quitó a propósito). Estas pruebas
**no** redirigieron `%APPDATA%` ni `%LOCALAPPDATA%`: corrieron sobre el perfil
real, salvo donde se indica. Todo lo de abajo se ejecutó el 2026-11-18.

### Causa de cada problema (con evidencia)

**Claude Desktop.** El registro `Microsoft-Windows-AppXDeploymentServer/Operational`
guarda el fallo de la 2.0.0 (17:33): `AppX Deployment operation failed for package
Claude_5.11492.5.0_x64__pzs8sxrjxfjjc with error 0x80073D28 … Administrator
privileges required to install packaged service`, más el evento 605 «Failure in
the Approved state handler». No hay políticas de Appx que lo expliquen (solo
`MdmHosts` en `HKLM\SOFTWARE\Policies\Microsoft\Windows\Appx`); la firma del MSIX
era válida. Es un requisito del propio paquete (declara un servicio). Hay otra
vía oficial: `downloads.claude.ai` publica, con el mismo nombre y hash, el
`Setup.exe` (Squirrel.Windows, `OriginalFilename: Setup.exe`, firma `Anthropic,
PBC` válida) que instala por usuario. Además, el redirect «msix/latest» iba
**detrás**: servía 5.11492.5 (publicada el 2026-11-13) mientras el canal
`RELEASES` ya listaba `AnthropicClaude-6.6395.1-full.nupkg` (publicado el
2026-11-18 18:45 UTC). `winget show Anthropic.Claude` marca 4.29.0 (2026-10-27):
también atrasado, por eso no se usa.

**QGIS.** El 2026-11-18, `setup.ini` de OSGeo4W: `qgis-ltr` 3.44.15-1 (y `qgis`
a secas 4.2.3-1); índice de `download.qgis.org/downloads/`: el MSI 3.44 más
nuevo es 3.44.15-2 (`3.44.15-3`, `3.44.16-*` y `3.44.17-1` responden 403). O sea:
la versión fijada **era correcta hoy**; el defecto era de garantía (nada la
resolvía ni la comprobaba, y un QGIS 4.x existente se daba por instalado). Esa
parte no se pudo reproducir como fallo en vivo porque el repositorio hoy sirve
3.44.15; la lógica nueva se probó con pruebas unitarias y simulaciones (abajo).

### Las cinco pruebas

| # | Prueba | Resultado | Evidencia |
|---|---|---|---|
| 1 | 53 pruebas unitarias (20 nuevas) + plan en seco es/pt, forzando «nada instalado», con `--qgis-install user` y `msi` | **Pasa** | `python -m unittest discover -s tests` → `Ran 53 tests … OK`. Planes: código 0, 4 combinaciones (es/pt × user/msi), no se creó ningún archivo (`C:\Users\Lucho\qmi_dry` no existe). El plan MSI resuelve `QGIS-OSGeo4W-3.44.15-2.msi` |
| 2 | **Paso 1 real** con el código fuente, Claude Desktop sin instalar (quedaba una carpeta residual `app-6.6395.1` sin `claude.exe` de una desinstalación previa, que se ignoró correctamente) | **Pasa**, código 0 | Descarga `…/5.11492.5/Claude-1403e2cf….exe` (254.9 MB), firma válida `CN="Anthropic, PBC"`, instala sin administrador, `Update.exe --update` al canal oficial, `claude.exe` **6.6395.1** firmado (`Valid`), clave `HKCU\…\Uninstall\AnthropicClaude` y acceso `Anthropic\Claude.lnk`. El canal `RELEASES` dice `AnthropicClaude-6.6395.1-full.nupkg` ⇒ es la última publicada (consultado el mismo día) |
| 3 | **Paso 2 real**, raíz limpia `C:\Users\Lucho\qmi_t3` (OSGeo4W, sin administrador) | **Pasa**, código 0 | Log: «El repositorio OSGeo4W sirve qgis-ltr 3.44.15-1» → «Versión comprobada en el binario: QGIS 3.44.15 (serie 3.44 LTR)». Verificación independiente: `bin\qgis_process-qgis-ltr.bat --version` → `QGIS 3.44.15-Solothurn 'Solothurn' (44b4ef05178)`; `installed.db`: `qgis-ltr qgis-ltr-3.44.15-1`. Tardó ~7 min |
| 4 | **Instalación completa pasos 1–7** con el `.exe` construido (`python build_exe.py --clean`, 8.1 MB, `qgis-mcp-installer 2.1.0`), Claude quitado antes con `Update.exe --uninstall`, defaults sobre el perfil real; luego **segunda corrida** | **Pasa**: 1.ª corrida código 0, 2.ª corrida código 0 | 1.ª: paso 1 instala Claude 6.6395.1 (mismas líneas de la prueba 2), paso 2 «Detectado QGIS v3.44.15 … es el último parche publicado de la serie 3.44 LTR», paso 7 «Claude Desktop 6.6395.1 … Es la última versión estable publicada» y «El servidor MCP responde: Qgis_mcp 1.30.0, 102 herramientas». 2.ª: pasos 1 y 2 «ya presente», paso 6 «ya estaba al día; no se tocó» |
| 5 | **`instalar.cmd`** de punta a punta **sin Python en el PATH** (Claude quitado antes) + `--uninstall` + verificación negativa | **Pasa** | Instalación: código 0 (paso 1 instaló Claude 6.6395.1 de nuevo, 7 pasos ✓). `--uninstall`: código 0, plugin borrado, `mcpServers` quedó vacío. `--steps 7`: **código 1** («Falta el plugin…», «Falta la entrada 'qgis'») como debe |

Además, en el equipo real:

- **Claude Desktop real lee la configuración.** Con la configuración de la
  prueba 4, se abrió `AnthropicClaude\claude.exe` (6.6395.1): lanzó
  `python.exe -I C:\Users\Lucho\qgis-mcp\env\run_server.py` (proceso hijo de
  `claude.exe`) y escribió `%LOCALAPPDATA%\Claude\logs\mcp-server-qgis.log` con
  `ListToolsRequest` atendido por el servidor. La configuración efectiva es
  `%APPDATA%\Claude\claude_desktop_config.json` (entrada `qgis`); no hay copia
  virtualizada `Packages\Claude_*` porque no es MSIX. Después se cerró la app.
- **Una instalación que no es la última se actualiza** (simulado en las pruebas
  unitarias; en vivo solo el caso «instalar y subir de 5.11492.5 a 6.6395.1»,
  que es lo que hicieron las pruebas 2, 4 y 5).
- **Estado final**: ver el informe de la entrega; se repitió el `.exe` completo
  al final (código 0) porque la prueba 5 desinstaló plugin y entrada MCP.

### Simulado (pruebas unitarias, no en vivo)

- `qgis-ltr` que pasa a otra serie (3.48): el instalador **no instala**.
- Solo hay QGIS 4.2.3: no cuenta como 3.44, el paso 2 instala la 3.44 aparte y
  el paso 7 falla si no hay 3.44.
- 3.44.15 y 4.2.3 a la vez: gana la 3.44.15.
- Parche viejo (3.44.12) en la instalación propia: se actualiza; en una ajena:
  solo avisa.
- Actualización de Claude que «termina» pero no deja la versión nueva: queda
  instalado, advertencia, código 2.
- Redirect hacia otro host, `http` o sin `.msix`: se rechaza.

### Lo que NO se probó (y por qué)

- **Un parche 3.44 más nuevo que 3.44.15.** Hoy no existe: no hay forma de
  ejercitar «subir de parche» en vivo. Solo unitaria.
- **El MSI con administrador** (`--qgis-install msi`): el equipo no tiene
  administrador. Se probó su resolución (plan en seco → `3.44.15-2`) y la lógica,
  no `msiexec`. Su firma se verificó en la 2.0.0.
- **QGIS 4.x instalado de verdad** junto a la 3.44: solo simulado.
- **Qué pasa cuando Anthropic cambie la forma de publicar** (nombre del
  `Setup.exe`, formato de `RELEASES`): el instalador cae a la guía manual con
  código 2, pero esa rama solo se ejerció simulando que no se resuelve la URL.
- **Que la «última estable» del canal `RELEASES` no sea una versión en
  despliegue gradual.** Es **inferencia**: el archivo lista una sola versión
  `full` y es el mismo que usa la aplicación para actualizarse; no hay otro
  canal publicado que distinga «estable» de «beta».
- **Claude Desktop con administrador / MSIX preexistente que haya que
  actualizar:** solo avisa (no puede actualizarlo sin administrador).
- Windows 10, Windows en portugués, proxy corporativo, antivirus de terceros,
  `Setup.exe` de Claude bajo otras políticas de Smart App Control (en este equipo
  corrió sin problema; la decisión es del servicio en la nube de Microsoft).

## Parte 3 — Qué se probó en la versión 2.0.0 (historial)

Lo que sigue es el estado de la 2.0.0; **el paso 1 y los pendientes de Claude
Desktop descritos aquí quedaron superados por la 2.1.0** (arriba).

Equipo de prueba (2026-11-18): Windows 11 Pro 10.0.26200, cuenta **sin
administrador**, **Smart App Control activado**, sin QGIS instalado, Python 3.12
del usuario presente. Las pruebas 2 a 5 redirigieron `%APPDATA%` y
`%LOCALAPPDATA%` a carpetas temporales para no tocar el perfil real.

### Línea base (versión 1.2.0, antes de los cambios)

Pasos 3 a 6 terminaron con «Instalación completa». Al lanzar el servidor MCP con
la configuración que dejó, tal como lo hace Claude Desktop:

```
ModuleNotFoundError: No module named 'mcp'
```

Es decir: el instalador reportaba éxito y el servidor no arrancaba.

### Las cinco pruebas

| # | Prueba | Qué cubre | Resultado |
|---|---|---|---|
| 1 | Plan en seco, español y portugués, forzando «nada instalado» | Los 7 pasos, ambas vías de QGIS, i18n; no crea ni un archivo | Pasa |
| 2 | Pasos 3–7 reales desde el código fuente, raíz con espacios y tildes (`…\p2 José Pérez\raíz qgis`) | uv + Python propio, servidor, perfil nuevo de QGIS, config de Claude, verificación | Pasa — 102 herramientas |
| 3 | Pasos 2–7 reales **instalando QGIS sin administrador** (OSGeo4W), y luego QGIS abierto con ese perfil | Paso 2 completo; el plugin carga en QGIS 3.44.15; `ping` de punta a punta | Pasa — `{"pong": true}` |
| 4 | Pasos 3–7 con el **`.exe`**, sin Python en el PATH, sobre un equipo «usado»: config de Claude con BOM y otro servidor, perfil activo distinto de `default`, `QGIS3.ini` existente, QGIS3 y QGIS4 a la vez, copia MSIX virtualizada | Empaquetado; que no se pierda nada de lo que ya había | Pasa — el INI cambió en una sola línea; se conservaron el otro servidor y las preferencias |
| 5 | Pasos 3–7 con **`instalar.cmd`**, sin Python en el PATH, usuario con tilde | Arranque sin Python ni `.exe`; reutiliza uv y Python en la segunda fase | Pasa |

Además:

- **Paso 1 real** en el mismo equipo, sin Claude Desktop: el MSIX oficial se
  descargó y su firma (`Anthropic, PBC`) se verificó; `Add-AppxPackage` falló con
  `0x80073D28` (exige administrador), que es lo que documenta Anthropic. El
  instalador siguió con la guía manual y terminó con código 2.
- **Regresión final con el `.exe`**: instalación (código 2 por Claude
  pendiente), segunda corrida idéntica (código 0, sin cambios), `--uninstall`, y
  verificación posterior que **falla** como debe (código 1).
- **Instalación completa desde cero, sin aislar nada**: el `.exe` con los valores
  por defecto sobre el equipo real (sin Claude Desktop, sin QGIS, sin
  administrador). Pasos 2 a 7 correctos en 12 minutos — QGIS 3.44.15 en
  `%USERPROFILE%\qgis-mcp\qgis`, plugin en el perfil activo (`workshop`),
  servidor verificado — y paso 1 pendiente de instalación manual (código 2).
- **`--autostart`** con QGIS real: el puerto 9876 abrió sin tocar nada y respondió
  `pong`.
- 33 pruebas unitarias (`python -m unittest discover -s tests`).

### Fallos que las pruebas encontraron y quedaron corregidos

1. El servidor MCP configurado no arrancaba (línea base).
2. Smart App Control bloqueó el `python.exe` del entorno virtual (prueba 2,
   primer intento: `WinError 4551`).
3. La instalación de QGIS sin administrador se cortó a media descarga por rutas
   de más de 260 caracteres (prueba 3, primer intento).
4. `C:\Program Files\QGIS 3.44.12` era un residuo sin ejecutable y se tomaba por
   una instalación válida.
5. El perfil activo de QGIS del equipo era `workshop`, no `default`
   (`selectionPolicy=0` + `lastProfile`).
6. El propio `qgis-mcp-installer.exe` se detectaba como «QGIS abierto».
7. La edición del INI partía valores que contenían retornos de carro sueltos.

Y dos más que salieron de los logs de una instalación real con la versión
anterior (2026-08-31, mismo equipo):

8. El MSI oficial de QGIS se rechazaba por «Publisher inesperado»: lo firma la
   OSGeo Foundation y se esperaba «QGIS». Corregido y comprobado descargando el
   MSI 3.44.15-2 (553.6 MB) y verificando su firma.
9. `osgeo4w-setup.exe` abortaba con `WinError 740` (requiere elevación). Se
   lanza ahora con `RunAsInvoker`. No se logró reproducir el 740 el 2026-11-18,
   así que la corrección es preventiva.

### Lo que NO se probó (y por qué)

- **Instalar Claude Desktop con administrador** (`Add-AppxProvisionedPackage`).
  El equipo de prueba no tiene administrador. El código sigue los comandos de la
  documentación oficial, pero esa rama no se ejecutó nunca.
- **QGIS por MSI con administrador.** Misma razón. El MSI 3.44.15-2 se descargó
  y su firma se verificó, pero no se ejecutó.
- **Claude Desktop real leyendo la configuración.** Se verificó que el servidor
  responde al protocolo MCP lanzado igual que lo lanza Claude, no la aplicación
  en sí: en el equipo de prueba no quedó instalada.
- **La copia virtualizada del MSIX en un equipo real.** Se probó que se escribe
  cuando la carpeta existe (prueba 4, simulada). No se confirmó en un equipo
  donde Claude Desktop lea de ahí.
- **Windows 10, Windows en portugués, proxy corporativo, antivirus de terceros.**
- **QGIS 4.** Solo se probó que el plugin se despliega en `QGIS4\profiles`.
- **El `.exe` bajo Smart App Control en otros equipos.** En el equipo de prueba
  arrancó, pero esa decisión la toma el servicio en la nube de Microsoft por
  archivo y puede variar; por eso existe `instalar.cmd`.

La prueba en un equipo nuevo (Parte 1) existe para cubrir justo estos huecos.
