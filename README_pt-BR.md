# QGIS MCP — Instalador ETL

> 🇪🇸 [Lee esta documentación en español](README.md) · 🇧🇷 Você está lendo a versão em português.

Instalador **transparente e auditável** que deixa um computador Windows pronto
para usar o **QGIS** com a **Claude AI** via Model Context Protocol (MCP): instala
o que estiver faltando, configura e **verifica que o servidor MCP responde** antes
de dizer que terminou.

Versão atual: **2.0.0** — veja [`CHANGELOG.md`](CHANGELOG.md) (em espanhol).

## Duas formas de instalar

Você não precisa de Python nem de permissões de administrador para nenhuma delas.

### A. O `.exe` (o mais simples)

1. Baixe `qgis-mcp-installer.exe` em
   [Releases](https://github.com/lefcgis/qgis-mcp-installer/releases).
2. Clique duas vezes. Enter aceita os valores padrão.

O `.exe` **ainda não tem assinatura de código**, então o Windows pode mostrar o
aviso azul do SmartScreen («O Windows protegeu o computador» → *Mais informações*
→ *Executar assim mesmo*) ou um antivírus pode retê-lo. Se não conseguir abri-lo,
use a forma B.

### B. `instalar.cmd` (se o Windows não deixar abrir o `.exe`)

1. Na página do repositório: **Code → Download ZIP**, e **extraia o ZIP inteiro**.
2. Clique duas vezes em `instalar.cmd`.

O `instalar.cmd` executa exatamente o mesmo código, mas sem nenhum executável
próprio: baixa o `uv` com `curl.exe`, confere o SHA-256 com `certutil.exe` e
extrai com `tar.exe` (os três vêm com o Windows 10/11), instala um Python próprio
e inicia o `etl_installer.py`.

### Com Python já instalado (3.10 ou superior)

```bash
python etl_installer.py
```

## O que ele faz (6 passos + verificação)

| Passo | Ação | Como |
|-------|------|------|
| 1 | **Claude Desktop** | Detecta (versão MSIX ou clássica). Se faltar, baixa o pacote MSIX oficial, verifica a assinatura e tenta instalar; se o Windows não permitir, abre a página de download e continua com o restante |
| 2 | **QGIS 3.44 LTR** | Detecta. Se faltar — com admin: MSI oficial. **Sem admin: OSGeo4W na sua pasta de usuário (zero UAC)** |
| 3 | **Ambiente Python** | Baixa o `uv` (hash fixado) e um CPython 3.12 próprio; instala as bibliotecas em uma pasta isolada. Não usa o Python do sistema nem o do QGIS |
| 4 | **Plugin + servidor MCP** | Baixa o fork ([lefcgis/qgis-mcp](https://github.com/lefcgis/qgis-mcp), com fallback para o upstream) e instala o servidor |
| 5 | **Configura o QGIS** | Copia o plugin para o perfil ativo e o habilita (cria o perfil se o QGIS nunca foi aberto) |
| 6 | **Configura o Claude** | Adiciona a entrada `qgis` ao `claude_desktop_config.json` sem mexer no resto, com backup |
| 7 | **Verificação** | Inicia o servidor MCP **do mesmo jeito que o Claude Desktop fará** e confere que ele responde e lista as ferramentas |

Se o passo 7 não passar, o instalador **não** diz «instalação completa»: ele diz
o que falhou e onde está o log.

Ao terminar:

1. Abra o QGIS → menu **Complementos → QGIS MCP → Start Server**.
2. Feche o Claude Desktop **por completo** (ícone na bandeja do sistema → *Sair*;
   fechar a janela não basta) e abra-o de novo.
3. No Claude, peça: «faça ping no QGIS».

## Onde fica cada coisa

Tudo fica na pasta raiz que você escolher (padrão: `C:\Users\<você>\qgis-mcp`):

```
qgis-mcp\
├── tools\uv\          uv.exe (versão e hash fixados no manifest.py)
├── python\            CPython 3.12 próprio (não é o do sistema)
├── env\
│   ├── site-packages\ bibliotecas do servidor (mcp, pydantic, …)
│   └── run_server.py  lançador que o Claude Desktop executa
├── server\            cópia auditável do código do servidor (src/, pyproject.toml)
├── qgis\              QGIS LTR, somente se foi instalado sem administrador
├── downloads\         o que foi baixado
└── logs\              um log com data para cada execução
```

Fora dessa pasta só se mexe em:

- `%APPDATA%\QGIS\QGIS3\profiles\<perfil>\` — o plugin e **uma linha** do
  `QGIS3.ini` (com backup `QGIS3.ini.bak-qgismcp-<data>`).
- `%APPDATA%\Claude\claude_desktop_config.json` — a entrada `mcpServers.qgis`
  (com backup `.bak-<data>`).

A entrada gravada no Claude é:

```json
{
  "mcpServers": {
    "qgis": {
      "command": "C:\\Users\\<você>\\qgis-mcp\\python\\cpython-3.12.x-windows-x86_64-none\\python.exe",
      "args": ["-I", "C:\\Users\\<você>\\qgis-mcp\\env\\run_server.py"]
    }
  }
}
```

Caminhos absolutos: não depende do `PATH` nem do diretório de trabalho.

## Opções

```bash
# Ver o plano completo SEM tocar no sistema
python etl_installer.py --dry-run

# Instalação não interativa
python etl_installer.py --non-interactive --base-dir "C:/qgis-mcp"

# "Já tenho Claude e QGIS; só configure o restante"
python etl_installer.py --non-interactive --assume-installed claude,qgis

# Apenas alguns passos (reimplantar o plugin, reconfigurar e verificar)
python etl_installer.py --steps 4-7

# Apenas verificar uma instalação existente
python etl_installer.py --steps 7

# QGIS sem administrador mesmo sendo administrador
python etl_installer.py --qgis-install user

# Fazer o servidor do plugin iniciar sozinho ao abrir o QGIS (sem clicar em Start Server)
python etl_installer.py --autostart

# Outro perfil do QGIS (padrão: o perfil ativo)
python etl_installer.py --profile trabalho

# Outro fork do plugin
python etl_installer.py --plugin-url "https://github.com/<USUARIO>/qgis-mcp/archive/refs/heads/main.zip"

# Idioma (por padrão detecta o do Windows): es | pt
python etl_installer.py --lang pt

# Remover o plugin e a entrada do Claude (não desinstala o Claude nem o QGIS)
python etl_installer.py --uninstall
```

As mesmas opções valem para `qgis-mcp-installer.exe` e `instalar.cmd`.

**Códigos de saída:** `0` tudo certo · `1` um passo falhou · `2` concluído, mas
falta algo a fazer manualmente (o instalador diz o quê) · `130` cancelado.

## Se algo falhar

| Sintoma | Causa habitual | O que fazer |
|---|---|---|
| O Windows não deixa abrir o `.exe` | SmartScreen / antivírus / Smart App Control: o `.exe` não é assinado | Use o `instalar.cmd` |
| Passo 1: «O Windows não permitiu a instalação automática» | O MSIX do Claude exige administrador em muitos computadores | Instale em <https://claude.com/download>; a configuração já foi gravada, não é preciso repetir o instalador |
| Passo 2: «a pasta … é longa demais» | O OSGeo4W não aceita caminhos longos (limite de 260 do Windows) | Escolha uma raiz curta, ex.: `C:\qgis-mcp` |
| Passo 2: espaço insuficiente | O QGIS precisa de ~6 GB entre download e instalação | Libere espaço ou use outra unidade com `--base-dir` |
| Passos 3–4: um download falha | Proxy, antivírus ou sem internet | Tente de novo; o instalador já faz 3 tentativas por download |
| Passo 7: «o servidor MCP NÃO respondeu» | Um antivírus bloqueou o Python próprio | Adicione uma exceção para a pasta raiz e execute `--steps 3-7` |
| O Claude não mostra as ferramentas do QGIS | O Claude Desktop não foi reiniciado por completo | Bandeja do sistema → *Sair* e abrir de novo |
| O Claude mostra, mas «não conecta ao QGIS» | Falta clicar em *Start Server* no QGIS | Complementos → QGIS MCP → Start Server |
| O plugin não aparece no QGIS | Foi instalado em outro perfil | `--profile <nome>` e `--steps 5,7` |

Cada execução deixa um log completo em `<raiz>\logs\`. Se pedir ajuda, anexe esse
arquivo.

Para testá-lo passo a passo em um computador novo, veja [`TESTING.md`](TESTING.md)
(em espanhol).

## Integridade e segurança (por design)

- **Tudo declarado às claras**: cada URL baixada está no `manifest.py`.
- **Assinatura Authenticode** antes de executar: Claude (`Anthropic`), QGIS
  e OSGeo4W (`OPEN SOURCE GEOSPATIAL`). Um arquivo que não passa na
  verificação é apagado e não é executado.
- **SHA-256 fixado** para o `uv`, igual ao publicado no próprio release.
- **Isolado**: nada é instalado no Python do sistema nem no do QGIS.
- **Backup** do `claude_desktop_config.json` e do `QGIS3.ini` antes de alterá-los.
- **Sem executáveis próprios sem assinatura em tempo de execução**: o servidor MCP
  é iniciado com o `python.exe` da distribuição, não com um lançador de ambiente
  virtual (o Smart App Control os bloqueia).

> ⚠️ O plugin QGIS MCP expõe a ferramenta `execute_code`, que executa código
> Python/PyQGIS arbitrário na máquina. Instale-o apenas de fontes em que você
> confia e não deixe o servidor MCP ativo quando não estiver usando.

### Integridade dos releases

Os `.exe` em [Releases](https://github.com/lefcgis/qgis-mcp-installer/releases)
são construídos pelo GitHub Actions a partir do código público deste repositório,
sem ofuscação, e cada release publica o seu **SHA-256**:

```powershell
Get-FileHash .\qgis-mcp-installer.exe -Algorithm SHA256
# compare com o SHA256SUMS.txt do release
```

A assinatura gratuita da **SignPath Foundation** foi solicitada (jul/2026); eles
pediram que o projeto ganhe primeiro visibilidade pública. O workflow de
assinatura está pronto e será ativado quando houver certificado. Veja
[`SIGNING.md`](SIGNING.md).

## Desenvolvimento

```bash
# Testes unitários (apenas biblioteca padrão)
python -m unittest discover -s tests -v

# Construir o .exe
python -m pip install -r requirements-build.txt
python build_exe.py --clean        # -> dist/qgis-mcp-installer.exe
```

## Créditos e licença

- Plugin e servidor MCP: **Nicolas Karasiak** — https://github.com/nkarasiak/qgis-mcp (MIT, © 2025).
- Instalador ETL e melhorias do fork: **Luis Ferrer** (MIT, © 2026).

Distribuído sob licença MIT, preservando a atribuição original. Veja `LICENSE`
e `fork_patch/NOTICE`.
