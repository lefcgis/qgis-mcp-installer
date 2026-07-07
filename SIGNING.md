# Firma del instalador con SignPath Foundation (gratis para OSS)

El workflow `.github/workflows/build-and-sign.yml` construye el `.exe` y lo firma
automáticamente con **SignPath Foundation**, el programa gratuito de SignPath para
proyectos de código abierto. Esta guía cubre el alta (se hace **una vez**).

## Requisitos previos

- El instalador vive en un **repositorio público de GitHub** (ej. `lefcgis/qgis-mcp-installer`).
- Licencia OSS aprobada — **MIT** en nuestro caso ✓ (ver `LICENSE`).
- El código es auditable y **no ofuscado** ✓ (requisito de SignPath).

## Paso 1 — Alta en SignPath Foundation

1. Ve a **https://signpath.org/** → *Apply for the Foundation program*.
2. Regístrate con tu cuenta de GitHub y **conecta el repositorio** del instalador.
3. SignPath revisa que el proyecto sea OSS elegible (suele tardar unos días).

## Paso 2 — Crear el proyecto y la política de firma

En el panel de SignPath, dentro de tu organización:

1. Crea un **Project** con slug exactamente **`qgis-mcp-installer`**
   (debe coincidir con `project-slug` del workflow).
2. Crea un **Signing Policy** con slug **`release-signing`**
   (debe coincidir con `signing-policy-slug` del workflow).
3. Configura el **Artifact Configuration** para un binario Windows PE (`.exe`).
4. Conecta el **Trusted Build System** = GitHub Actions de tu repo.

## Paso 3 — Secretos y variables en GitHub

En el repo → *Settings* → *Secrets and variables* → *Actions*:

| Tipo | Nombre | Valor |
|---|---|---|
| **Secret** | `SIGNPATH_API_TOKEN` | Token de API que genera SignPath para tu usuario/CI |
| **Variable** | `SIGNPATH_ORGANIZATION_ID` | El *Organization ID* (GUID) de tu panel de SignPath |

> El `project-slug` y `signing-policy-slug` van fijos en el YAML; solo el token y
> el organization-id son secretos/variables.

## Paso 4 — Lanzar un release firmado

```bash
git tag v1.0.0
git push origin v1.0.0
```

El workflow:
1. Construye `qgis-mcp-installer.exe` en `windows-latest`.
2. Lo sube como artefacto y lo envía a SignPath.
3. SignPath lo firma con el certificado de la Foundation y lo devuelve.
4. Se **adjunta el `.exe` firmado al GitHub Release** y se publica su **SHA-256**
   en el resumen del job.

También puedes dispararlo a mano desde *Actions* → *build-and-sign* → *Run workflow*.

## Qué esperar (expectativas realistas)

- La firma será **válida** (`Status=Valid`, sin "editor desconocido").
- **SmartScreen NO desaparece el primer día**: la reputación se gana con
  descargas y tiempo. Esto le pasa a todo lo que no sea EV; es normal.
- Publica siempre el **SHA-256** junto a la descarga para verificación de
  integridad independiente del certificado.

## Notas

- `sign.ps1` (firma local con tu propio cert) sigue disponible como alternativa
  manual; SignPath es la vía **automática y gratuita** para OSS y la recomendada
  para releases públicos.
- Si SignPath cambia los nombres de sus inputs de la action, ajusta el `with:`
  del workflow según su documentación vigente.
