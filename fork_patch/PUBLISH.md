# Cómo publicar el fork mejorado (paso 4 del ETL)

El paso 4 del instalador descarga el plugin desde **tu** repositorio de GitHub.
Este es el procedimiento para crear ese fork correctamente, con la atribución
legal en regla.

## 1. Crea el fork a partir del upstream 0.5.0

Parte del upstream avanzado, no del fork antiguo `qgis_mcp_lefcgis`:

```bash
# Opción A: fork con la UI de GitHub (recomendado, conserva el historial)
#   Ve a https://github.com/nkarasiak/qgis-mcp  ->  botón "Fork"

# Opción B: clon + repo nuevo
git clone https://github.com/nkarasiak/qgis-mcp.git
cd qgis-mcp
git remote set-url origin https://github.com/<TU_USUARIO>/qgis-mcp.git
```

## 2. Aplica las mejoras de este proyecto

1. **Arregla la inconsistencia de licencia** (ver `UPSTREAM_REVIEW.md`, hallazgo 1):
   reemplaza el `LICENSE` raíz (que está en GPL v2) por el `LICENSE` MIT unificado
   de este directorio, que preserva el copyright de Nicolas Karasiak y añade tu
   atribución por las mejoras.

   ```bash
   cp fork_patch/LICENSE        qgis-mcp/LICENSE
   cp fork_patch/NOTICE         qgis-mcp/NOTICE
   ```

2. **Declara la licencia en `pyproject.toml`** (cierra la ambigüedad):

   ```toml
   [project]
   license = "MIT"
   ```

3. (Opcional) Añade tu autoría de fork en `metadata.txt` SIN borrar la original:

   ```
   author=Nicolas Karasiak; fork y mejoras por Luis Ferrer
   ```

## 3. Publica

```bash
cd qgis-mcp
git add LICENSE NOTICE pyproject.toml qgis_mcp_plugin/metadata.txt
git commit -m "Unify license to MIT; add fork attribution and NOTICE"
git push origin main
```

## 4. Apunta el ETL a tu fork

En `manifest.py`, cambia:

```python
PLUGIN_FORK_OWNER = "lefcgis"     # <- tu usuario/organización real de GitHub
PLUGIN_FORK_REPO  = "qgis-mcp"
```

O, sin recompilar, pásalo en tiempo de ejecución:

```bash
python etl_installer.py --plugin-url \
    "https://github.com/<TU_USUARIO>/qgis-mcp/archive/refs/heads/main.zip"
```

## Nota legal (importante)

- El plugin/servidor son obra de **Nicolas Karasiak** bajo **MIT**. La MIT te
  permite modificar y redistribuir, **pero exige conservar su aviso de copyright
  y la licencia**. Por eso el `LICENSE` y el `NOTICE` mantienen su nombre.
- Tú puedes atribuirte **las mejoras** (el ETL, el arreglo de licencia, la
  atribución), no la autoría original del plugin. Eso es exactamente lo que
  reflejan estos archivos.
