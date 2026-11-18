# Pruebas

Este documento tiene dos partes: **cómo probar el instalador en un equipo nuevo**
(lo que hay que hacer) y **qué se probó en la versión 2.0.0** (lo que ya consta,
y lo que no).

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
   | `[!]` en el paso 1 | Claude Desktop hay que instalarlo a mano (normal sin administrador). Instálalo desde <https://claude.com/download>; no hace falta repetir el instalador |
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

## Parte 2 — Qué se probó en la versión 2.0.0

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
