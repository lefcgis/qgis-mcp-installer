# QGIS MCP — Instalador ETL

> 🇪🇸 [Lee esta documentación en español](README.md) · 🇧🇷 Você está lendo a versão em português.

Instalador **transparente e auditável** que prepara do zero um computador Windows
para usar o **QGIS** com a **Claude AI** via Model Context Protocol (MCP).

Empacotável como um único `.exe` para que o usuário final não precise instalar
Python nem lidar com arquivos soltos — mas **sem ofuscação nem evasão**: o código
que vai dentro é exatamente o deste repositório, publicado e verificável.

## Integridade dos releases

Os `.exe` publicados em [GitHub Releases](https://github.com/lefcgis/qgis-mcp-installer/releases)
**ainda não possuem assinatura de código de terceiros**. Em vez disso, cada release
inclui seu **hash SHA-256**, e o binário é construído pelo GitHub Actions diretamente
a partir do código público deste repositório (sem ofuscação), de modo que qualquer
pessoa pode auditá-lo ou reproduzir a construção.

Para verificar seu download no PowerShell:

```powershell
Get-FileHash .\qgis-mcp-installer.exe -Algorithm SHA256
# compare o resultado com o SHA-256 publicado na página do release
```

> A assinatura gratuita da **SignPath Foundation** foi solicitada (jul/2026); eles
> pediram que o projeto ganhe primeiro visibilidade pública (estrelas, usuários,
> menções) e vamos reaplicar mais adiante. O workflow de assinatura já está pronto
> e será ativado assim que houver certificado. Veja `SIGNING.md`.

## O que ele faz (os 6 passos do ETL)

| Passo | Ação | Como |
|-------|------|------|
| 1 | Instala o **Claude Desktop** | Baixa o instalador oficial (win x64) e o executa em modo silencioso |
| 2 | Instala o **QGIS 3.44 LTR** | Com admin: MSI oficial via `msiexec`. **Sem admin: OSGeo4W na sua pasta de usuário (zero UAC)** |
| 3 | Instala as **dependências de Python** | Cria um **venv isolado** com bibliotecas fixadas e atualizadas |
| 4 | Obtém o **plugin QGIS MCP** | Baixa o fork aprimorado do GitHub (com fallback para o upstream) |
| 5 | Configura o **QGIS** | Copia o plugin para o perfil e o habilita no `QGIS3.ini` |
| 6 | Configura o **Claude** | Escreve o `claude_desktop_config.json` (com backup prévio) |

*Extract* = downloads · *Transform* = verificação de integridade + preparação ·
*Load* = instalação e configuração.

## Sem permissões de administrador: sem problema

**Você não precisa ser administrador do computador.** Se o QGIS não estiver
instalado, o passo 2 detecta automaticamente suas permissões:

- **Com administrador** → instala o MSI oficial do QGIS (em nível de máquina,
  em `C:\Program Files`), como sempre.
- **Sem administrador** → usa o **instalador de rede OSGeo4W oficial** (assinado
  pela OSGeo Foundation e verificado antes de ser executado) para instalar o
  mesmo QGIS LTR completo (`qgis-ltr-full`: Python, GDAL, GRASS, processing)
  dentro da **sua pasta de usuário** (`<raiz>/qgis`). Zero janelas de UAC.

Você também pode forçar o caminho com `--qgis-install msi|user|auto` (padrão
`auto`). O Claude Desktop sempre é instalado por-usuário, então **o fluxo
completo funciona de ponta a ponta sem elevação**:

```bash
# instalação completa garantida sem administrador
python etl_installer.py --qgis-install user
```

## Detecção: não reinstala o que você já tem

Antes de instalar o Claude (passo 1) e o QGIS (passo 2), o ETL **detecta** se eles
já estão no sistema, mostra a **versão** encontrada e **pergunta** se você já
possui esse software:

- **Se você já o tem** → pula essa instalação e vai direto para as dependências
  de Python, o plugin e a configuração. O artefato deixa tudo pronto sem
  reinstalar nada.
- **Se você não tem nada** → baixa e instala como previsto.

A detecção reconhece a versão maior do QGIS: implanta o plugin no perfil
**QGIS4** ou **QGIS3** conforme o que você tiver (testado com QGIS 4.0.0 e 3.44 LTR).
Se o seu QGIS for anterior ao 3.28, ele avisa (o plugin exige ≥ 3.28).

No modo não interativo ele usa a detecção automática, ou você força o resultado
com `--assume-installed`:

```bash
# "Já tenho o Claude e o QGIS; só configure o resto para mim"
python etl_installer.py --non-interactive --base-dir "D:/QGIS-Claude" \
    --assume-installed claude,qgis
```

## Uso

```bash
# Assistente interativo (o usuário escolhe as pastas)
python etl_installer.py

# Ver o plano completo SEM tocar no sistema
python etl_installer.py --non-interactive --base-dir "D:/QGIS-Claude" --dry-run

# Instalação não interativa completa
python etl_installer.py --non-interactive --base-dir "D:/QGIS-Claude"

# Apenas alguns passos (ex.: reimplantar o plugin e reconfigurar)
python etl_installer.py --steps 4,5,6

# Usar o seu próprio fork sem recompilar
python etl_installer.py --plugin-url "https://github.com/<SEU_USUARIO>/qgis-mcp/archive/refs/heads/main.zip"
```

O usuário escolhe **todas** as pastas de instalação (raiz, downloads, venv,
código do servidor). Cada execução deixa um **log com data** em `<raiz>/logs/`.

## Construir o `.exe`

```bash
python -m pip install -r requirements-build.txt
python build_exe.py --clean
# -> dist/qgis-mcp-installer.exe
```

### Assinatura de código (recomendado para distribuição pública)

Um `.exe` sem assinatura dispara avisos do SmartScreen e de antivírus. A forma
correta de gerar confiança **não é se esconder, e sim assinar**. Dois caminhos:

- **Automático via SignPath Foundation (PENDENTE de aprovação)** — o workflow
  `.github/workflows/build-and-sign.yml` já está pronto para assinar cada
  release; será ativado quando a SignPath aprovar o projeto (veja **`SIGNING.md`**).
  Enquanto isso, o workflow publica o `.exe` **sem assinatura** junto com seu SHA-256.
- **Manual** — com o seu próprio certificado, usando o `sign.ps1`:
  ```powershell
  .\sign.ps1 -PfxPath "C:\certs\meu-cert.pfx" -Password "****"
  # ou com certificado EV em token de hardware:
  .\sign.ps1 -Thumbprint "A1B2C3..."
  ```

Publique sempre o **SHA-256** do `.exe` junto com o download (tanto o `sign.ps1`
quanto o workflow o geram) para verificação independente do certificado.

## Integridade e segurança (por design)

- **Assinatura Authenticode**: os instaladores do Claude e do QGIS são verificados
  por publisher (`Anthropic`, `QGIS`) e validade da assinatura **antes** de serem
  executados. Nada roda às cegas. (`--skip-signature` existe mas avisa; não o use
  em distribuição.)
- **SHA-256 opcional**: fixe hashes no `manifest.py` para builds reproduzíveis.
- **venv isolado**: as dependências de Python NUNCA tocam o Python do sistema
  nem o do QGIS.
- **Backup**: o `claude_desktop_config.json` existente é copiado antes de
  ser modificado.
- **Tudo declarado às claras**: cada URL baixada vive no `manifest.py`.

> ⚠️ O plugin QGIS MCP expõe a ferramenta `execute_code`, que executa código
> Python/PyQGIS arbitrário na máquina. Instale-o apenas de fontes em que você
> confie e não deixe o servidor MCP ativo se não estiver usando.

## Estrutura do projeto

```
qgis_mcp_installer/
├── etl_installer.py         # o ETL (apenas biblioteca padrão do Python)
├── manifest.py              # ÚNICA fonte de URLs, versões e checksums
├── build_exe.py             # empacota o .exe com PyInstaller (sem ofuscar)
├── requirements-build.txt   # PyInstaller fixado (apenas para construir)
├── LICENSE                  # MIT: Karasiak (original) + Ferrer (melhorias)
├── UPSTREAM_REVIEW.md        # erros/melhorias encontrados em nkarasiak/qgis-mcp
└── fork_patch/              # kit para publicar o fork aprimorado (passo 4)
    ├── LICENSE  ├── NOTICE  └── PUBLISH.md
```

## Créditos e licença

- Plugin e servidor MCP: **Nicolas Karasiak** — https://github.com/nkarasiak/qgis-mcp (MIT, © 2025).
- Instalador ETL e melhorias do fork: **Luis Ferrer** (MIT, © 2026).

Distribuído sob a licença MIT, preservando a atribuição original. Veja `LICENSE`
e `fork_patch/NOTICE`.
