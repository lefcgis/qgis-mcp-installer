# Revisión de `nkarasiak/qgis-mcp` — errores y mejoras

Revisión hecha el 2026-07-05 sobre el clon de `main` de
[github.com/nkarasiak/qgis-mcp](https://github.com/nkarasiak/qgis-mcp)
(versión **0.5.0** del plugin y del servidor).

Contexto importante: el upstream de Karasiak está **mucho más avanzado** que el
fork `qgis_mcp_lefcgis` con el que veníamos trabajando. El upstream ya trae:
`src/` refactorizado (server/client/helpers/compound_tools), 100+ herramientas
MCP, tests (TDD + stress + concurrencia), benchmarks, CI de release, un
`install.py` multi-cliente, capa de compatibilidad QGIS 3/4, y framing de socket
con prefijo de longitud. Por eso **la recomendación es basar el fork mejorado en
el upstream 0.5.0**, no en el fork antiguo.

## Hallazgo confirmado (defecto real)

### 1. Inconsistencia de licencia — GPL v2 vs MIT
- **Qué**: el archivo raíz `LICENSE` contiene el texto de la **GNU GPL v2**,
  pero:
  - `qgis_mcp_plugin/LICENSE` es **MIT** (`Copyright (c) 2025 Nicolas Karasiak`).
  - `qgis_mcp_plugin/metadata.txt` declara `license=MIT`.
  - `pyproject.toml` no declara `license`.
- **Por qué importa**: GPL-2.0 y MIT son licencias con obligaciones distintas
  (la GPL es copyleft; MIT es permisiva). Tener ambas en el mismo repo crea
  ambigüedad legal sobre bajo qué términos se distribuye realmente el software,
  y confunde a quien quiera hacer un fork (como nosotros).
- **Intención aparente**: MIT (coinciden el `metadata.txt` y el `LICENSE` del
  plugin). El `LICENSE` raíz en GPL parece un remanente.
- **Corrección en nuestro fork**: unificamos a **MIT**, preservando el copyright
  original de Karasiak y añadiendo la atribución de las mejoras (ver `LICENSE`
  y `fork_patch/` de este instalador). Recomendado reportarlo como *issue* al
  upstream.

## Mejoras aportadas por este proyecto (no son bugs del upstream)

Estas son mejoras nuestras alrededor del upstream, no defectos suyos:

### 2. Falta un aprovisionamiento de máquina de extremo a extremo
- El `install.py` del upstream **despliega el plugin y configura los clientes
  MCP**, pero **no instala Claude Desktop, ni QGIS, ni Python**. Da por hecho que
  ya están en el sistema.
- **Nuestra mejora**: el ETL (`etl_installer.py`) añade esa capa que falta —
  descarga e instala Claude Desktop y QGIS 3.44 LTR con verificación de firma,
  crea un venv aislado con dependencias fijadas, y luego despliega y configura
  todo. Es el complemento natural del `install.py` upstream, no un reemplazo.

### 3. Integridad de descargas verificable
- **Mejora**: todas las descargas se verifican por **firma Authenticode**
  (publisher esperado) antes de ejecutarse, con opción de fijar SHA-256. El
  upstream no aprovisiona binarios, así que no tenía esta necesidad; nosotros sí.

## Sugerencias para el upstream (no implementadas aquí)

- **Fijar checksums de release**: publicar el SHA-256 de cada release del plugin
  facilitaría a instaladores de terceros (como este) verificar el ZIP.
- **Declarar `license` en `pyproject.toml`** para cerrar la ambigüedad del punto 1.

## Cómo reproducir la revisión

```bash
git clone --depth 1 https://github.com/nkarasiak/qgis-mcp
# Comparar las tres fuentes de licencia:
head -2 qgis-mcp/LICENSE                       # -> "GNU GENERAL PUBLIC LICENSE"
head -3 qgis-mcp/qgis_mcp_plugin/LICENSE       # -> "MIT License ... Karasiak"
grep -i "^license" qgis-mcp/qgis_mcp_plugin/metadata.txt   # -> license=MIT
```
