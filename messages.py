"""
messages.py — Catálogo de mensajes del instalador (español y portugués de Brasil).

Clave -> {es, pt}. Los marcadores {así} se rellenan con str.format. TODO texto
que ve la persona sale de aquí; `tests/test_installer.py` comprueba que cada
clave tenga los dos idiomas y los mismos marcadores.
"""

from __future__ import annotations

MSG: dict[str, dict[str, str]] = {
    # ── genéricos ────────────────────────────────────────────────────────
    "ui.step_prefix": {"es": "[Paso {n}] {title}", "pt": "[Passo {n}] {title}"},
    "log.session": {"es": "Sesión iniciada {ts}", "pt": "Sessão iniciada {ts}"},
    "run.fail": {"es": "No se pudo ejecutar {exe}: {exc}",
                 "pt": "Não foi possível executar {exe}: {exc}"},
    "run.progress": {"es": "… trabajando ({n} líneas en el log)",
                     "pt": "… trabalhando ({n} linhas no log)"},
    # ── descarga / verificación ──────────────────────────────────────────
    "dl.dry": {"es": "[dry-run] descargaría {url} -> {dest}",
               "pt": "[dry-run] baixaria {url} -> {dest}"},
    "dl.cached": {"es": "Ya descargado: {name} ({size})",
                  "pt": "Já baixado: {name} ({size})"},
    "dl.downloading": {"es": "Descargando {name}", "pt": "Baixando {name}"},
    "dl.from": {"es": "  desde: {url}", "pt": "  de: {url}"},
    "dl.done": {"es": "Descargado {name} ({size})", "pt": "Baixado {name} ({size})"},
    "dl.retry": {"es": "Intento {n} fallido ({exc}). Reintentando…",
                 "pt": "Tentativa {n} falhou ({exc}). Tentando novamente…"},
    "dl.fail": {"es": "No se pudo descargar {name}: {exc}. Revisa tu conexión a "
                      "internet o el proxy/antivirus de tu red.",
                "pt": "Não foi possível baixar {name}: {exc}. Verifique sua conexão "
                      "com a internet ou o proxy/antivírus da sua rede."},
    "sha.ok": {"es": "SHA-256 verificado: {h}…", "pt": "SHA-256 verificado: {h}…"},
    "sha.bad": {"es": "SHA-256 NO coincide. esperado={e}… actual={a}…",
                "pt": "SHA-256 NÃO confere. esperado={e}… atual={a}…"},
    "sig.skipped": {"es": "Verificación de firma OMITIDA por el usuario (--skip-signature).",
                    "pt": "Verificação de assinatura IGNORADA pelo usuário (--skip-signature)."},
    "sig.notwin": {"es": "No es Windows: se omite la verificación Authenticode.",
                   "pt": "Não é Windows: a verificação Authenticode será ignorada."},
    "sig.execfail": {"es": "No se pudo ejecutar la verificación de firma: {exc}",
                     "pt": "Não foi possível executar a verificação de assinatura: {exc}"},
    "sig.invalid": {"es": "Firma inválida o ausente (Status={status}).",
                    "pt": "Assinatura inválida ou ausente (Status={status})."},
    "sig.publisher": {"es": "Publisher inesperado. esperado ~'{exp}', firma='{subj}'",
                      "pt": "Publisher inesperado. esperado ~'{exp}', assinatura='{subj}'"},
    "sig.ok": {"es": "Firma válida. Publisher: {subj}",
               "pt": "Assinatura válida. Publisher: {subj}"},
    "fetch.discarded": {"es": "{name} no pasó la verificación y se eliminó de las descargas.",
                        "pt": "{name} não passou na verificação e foi removido dos downloads."},
    "fetch.size": {"es": "Tamaño inesperado ({size}); continúo, pero revísalo.",
                   "pt": "Tamanho inesperado ({size}); continuo, mas verifique."},
    # ── detección / confirmación ─────────────────────────────────────────
    "det.found": {"es": "Detectado {name}{detail}{loc}",
                  "pt": "Detectado: {name}{detail}{loc}"},
    "det.ver_unknown": {"es": " (versión no detectada)", "pt": " (versão não detectada)"},
    "det.notfound": {"es": "No detecté {name} en este equipo.",
                     "pt": "Não detectei {name} neste computador."},
    "det.assume": {"es": "--assume-installed: se asume {name} ya presente.",
                   "pt": "--assume-installed: assume-se que {name} já está presente."},
    "det.force": {"es": "--force-install: se instalará {name} aunque ya exista.",
                  "pt": "--force-install: {name} será instalado mesmo que já exista."},
    "det.ask_have": {"es": "  ¿Ya tienes {name} instalado? [{d}]: ",
                     "pt": "  Você já tem o {name} instalado? [{d}]: "},
    "det.ask_ver": {"es": "  ¿Qué versión de {name} tienes? [{d}]: ",
                    "pt": "  Qual versão do {name} você tem? [{d}]: "},
    "det.dontknow": {"es": "no sé", "pt": "não sei"},
    # ── uv ───────────────────────────────────────────────────────────────
    "uv.present": {"es": "uv {v} ya está en la carpeta de herramientas.",
                   "pt": "uv {v} já está na pasta de ferramentas."},
    "uv.ready": {"es": "uv listo en {path}", "pt": "uv pronto em {path}"},
    "uv.fail": {"es": "El ZIP de uv no contenía uv.exe.",
                "pt": "O ZIP do uv não continha uv.exe."},
    "uv.notwin": {"es": "La descarga automática de uv solo está prevista para Windows.",
                  "pt": "O download automático do uv só está previsto para Windows."},
    # ── estados (aparecen en el RESUMEN) ─────────────────────────────────
    "st.present": {"es": "ya presente{v}", "pt": "já presente{v}"},
    "st.installed_manual": {"es": "instalado a mano", "pt": "instalado manualmente"},
    "st.manual_pending": {"es": "PENDIENTE: instálalo a mano",
                          "pt": "PENDENTE: instale manualmente"},
    "st.venv": {"es": "uv + Python {py} propio", "pt": "uv + Python {py} próprio"},
    "st.configs": {"es": "{n} archivo(s) de configuración",
                   "pt": "{n} arquivo(s) de configuração"},
    "st.verified": {"es": "el servidor MCP responde", "pt": "o servidor MCP responde"},
    "st.verify_failed": {"es": "hay comprobaciones fallidas",
                         "pt": "há verificações com falha"},
    # ── paso 1 ───────────────────────────────────────────────────────────
    "s1.title": {"es": "Claude Desktop", "pt": "Claude Desktop"},
    "s1.existing_ok": {"es": "Usas tu Claude Desktop existente{v}. Se omite la "
                             "instalación; se configurará en el paso 6.",
                       "pt": "Usando o seu Claude Desktop existente{v}. A instalação "
                             "será pulada; ele será configurado no passo 6."},
    "s1.manual": {"es": "Instala Claude Desktop a mano desde {url} (es un instalador "
                        "normal: siguiente, siguiente). El resto de pasos continúa.",
                  "pt": "Instale o Claude Desktop manualmente em {url} (é um instalador "
                        "comum: avançar, avançar). Os demais passos continuam."},
    "s1.manual_wait": {"es": "  Abrí la página de descarga. Cuando termines de instalarlo, "
                             "pulsa Enter (o Enter ahora para dejarlo para después): ",
                       "pt": "  Abri a página de download. Quando terminar de instalar, "
                             "pressione Enter (ou Enter agora para deixar para depois): "},
    "w.claude": {"es": "Falta instalar Claude Desktop: {url}. Cuando lo instales no hace "
                       "falta volver a ejecutar este instalador.",
                 "pt": "Falta instalar o Claude Desktop: {url}. Depois de instalá-lo não é "
                       "preciso executar este instalador de novo."},
    # ── paso 2 ───────────────────────────────────────────────────────────
    "s2.title": {"es": "QGIS {v} LTR", "pt": "QGIS {v} LTR"},
    "s2.existing_ok": {"es": "Usas tu QGIS existente{v}. Se omite la instalación; "
                             "el plugin se desplegará en tu perfil.",
                       "pt": "Usando o seu QGIS existente{v}. A instalação será "
                             "pulada; o plugin será implantado no seu perfil."},
    "s2.mode_msi": {"es": "Tienes permisos de administrador → instalación estándar (MSI).",
                    "pt": "Você tem permissões de administrador → instalação padrão (MSI)."},
    "s2.mode_user": {"es": "Sin permisos de administrador → QGIS se instalará en tu "
                           "carpeta de usuario (OSGeo4W, no requiere elevación).",
                     "pt": "Sem permissões de administrador → o QGIS será instalado na "
                           "sua pasta de usuário (OSGeo4W, não requer elevação)."},
    "s2.nospace": {"es": "Espacio insuficiente en {where}: hay {free} libres y QGIS "
                         "necesita unos {need}. Libera espacio o elige otra carpeta raíz.",
                   "pt": "Espaço insuficiente em {where}: há {free} livres e o QGIS "
                         "precisa de cerca de {need}. Libere espaço ou escolha outra pasta raiz."},
    "msi.dry": {"es": "[dry-run] ejecutaría msiexec para instalar QGIS.",
                "pt": "[dry-run] executaria o msiexec para instalar o QGIS."},
    "msi.installing": {"es": "Instalando QGIS con msiexec (barra de progreso básica)…",
                       "pt": "Instalando o QGIS com msiexec (barra de progresso básica)…"},
    "msi.ok": {"es": "QGIS instalado.", "pt": "QGIS instalado."},
    "msi.err": {"es": "msiexec devolvió código {rc}. Detalle en {log}",
                "pt": "msiexec retornou o código {rc}. Detalhes em {log}"},
    "msi.perm_hint": {"es": "Ese código suele indicar falta de permisos de administrador. "
                            "Reintenta con --qgis-install user para instalar QGIS en tu "
                            "carpeta de usuario SIN administrador.",
                      "pt": "Esse código costuma indicar falta de permissões de administrador. "
                            "Tente novamente com --qgis-install user para instalar o QGIS na "
                            "sua pasta de usuário SEM administrador."},
    "o4w.dry": {"es": "[dry-run] instalaría QGIS sin admin en {root} con:",
                "pt": "[dry-run] instalaria o QGIS sem admin em {root} com:"},
    "o4w.installing": {"es": "Instalando QGIS LTR en {root} (sin administrador)…",
                       "pt": "Instalando o QGIS LTR em {root} (sem administrador)…"},
    "o4w.big": {"es": "Descarga ~0.7 GB del repositorio oficial de OSGeo e instala ~2.5 GB. "
                      "Suele tardar entre 10 y 20 minutos; el detalle va al log.",
                "pt": "Baixa ~0,7 GB do repositório oficial da OSGeo e instala ~2,5 GB. "
                      "Costuma levar de 10 a 20 minutos; os detalhes vão para o log."},
    "o4w.ok": {"es": "QGIS LTR instalado en {root} (binario: {bin}).",
               "pt": "QGIS LTR instalado em {root} (binário: {bin})."},
    "o4w.open": {"es": "Ábrelo desde el menú Inicio ('QGIS LTR (usuario)') o con {bat}",
                 "pt": "Abra-o pelo menu Iniciar ('QGIS LTR (usuario)') ou com {bat}"},
    "o4w.err": {"es": "OSGeo4W setup devolvió código {rc}{nobin}. Revisa el log de "
                      "OSGeo4W en {log}",
                "pt": "O setup do OSGeo4W retornou o código {rc}{nobin}. Verifique o "
                      "log do OSGeo4W em {log}"},
    "o4w.longpath": {"es": "La carpeta {root} es demasiado larga ({n} caracteres; máximo "
                           "{max}) para instalar QGIS: Windows limita las rutas a 260. "
                           "Elige una carpeta raíz más corta, por ejemplo C:\\qgis-mcp.",
                     "pt": "A pasta {root} é longa demais ({n} caracteres; máximo {max}) "
                           "para instalar o QGIS: o Windows limita os caminhos a 260. "
                           "Escolha uma pasta raiz mais curta, por exemplo C:\\qgis-mcp."},
    "o4w.nobin": {"es": " y no se encontró el binario de QGIS",
                  "pt": " e o binário do QGIS não foi encontrado"},
    # ── pasos 1 y 2 (versión 2.1.0: Claude por usuario, QGIS 3.44 verificado) ──
    "run.timeout": {"es": "{exe} no terminó en {n} s y se detuvo.",
                    "pt": "{exe} não terminou em {n} s e foi interrompido."},
    "st.claude_installed": {"es": "instalado v{v} (firmado por Anthropic)",
                            "pt": "instalado v{v} (assinado pela Anthropic)"},
    "st.installed_msi": {"es": "instalado (MSI) v{v}", "pt": "instalado (MSI) v{v}"},
    "st.installed_user": {"es": "instalado sin admin v{v} en {root}",
                          "pt": "instalado sem admin v{v} em {root}"},
    "s1.dry": {"es": "[dry-run] consultaría la última versión del canal oficial ({feed}), "
                     "descargaría el Setup.exe vigente (se obtiene de {url}), "
                     "comprobaría su firma y lo instalaría POR USUARIO, sin administrador; "
                     "después lo llevaría a la última versión del canal.",
               "pt": "[dry-run] consultaria a última versão do canal oficial ({feed}), "
                     "baixaria o Setup.exe vigente (obtido de {url}), verificaria a "
                     "assinatura e o instalaria POR USUÁRIO, sem administrador; depois o "
                     "levaria à última versão do canal."},
    "s1.nofeed": {"es": "No pude leer el canal oficial de versiones de Claude Desktop "
                        "(¿sin internet o proxy?). No se puede comprobar si es la última.",
                  "pt": "Não consegui ler o canal oficial de versões do Claude Desktop "
                        "(sem internet ou proxy?). Não é possível verificar se é a última."},
    "s1.nourl": {"es": "No pude resolver la dirección oficial del instalador de Claude "
                       "Desktop (¿sin internet o proxy?).",
                 "pt": "Não consegui resolver o endereço oficial do instalador do Claude "
                       "Desktop (sem internet ou proxy?)."},
    "s1.running": {"es": "Instalando Claude Desktop para tu usuario (no requiere administrador)…",
                   "pt": "Instalando o Claude Desktop para o seu usuário (não requer administrador)…"},
    "s1.autofail": {"es": "El instalador de Claude Desktop no dejó la aplicación instalada ({reason}).",
                    "pt": "O instalador do Claude Desktop não deixou o aplicativo instalado ({reason})."},
    "s1.updating": {"es": "Actualizando Claude Desktop a la última versión del canal oficial ({v})…",
                    "pt": "Atualizando o Claude Desktop para a última versão do canal oficial ({v})…"},
    "s1.update_fail": {"es": "Claude Desktop quedó en {v}, pero el canal oficial publica {latest}; "
                             "no se pudo actualizar ahora.",
                       "pt": "O Claude Desktop ficou na {v}, mas o canal oficial publica a {latest}; "
                             "não foi possível atualizar agora."},
    "w.claude_update": {"es": "Claude Desktop quedó en la versión {v} y la última publicada es "
                              "{latest}. Ábrelo: se actualiza solo, o vuelve a ejecutar este "
                              "instalador.",
                        "pt": "O Claude Desktop ficou na versão {v} e a última publicada é "
                              "{latest}. Abra-o: ele se atualiza sozinho, ou execute este "
                              "instalador de novo."},
    "s1.is_latest": {"es": "Claude Desktop {v} es la última versión estable publicada.",
                     "pt": "O Claude Desktop {v} é a última versão estável publicada."},
    "s1.outdated": {"es": "Tu Claude Desktop ({v}) es anterior a la última publicada ({latest}) "
                          "y es una instalación que este instalador no puede actualizar sin "
                          "administrador. Actualízalo desde la propia aplicación o reinstálalo "
                          "desde claude.com/download.",
                    "pt": "Seu Claude Desktop ({v}) é anterior à última publicada ({latest}) e "
                          "é uma instalação que este instalador não consegue atualizar sem "
                          "administrador. Atualize pelo próprio aplicativo ou reinstale em "
                          "claude.com/download."},
    "s1.binver": {"es": "Ejecutable instalado: {path} (versión {v})",
                  "pt": "Executável instalado: {path} (versão {v})"},
    "s1.ok": {"es": "Claude Desktop instalado (v{v}).", "pt": "Claude Desktop instalado (v{v})."},
    "s2.other_series": {"es": "Hay un QGIS {v}, pero este instalador garantiza la serie "
                              "{series} LTR: se instalará aparte, sin tocar el otro.",
                        "pt": "Há um QGIS {v}, mas este instalador garante a série {series} "
                              "LTR: ela será instalada à parte, sem mexer no outro."},
    "s2.not_series": {"es": "Indicaste QGIS {v}, que no es de la serie {series} LTR: se "
                            "instalará la {series}.",
                      "pt": "Você indicou o QGIS {v}, que não é da série {series} LTR: a "
                            "{series} será instalada."},
    "s2.unverified": {"es": "No se pudo leer la versión de ese QGIS: no se comprobó que sea 3.44.",
                      "pt": "Não foi possível ler a versão desse QGIS: não foi verificado que seja 3.44."},
    "s2.latest_ok": {"es": "QGIS {v} es el último parche publicado de la serie 3.44 LTR.",
                     "pt": "O QGIS {v} é o último patch publicado da série 3.44 LTR."},
    "s2.patch_available": {"es": "Hay un parche más nuevo de 3.44 LTR ({latest}); tienes {v}. "
                                 "Actualízalo con el instalador de QGIS o con OSGeo4W.",
                           "pt": "Há um patch mais novo do 3.44 LTR ({latest}); você tem a {v}. "
                                 "Atualize com o instalador do QGIS ou o OSGeo4W."},
    "s2.running_skip": {"es": "Hay un parche más nuevo ({latest}; tienes {v}) pero QGIS está "
                              "abierto: ciérralo y vuelve a ejecutar para actualizarlo.",
                        "pt": "Há um patch mais novo ({latest}; você tem a {v}) mas o QGIS está "
                              "aberto: feche-o e execute de novo para atualizar."},
    "s2.upgrading": {"es": "Actualizando QGIS {v} → {latest} (último parche de la serie 3.44 LTR)…",
                     "pt": "Atualizando o QGIS {v} → {latest} (último patch da série 3.44 LTR)…"},
    "msi.resolved": {"es": "Último MSI de la serie 3.44 en qgis.org: {v}-{b}",
                     "pt": "Último MSI da série 3.44 em qgis.org: {v}-{b}"},
    "msi.noindex": {"es": "No pude leer el índice de descargas de qgis.org; uso la última "
                          "versión verificada: {v}-{b}.",
                    "pt": "Não consegui ler o índice de downloads do qgis.org; uso a última "
                          "versão verificada: {v}-{b}."},
    "o4w.noindex": {"es": "No pude leer el índice del repositorio OSGeo4W; la versión se "
                          "comprobará al terminar.",
                    "pt": "Não consegui ler o índice do repositório OSGeo4W; a versão será "
                          "verificada ao terminar."},
    "o4w.resolved": {"es": "El repositorio OSGeo4W sirve qgis-ltr {v}.",
                     "pt": "O repositório OSGeo4W serve o qgis-ltr {v}."},
    "o4w.series_changed": {"es": "El paquete qgis-ltr del repositorio OSGeo4W ya es la {v}, que "
                                 "no es de la serie {series} LTR. No se instala para no dejar "
                                 "otra versión. Usa el MSI oficial de la serie {series} "
                                 "(--qgis-install msi, con administrador) o espera una "
                                 "versión nueva de este instalador.",
                           "pt": "O pacote qgis-ltr do repositório OSGeo4W já é a {v}, que não "
                                 "é da série {series} LTR. Não será instalado para não deixar "
                                 "outra versão. Use o MSI oficial da série {series} "
                                 "(--qgis-install msi, com administrador) ou aguarde uma nova "
                                 "versão deste instalador."},
    "qv.dry": {"es": "[dry-run] resolvería el último parche de la serie {series} y, al terminar, "
                     "leería la versión del binario: si no es {series}.x, el paso falla.",
               "pt": "[dry-run] resolveria o último patch da série {series} e, ao terminar, "
                     "leria a versão do binário: se não for {series}.x, o passo falha."},
    "qv.ok": {"es": "Versión comprobada en el binario: QGIS {v} (serie {series} LTR).",
              "pt": "Versão verificada no binário: QGIS {v} (série {series} LTR)."},
    "qv.unreadable": {"es": "QGIS se instaló pero no pude leer su versión en {root}.",
                      "pt": "O QGIS foi instalado mas não consegui ler a versão em {root}."},
    "qv.wrong": {"es": "Quedó instalado QGIS {v}, que NO es de la serie {series} LTR.",
                 "pt": "Ficou instalado o QGIS {v}, que NÃO é da série {series} LTR."},
    "s7.qgis_ok": {"es": "QGIS {v} (serie {series} LTR, leída del binario) en {path}",
                   "pt": "QGIS {v} (série {series} LTR, lida do binário) em {path}"},
    "s7.qgis_wrong": {"es": "El QGIS instalado es {v}, NO de la serie {series} LTR.",
                      "pt": "O QGIS instalado é o {v}, NÃO da série {series} LTR."},
    "s7.qgis_missing": {"es": "No se encontró QGIS {series} LTR en este equipo.",
                        "pt": "O QGIS {series} LTR não foi encontrado neste computador."},
    "s7.qgis_assumed": {"es": "No se pudo comprobar la versión de QGIS (--assume-installed).",
                        "pt": "Não foi possível verificar a versão do QGIS (--assume-installed)."},
    "s7.claude_ok": {"es": "Claude Desktop {v} en {loc}",
                     "pt": "Claude Desktop {v} em {loc}"},
    "s7.claude_latest": {"es": "Es la última versión estable publicada ({v}).",
                         "pt": "É a última versão estável publicada ({v})."},
    "s7.claude_old": {"es": "Claude Desktop {v}: el canal oficial ya publica {latest}.",
                      "pt": "Claude Desktop {v}: o canal oficial já publica a {latest}."},
    "s7.claude_missing": {"es": "Claude Desktop no está instalado (pendiente del paso 1).",
                          "pt": "O Claude Desktop não está instalado (pendente do passo 1)."},
    "s7.claude_sig_bad": {"es": "La firma de {path} NO es válida de Anthropic.",
                          "pt": "A assinatura de {path} NÃO é válida da Anthropic."},
    # ── paso 3 ───────────────────────────────────────────────────────────
    "s3.title": {"es": "Entorno de Python del servidor (aislado)",
                 "pt": "Ambiente Python do servidor (isolado)"},
    "s3.dry": {"es": "[dry-run] descargaría uv {uv} y un CPython {py} propio, e instalaría "
                     "en {env}: {deps}",
               "pt": "[dry-run] baixaria o uv {uv} e um CPython {py} próprio, e instalaria "
                     "em {env}: {deps}"},
    "s3.reuse": {"es": "El Python propio ya está instalado y funciona: {py}",
                 "pt": "O Python próprio já está instalado e funciona: {py}"},
    "s3.python": {"es": "Descargando un CPython {py} propio en {dir} (~25 MB)…",
                  "pt": "Baixando um CPython {py} próprio em {dir} (~25 MB)…"},
    "s3.pyerr": {"es": "No se pudo instalar el CPython propio.",
                 "pt": "Não foi possível instalar o CPython próprio."},
    "s3.blocked": {"es": "Windows no deja ejecutar {py}. Suele ser el antivirus o una "
                         "directiva de Control de aplicaciones; añade una excepción "
                         "para la carpeta raíz y reintenta.",
                   "pt": "O Windows não permite executar {py}. Costuma ser o antivírus ou "
                         "uma política de Controle de aplicativos; adicione uma exceção "
                         "para a pasta raiz e tente de novo."},
    "s3.deps": {"es": "Instalando dependencias fijadas: {deps}",
                "pt": "Instalando as dependências fixadas: {deps}"},
    "s3.depserr": {"es": "Falló la instalación de dependencias. Si Claude Desktop está "
                         "abierto, ciérralo por completo (bandeja → Salir) y reintenta.",
                   "pt": "A instalação das dependências falhou. Se o Claude Desktop estiver "
                         "aberto, feche-o por completo (bandeja → Sair) e tente de novo."},
    "s3.ok": {"es": "Entorno de Python listo.", "pt": "Ambiente Python pronto."},
    # ── paso 4 ───────────────────────────────────────────────────────────
    "s4.title": {"es": "Plugin QGIS MCP + servidor MCP",
                 "pt": "Plugin QGIS MCP + servidor MCP"},
    "s4.url": {"es": "Usando URL de plugin indicada: {url}",
               "pt": "Usando a URL de plugin indicada: {url}"},
    "s4.forkfail": {"es": "No se pudo obtener el fork ({exc}).",
                    "pt": "Não foi possível obter o fork ({exc})."},
    "s4.fallback": {"es": "Recurriendo al upstream original (nkarasiak, MIT).",
                    "pt": "Recorrendo ao upstream original (nkarasiak, MIT)."},
    "s4.dry": {"es": "[dry-run] extraería el ZIP, copiaría el servidor a {server} y lo "
                     "instalaría en el entorno aislado.",
               "pt": "[dry-run] extrairia o ZIP, copiaria o servidor para {server} e o "
                     "instalaria no ambiente isolado."},
    "s4.badzip": {"es": "El ZIP del plugin está dañado: {exc}",
                  "pt": "O ZIP do plugin está corrompido: {exc}"},
    "s4.nometa": {"es": "El repositorio no contiene qgis_mcp_plugin/metadata.txt.",
                  "pt": "O repositório não contém qgis_mcp_plugin/metadata.txt."},
    "s4.nosrc": {"es": "El repositorio no trae src/ o pyproject.toml: no hay servidor "
                       "MCP que instalar.",
                 "pt": "O repositório não traz src/ ou pyproject.toml: não há servidor "
                       "MCP para instalar."},
    "s4.servercopied": {"es": "Código del servidor MCP copiado a {dir}",
                        "pt": "Código do servidor MCP copiado para {dir}"},
    "s4.installing": {"es": "Instalando el servidor MCP en el entorno aislado…",
                      "pt": "Instalando o servidor MCP no ambiente isolado…"},
    "s4.installerr": {"es": "No se pudo instalar el servidor MCP. Si Claude Desktop está "
                            "abierto, ciérralo por completo (bandeja → Salir) y reintenta.",
                      "pt": "Não foi possível instalar o servidor MCP. Se o Claude Desktop "
                            "estiver aberto, feche-o por completo (bandeja → Sair) e tente "
                            "de novo."},
    "s4.ok": {"es": "Plugin y servidor MCP v{v} preparados.",
              "pt": "Plugin e servidor MCP v{v} preparados."},
    # ── paso 5 ───────────────────────────────────────────────────────────
    "s5.title": {"es": "Configurar QGIS (desplegar y habilitar el plugin)",
                 "pt": "Configurar o QGIS (implantar e habilitar o plugin)"},
    "s5.dry_copy": {"es": "[dry-run] copiaría el plugin -> {dest}",
                    "pt": "[dry-run] copiaria o plugin -> {dest}"},
    "s5.dry_enable": {"es": "[dry-run] habilitaría 'qgis_mcp_plugin' en {ini}",
                      "pt": "[dry-run] habilitaria 'qgis_mcp_plugin' em {ini}"},
    "s5.notfound": {"es": "No encuentro el plugin extraído. Ejecuta antes el paso 4.",
                    "pt": "Não encontro o plugin extraído. Execute antes o passo 4."},
    "s5.qgis_open": {"es": "QGIS está abierto. Ciérralo: si no, el plugin no aparecerá "
                           "hasta que lo reinicies.",
                     "pt": "O QGIS está aberto. Feche-o: caso contrário, o plugin só "
                           "aparecerá depois de reiniciá-lo."},
    "s5.qgis_wait": {"es": "  Cierra QGIS y pulsa Enter para continuar: ",
                     "pt": "  Feche o QGIS e pressione Enter para continuar: "},
    "s5.copyerr": {"es": "No se pudo escribir en {dest}: {exc}",
                   "pt": "Não foi possível gravar em {dest}: {exc}"},
    "s5.copied": {"es": "Plugin copiado a {dest}", "pt": "Plugin copiado para {dest}"},
    "s5.iniwarn": {"es": "No pude habilitar el plugin automáticamente ({exc}).",
                   "pt": "Não consegui habilitar o plugin automaticamente ({exc})."},
    "w.enable": {"es": "Habilita 'QGIS MCP' a mano en QGIS: Complementos → Administrar "
                       "e instalar complementos → Instalados.",
                 "pt": "Habilite o 'QGIS MCP' manualmente no QGIS: Complementos → "
                       "Gerenciar e instalar complementos → Instalados."},
    "s5.ok": {"es": "QGIS configurado.", "pt": "QGIS configurado."},
    "ini.created": {"es": "QGIS aún no se había abierto en este perfil: se creó {ini} "
                          "con el plugin habilitado.",
                    "pt": "O QGIS ainda não tinha sido aberto neste perfil: {ini} foi "
                          "criado com o plugin habilitado."},
    "ini.autostart": {"es": "Inicio automático activado: el servidor del plugin arrancará "
                            "solo al abrir QGIS.",
                      "pt": "Início automático ativado: o servidor do plugin iniciará "
                            "sozinho ao abrir o QGIS."},
    "ini.already": {"es": "El plugin ya estaba habilitado en {ini}",
                    "pt": "O plugin já estava habilitado em {ini}"},
    "ini.enabled": {"es": "Plugin habilitado en {ini} (respaldo: {bak})",
                    "pt": "Plugin habilitado em {ini} (backup: {bak})"},
    # ── paso 6 ───────────────────────────────────────────────────────────
    "s6.title": {"es": "Configurar Claude Desktop (claude_desktop_config.json)",
                 "pt": "Configurar o Claude Desktop (claude_desktop_config.json)"},
    "s6.dry": {"es": "[dry-run] escribiría en {path}:",
               "pt": "[dry-run] escreveria em {path}:"},
    "s6.noenv": {"es": "El servidor MCP aún no está instalado. Ejecuta antes los pasos 3 y 4.",
                 "pt": "O servidor MCP ainda não está instalado. Execute antes os passos 3 e 4."},
    "s6.unchanged": {"es": "La configuración de {path} ya estaba al día; no se tocó.",
                     "pt": "A configuração em {path} já estava atualizada; não foi alterada."},
    "s6.backup": {"es": "Respaldo creado: {name}", "pt": "Backup criado: {name}"},
    "s6.badjson": {"es": "El config existente no era JSON válido; se reemplaza (quedó "
                         "el respaldo).",
                   "pt": "O config existente não era um JSON válido; será substituído "
                         "(o backup foi mantido)."},
    "s6.written": {"es": "Config de Claude escrita en {path}",
                   "pt": "Config do Claude gravada em {path}"},
    "s6.writeerr": {"es": "No se pudo escribir {path}: {exc}",
                    "pt": "Não foi possível gravar {path}: {exc}"},
    "s6.restart": {"es": "Claude Desktop está abierto y no lee la configuración hasta "
                         "reiniciarse.",
                   "pt": "O Claude Desktop está aberto e só lê a configuração ao ser "
                         "reiniciado."},
    "w.restart": {"es": "Cierra Claude Desktop POR COMPLETO (icono de la bandeja del "
                        "sistema → Salir; cerrar la ventana no basta) y vuelve a abrirlo.",
                  "pt": "Feche o Claude Desktop POR COMPLETO (ícone da bandeja do "
                        "sistema → Sair; fechar a janela não basta) e abra-o de novo."},
    # ── paso 7 ───────────────────────────────────────────────────────────
    "s7.title": {"es": "Verificación (¿quedó funcionando de verdad?)",
                 "pt": "Verificação (ficou funcionando de verdade?)"},
    "s7.dry": {"es": "[dry-run] comprobaría plugin, perfil, configuración y arrancaría "
                     "el servidor MCP para ver que responde.",
               "pt": "[dry-run] verificaria plugin, perfil, configuração e iniciaria o "
                     "servidor MCP para ver se responde."},
    "s7.plugin_ok": {"es": "Plugin v{v} presente en {dest}",
                     "pt": "Plugin v{v} presente em {dest}"},
    "s7.plugin_bad": {"es": "Falta el plugin en {dest}", "pt": "Falta o plugin em {dest}"},
    "s7.ini_ok": {"es": "Plugin habilitado en {ini}", "pt": "Plugin habilitado em {ini}"},
    "s7.ini_bad": {"es": "El plugin NO está habilitado en {ini}",
                   "pt": "O plugin NÃO está habilitado em {ini}"},
    "s7.cfg_ok": {"es": "Entrada 'qgis' correcta en {path}",
                  "pt": "Entrada 'qgis' correta em {path}"},
    "s7.cfg_bad": {"es": "Falta la entrada 'qgis' (o el JSON es inválido) en {path}",
                   "pt": "Falta a entrada 'qgis' (ou o JSON é inválido) em {path}"},
    "s7.cmd_missing": {"es": "El ejecutable configurado no existe: {cmd} (en {path})",
                       "pt": "O executável configurado não existe: {cmd} (em {path})"},
    "s7.starting": {"es": "Arrancando el servidor MCP tal como lo hará Claude Desktop…",
                    "pt": "Iniciando o servidor MCP como o Claude Desktop fará…"},
    "s7.server_ok": {"es": "El servidor MCP responde: {name}, {n} herramientas.",
                     "pt": "O servidor MCP responde: {name}, {n} ferramentas."},
    "s7.server_bad": {"es": "El servidor MCP NO respondió. Últimas líneas de su salida:",
                      "pt": "O servidor MCP NÃO respondeu. Últimas linhas da saída:"},
    "s7.port_open": {"es": "QGIS ya está escuchando en el puerto 9876 (servidor del "
                           "plugin iniciado).",
                     "pt": "O QGIS já está escutando na porta 9876 (servidor do plugin "
                           "iniciado)."},
    "s7.port_closed": {"es": "QGIS todavía no escucha en el puerto 9876: es normal hasta "
                             "que pulses 'Start Server' en el plugin.",
                       "pt": "O QGIS ainda não escuta na porta 9876: é normal até você "
                             "clicar em 'Start Server' no plugin."},
    # ── desinstalación ───────────────────────────────────────────────────
    "un.title": {"es": "DESINSTALACIÓN (plugin y configuración; no toca Claude ni QGIS)",
                 "pt": "DESINSTALAÇÃO (plugin e configuração; não mexe no Claude nem no QGIS)"},
    "un.dry": {"es": "[dry-run] quitaría {path}", "pt": "[dry-run] removeria {path}"},
    "un.removed": {"es": "Eliminado {path}", "pt": "Removido {path}"},
    "un.basedir": {"es": "Para terminar, borra a mano la carpeta {path} (con Claude "
                         "Desktop cerrado).",
                   "pt": "Para terminar, apague manualmente a pasta {path} (com o Claude "
                         "Desktop fechado)."},
    # ── interfaz general ─────────────────────────────────────────────────
    "ui.banner1": {"es": "QGIS MCP - Instalador ETL  v{v}",
                   "pt": "QGIS MCP - Instalador ETL  v{v}"},
    "ui.banner2": {"es": "Claude Desktop + QGIS LTR + plugin + servidor MCP",
                   "pt": "Claude Desktop + QGIS LTR + plugin + servidor MCP"},
    "ui.choose": {"es": "Tú eliges DÓNDE se instala todo. Enter = valor por defecto.\n",
                  "pt": "Você escolhe ONDE tudo será instalado. Enter = valor padrão.\n"},
    "ui.rootdir": {"es": "Carpeta raíz para QGIS MCP:", "pt": "Pasta raiz para o QGIS MCP:"},
    "ui.root": {"es": "Carpeta raíz : {v}", "pt": "Pasta raiz    : {v}"},
    "ui.profile": {"es": "Perfil QGIS  : {v}", "pt": "Perfil QGIS   : {v}"},
    "ui.qgismode": {"es": "Install QGIS : {v}{extra}", "pt": "Instalar QGIS : {v}{extra}"},
    "ui.qgismode_user": {"es": " (sin admin → carpeta de usuario)",
                         "pt": " (sem admin → pasta do usuário)"},
    "ui.steps": {"es": "Pasos        : {v}", "pt": "Passos        : {v}"},
    "ui.lang": {"es": "Idioma       : español", "pt": "Idioma        : português (BR)"},
    "ui.mode": {"es": "Modo         : {v}", "pt": "Modo          : {v}"},
    "ui.mode_dry": {"es": "DRY-RUN (no toca nada)", "pt": "DRY-RUN (não toca em nada)"},
    "ui.mode_real": {"es": "real", "pt": "real"},
    "ui.sigoff": {"es": "Verificación de firma DESACTIVADA.",
                  "pt": "Verificação de assinatura DESATIVADA."},
    "ui.notwin": {"es": "Este instalador solo funciona en Windows (fuera de Windows "
                        "solo admite --dry-run).",
                  "pt": "Este instalador só funciona no Windows (fora do Windows só "
                        "aceita --dry-run)."},
    "ui.continue": {"es": "\n¿Continuar? [S/n]: ", "pt": "\nContinuar? [S/n]: "},
    "ui.cancelled": {"es": "Cancelado por el usuario.", "pt": "Cancelado pelo usuário."},
    "ui.interrupted": {"es": "Interrumpido por el usuario.",
                       "pt": "Interrompido pelo usuário."},
    "ui.badsteps": {"es": "Pasos no válidos: {v}. Usa números del 1 al 7, por ejemplo "
                          "'4,5,6' o '3-7'.",
                    "pt": "Passos inválidos: {v}. Use números de 1 a 7, por exemplo "
                          "'4,5,6' ou '3-7'."},
    "ui.badbase": {"es": "No se puede escribir en la carpeta raíz {path}: {exc}",
                   "pt": "Não é possível gravar na pasta raiz {path}: {exc}"},
    "ui.exception": {"es": "El paso {n} lanzó una excepción: {exc}",
                     "pt": "O passo {n} lançou uma exceção: {exc}"},
    "ui.stepfail": {"es": "El paso {n} falló. Detengo la cadena ETL.",
                    "pt": "O passo {n} falhou. Interrompendo a cadeia ETL."},
    "ui.summary": {"es": "RESUMEN", "pt": "RESUMO"},
    "ui.sumline": {"es": "  [{mark}] Paso {n}: {label}{extra}",
                   "pt": "  [{mark}] Passo {n}: {label}{extra}"},
    "lbl.1": {"es": "Claude Desktop", "pt": "Claude Desktop"},
    "lbl.2": {"es": "QGIS", "pt": "QGIS"},
    "lbl.3": {"es": "Entorno de Python", "pt": "Ambiente Python"},
    "lbl.4": {"es": "Plugin + servidor MCP", "pt": "Plugin + servidor MCP"},
    "lbl.5": {"es": "Configurar QGIS", "pt": "Configurar o QGIS"},
    "lbl.6": {"es": "Configurar Claude", "pt": "Configurar o Claude"},
    "lbl.7": {"es": "Verificación", "pt": "Verificação"},
    "ui.failed": {"es": "La instalación NO terminó. Nada de lo que falta se dio por hecho.",
                  "pt": "A instalação NÃO terminou. Nada do que falta foi dado como feito."},
    "ui.dry_done": {"es": "Plan mostrado. No se descargó ni se modificó nada.",
                    "pt": "Plano exibido. Nada foi baixado nem modificado."},
    "ui.done": {"es": "Instalación completa y verificada.",
                "pt": "Instalação completa e verificada."},
    "ui.partial": {"es": "Pasos completados. (La verificación, paso 7, no se ejecutó.)",
                   "pt": "Passos concluídos. (A verificação, passo 7, não foi executada.)"},
    "ui.partial_warn": {"es": "Pasos completados, pero queda esto por hacer a mano:",
                        "pt": "Passos concluídos, mas falta fazer isto manualmente:"},
    "ui.done_warn": {"es": "Instalación completa, pero queda esto por hacer a mano:",
                     "pt": "Instalação completa, mas falta fazer isto manualmente:"},
    "ui.next1": {"es": "Para usarlo:", "pt": "Para usar:"},
    "ui.next2": {"es": "  1) Abre QGIS → menú Complementos → QGIS MCP → Start Server.",
                 "pt": "  1) Abra o QGIS → menu Complementos → QGIS MCP → Start Server."},
    "ui.next2_auto": {"es": "  1) Abre QGIS (el servidor MCP del plugin arranca solo).",
                      "pt": "  1) Abra o QGIS (o servidor MCP do plugin inicia sozinho)."},
    "ui.next3": {"es": "  2) Cierra Claude Desktop por completo (bandeja → Salir) y ábrelo.",
                 "pt": "  2) Feche o Claude Desktop por completo (bandeja → Sair) e abra-o."},
    "ui.next4": {"es": "  3) En Claude, pide: «haz ping a QGIS».",
                 "pt": "  3) No Claude, peça: «faça ping no QGIS»."},
    "ui.checklog": {"es": "Log de esta ejecución: {path}",
                    "pt": "Log desta execução: {path}"},
    "ui.pressenter": {"es": "Pulsa Enter para cerrar esta ventana…",
                      "pt": "Pressione Enter para fechar esta janela…"},
    # ── ayuda de la línea de comandos ────────────────────────────────────
    "h.desc": {"es": "Instalador ETL de QGIS MCP (transparente y auditable).",
               "pt": "Instalador ETL do QGIS MCP (transparente e auditável)."},
    "h.basedir": {"es": "Carpeta raíz de instalación (por defecto: tu carpeta de "
                        "usuario/qgis-mcp).",
                  "pt": "Pasta raiz da instalação (padrão: sua pasta de usuário/qgis-mcp)."},
    "h.profile": {"es": "Perfil de QGIS. 'auto' (por defecto) usa el perfil activo.",
                  "pt": "Perfil do QGIS. 'auto' (padrão) usa o perfil ativo."},
    "h.steps": {"es": "Pasos a ejecutar, ej. '4,5,6,7' o '3-7'. Vacío = todos (1 a 7).",
                "pt": "Passos a executar, ex.: '4,5,6,7' ou '3-7'. Vazio = todos (1 a 7)."},
    "h.pluginurl": {"es": "URL del ZIP del plugin (sobreescribe el fork).",
                    "pt": "URL do ZIP do plugin (substitui o fork)."},
    "h.assume": {"es": "Asume ya instalado y omite su instalación. "
                       "Lista: claude,qgis (útil en modo desatendido).",
                 "pt": "Assume que já está instalado e pula a instalação. "
                       "Lista: claude,qgis (útil no modo não interativo)."},
    "h.force": {"es": "Instala aunque ya se detecte. Lista: claude,qgis.",
                "pt": "Instala mesmo que já seja detectado. Lista: claude,qgis."},
    "h.qgisinstall": {"es": "Cómo instalar QGIS si falta: 'msi' (estándar, requiere "
                            "administrador), 'user' (en tu carpeta, SIN administrador), "
                            "'auto' (detecta permisos; por defecto).",
                      "pt": "Como instalar o QGIS se estiver faltando: 'msi' (padrão, "
                            "requer administrador), 'user' (na sua pasta, SEM "
                            "administrador), 'auto' (detecta permissões; padrão)."},
    "h.noninteractive": {"es": "Sin preguntas (usa --base-dir o la carpeta por defecto).",
                         "pt": "Sem perguntas (usa --base-dir ou a pasta padrão)."},
    "h.dryrun": {"es": "Muestra el plan sin descargar ni instalar nada.",
                 "pt": "Mostra o plano sem baixar nem instalar nada."},
    "h.skipsig": {"es": "Omite la verificación de firma (NO recomendado).",
                  "pt": "Ignora a verificação de assinatura (NÃO recomendado)."},
    "h.lang": {"es": "Idioma de los mensajes: es, pt o auto (detecta el de Windows).",
               "pt": "Idioma das mensagens: es, pt ou auto (detecta o do Windows)."},
    "h.autostart": {"es": "Hace que el servidor del plugin arranque solo al abrir QGIS "
                          "(equivale a marcar 'Auto-start on startup' en el plugin).",
                    "pt": "Faz o servidor do plugin iniciar sozinho ao abrir o QGIS "
                          "(equivale a marcar 'Auto-start on startup' no plugin)."},
    "h.uninstall": {"es": "Quita el plugin de QGIS y la entrada 'qgis' de Claude "
                          "(no desinstala Claude ni QGIS).",
                    "pt": "Remove o plugin do QGIS e a entrada 'qgis' do Claude "
                          "(não desinstala o Claude nem o QGIS)."},
}
