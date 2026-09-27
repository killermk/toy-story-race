# Decisão de engine (insumos)

- **Data:** 2026-09-27
- **Dimensão:** insumos para a decisão de engine (Prompt Master, seção 10). Cobre Unreal Engine 5.8, Unity 6, Godot 4.x e outras engines, além de um teste de ambiente.
- **Papel deste documento:** verificação adversarial independente das 49 afirmações (UE-01 a UE-20, UY-01 a UY-12, GD-01 a GD-12, OT-01 a OT-04, ENV-01) levantadas por outro agente de pesquisa.

> **Pesquisa pública — PISTAS DE INVESTIGAÇÃO, não prova. Nada aqui é E1.**
>
> O arquivo original ("Disney_Pixar Toy Story Racer.zip.7z") **não** estava disponível nesta sessão. Este documento **não decide a engine**. Pela seção 10 do Prompt Master, a opção inicial continua sendo **Unreal Engine 5.8 (E0)**, e só se troca de engine com "vantagem substancial e demonstrável". A decisão final deve sair no `ENGINE_TECHNICAL_DECISION.md`, que ainda não existe.

---

## Método

### O que foi feito

1. **Cada fonte citada foi baixada de novo**, sem usar os arquivos de trabalho do agente produtor:
   - arquivos de texto por `raw.githubusercontent.com` (README, CHANGELOG, `.rst`, `.yml`, `.md`, `.cs`, `.json`);
   - refs por `git ls-remote`. Para datas de tags: `git fetch --depth=1 --filter=tree:0`, que baixa só o objeto do commit, sem árvore nem blobs;
   - busca de código e de repositórios pelo conector GitHub (datas de criação, licença e linguagem dos repositórios);
   - APIs públicas: registro npm, NuGet e índice do crates.io.
2. **Espelho RSS de terceiros.** As páginas do YouTube, Phoronix e GamingOnLinux estão bloqueadas. Por isso, título, data e descrição foram lidos no espelho [rumca-js/RSS-Link-Database-2026](https://github.com/rumca-js/RSS-Link-Database-2026) (JSON por dia e por feed). **O texto da descrição é da Epic, da Unity ou do veículo, mas chegou por terceiros.** Por isso, o teto desses itens é **E3**.
3. **Blog do vorixo.** O site `vorixo.github.io` está bloqueado. O post foi lido no **fonte Markdown do próprio autor** no GitHub ([vorixo/devtricks](https://github.com/vorixo/devtricks/blob/master/_posts/2024-05-04-phys-prediction-use.md), `last_modified_at: 2026-09-23`).
4. **Reprodução independente do ENV-01.** O SHA-512 do zip do Godot 4.7.2 (baixado pelo produtor) foi comparado com o `SHA512-SUMS.txt` oficial, baixado de novo nesta verificação. Depois, o autor desta verificação escreveu e rodou **um projeto mínimo próprio** (ver ENV-01).
5. **Bloqueios nesta verificação:**
   - WebFetch retornou `EGRESS_BLOCKED` para `www.youtube.com`, `vorixo.github.io` e `godotengine.org`.
   - `curl` sem resposta para `dev.epicgames.com`, `www.unrealengine.com`, `unity.com`, `www.phoronix.com`, `www.gamingonlinux.com`, `www.reddit.com`, `x.com`, `news.ycombinator.com` e `tomlooman.com`.
   - Endpoints `api.github.com/repos/...` recusados (repositório fora da sessão).
   - Cota de **WebSearch esgotada** (200/200).

### Conformidade

- Nenhuma ROM, ISO, BIOS ou asset do jogo foi baixado, linkado ou versionado.
- Nenhum código-fonte do Unreal Engine foi acessado. O acesso é restrito pela EULA, conforme o [perfil oficial da Epic](https://github.com/EpicGames/.github/blob/main/profile/README.md).
- O único binário executado foi o Godot 4.7.2 oficial, com hash conferido. Nada foi instalado nesta verificação. O pacote `mesa-vulkan-drivers` já tinha sido instalado pelo produtor.
- Arquivos de verificação ficaram no scratchpad da sessão, fora do repositório.

### Legenda

| Status | Significado |
|---|---|
| **sustentada** | A fonte foi lida e diz isso. |
| **sustentada (pista)** | A fonte diz isso, mas é wiki, fórum, repositório de terceiros ou texto gerado por IA. Continua H. |
| **sustentada com ressalva** | O essencial está na fonte, mas um trecho foi corrigido ou retirado (ver seção 6). |
| **não sustentada** | A fonte não diz isso. A afirmação sai do corpo (seção 6). |
| **fonte inacessível** | A fonte não pôde ser aberta. Fica H / NÃO CONFIRMADO. |

| Nível | Uso aqui |
|---|---|
| **E2** | Documento oficial do fornecedor, lido direto no repositório oficial dele (Epic, Unity, Godot, O3DE, Bevy, Flax) ou em registro oficial de pacotes (npm, NuGet, crates.io). |
| **E3** | Texto oficial lido por espelho de terceiros; blog técnico de especialista; imprensa especializada. |
| **H** | Repositório de terceiros sem fonte, texto gerado por IA, fórum, wiki. Rótulo **[pista]**. |
| **E1** | **Nenhuma** afirmação. Não há acesso ao jogo. |

---

## 1. Resumo

- **49 de 49 afirmações foram conferidas** na fonte (ou no espelho/fonte Markdown dela). **43 sustentadas integralmente** e **6 sustentadas com ressalva** (UE-12, UE-17, UE-20, UY-11, UY-12, GD-10). Nenhuma foi totalmente rejeitada. Foram retirados **trechos** e **2 notas de divergência** do produtor (seção 6).
- **UE 5.8:** está lançado. Isso tem prova oficial indireta (E2: branch `UE5.8` do Pixel Streaming, "Current release — tracks the latest shipped UE version") e textos da Epic lidos por espelho (E3). A **data exata diverge**: 17/06/2026 no State of Unreal × 23/06/2026 em uma pista de terceiros (D-01).
- **Maturidade dos sistemas do UE 5.8 críticos para um jogo de corrida** (Chaos Vehicles, Chaos Modular Vehicles, Mover, Iris) continua **NÃO CONFIRMADA** em fonte oficial. Só há pistas, e as pistas divergem sobre o Iris (D-04). Uma pista nova (N-01) localiza Chaos Vehicles e Mover em `Plugins/Experimental` no 5.8.
- **Agentes de IA:** Epic e Unity mantêm plugins oficiais para Claude Code (E2). O MCP da Epic fica em `Engine/Plugins/Experimental/...` (N-03, E2). O da Unity depende da Unity CLI, ainda em **beta**.
- **Godot 4.7.2** tem documentação oficial E2 sobre headless/CI, Jolt como padrão em projetos 3D novos, `VehicleBody3D` com limitações declaradas e ausência de ports oficiais para console.
- **Ambiente (reproduzido de forma independente):** neste container sem GPU, o Godot 4.7.2 rodou headless e renderizou split-screen 2×2 via CPU (llvmpipe) em OpenGL e Vulkan. UE e Unity **não foram testados** (downloads bloqueados ou gated).
- **O que só o original resolve:** quais requisitos a engine precisa cumprir, isto é, os comportamentos do jogo que o Modo Clássico precisa reproduzir (seção 5).

---

## 2. Tabelas de afirmações

A coluna **Status** traz o resultado desta verificação. A coluna **Como confirmar (fonte original)** aponta a fonte primária que falta ler. Nenhuma delas é o jogo, porque estas afirmações tratam de ferramentas, não do jogo.

### 2.1 Unreal Engine 5.8: lançamento, versões e futuro

| ID | Tópico | Afirmação (versão verificada) | Nível | Status | Fonte(s) | Como confirmar (fonte original) |
|---|---|---|---|---|---|---|
| UE-01 | Lançamento (evidência indireta) | No `DEVELOPING.md` da branch `UE5.8` do Pixel Streaming, a Epic descreve `UE5.8` como "Current release — tracks the latest shipped UE version". O pacote npm `@epicgames-ps/lib-pixelstreamingfrontend-ue5.8` foi criado em **2026-06-26T03:30:53Z**. A tag `UE5.8-0.1.0` aponta para o commit `15f96c6`, de 2026-06-26T10:45:18+10:00. As datas são **do plugin, não da engine**. | E2 (indireta) | sustentada | [DEVELOPING.md (branch UE5.8)](https://github.com/EpicGames/PixelStreamingInfrastructure/blob/UE5.8/DEVELOPING.md); [npm registry](https://registry.npmjs.org/@epicgames-ps/lib-pixelstreamingfrontend-ue5.8); [tag UE5.8-0.1.0](https://github.com/EpicGames/PixelStreamingInfrastructure/tree/UE5.8-0.1.0) | [unrealengine.com/news/unreal-engine-5-8-is-now-available](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available) (bloqueado) |
| UE-02 | Data de lançamento | Descrição do vídeo oficial "State of Unreal 2026 Official 4K" (publicado 2026-06-17T21:14:01Z): "...released Unreal Engine 5.8, open sourced ... Lore". O livestream estava marcado para "7 AM PT ... on June 17". O clipe "Unreal Engine 5.8 Is Now Available" foi publicado em **2026-06-23T16:00:21Z**. Todo o texto foi lido no espelho RSS. | E3 | sustentada (divergência nova em D-01) | [YouTube xXGSvLH9zAs](https://www.youtube.com/watch?v=xXGSvLH9zAs); [YouTube 9ikOoOzAhPE (livestream)](https://www.youtube.com/watch?v=9ikOoOzAhPE); [YouTube Aaf12f_LA_Y](https://www.youtube.com/watch?v=Aaf12f_LA_Y); espelhos [2026-06-17](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/06/2026-06-17/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json) e [2026-06-23](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/06/2026-06-23/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json); [pista] [Masterofowls UE58_Guide](https://github.com/Masterofowls/Unreal_Files/blob/HEAD/Docs/UE58_Guide.md) ("released on **17 June 2026**") | Post oficial da Epic e [release notes 5.8](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-5-8-release-notes) (bloqueados) |
| UE-03 | Preview | Artigo **gerado por IA** (`author_bot_id: machineherald-prime`, `contributor_model: Claude Sonnet 4.6`): "Epic Games released Unreal Engine 5.8 Preview on May 12, 2026 ... Launcher, GitHub, and for Linux". O artigo cita o tópico oficial do fórum. | H [pista] | sustentada (pista) | [Machine Herald (fonte .md)](https://github.com/the-machine-herald/machineherald.io/blob/HEAD/src/content/articles/2026-05/22-unreal-engine-58-preview-arrives-with-mesh-terrain-metahuman-crowds-and-a-new-lumen-performance-mode.md) | [Fórum Epic: Unreal Engine 5.8 Preview](https://forums.unrealengine.com/t/unreal-engine-5-8-preview/2721597) |
| UE-04 | Hotfixes | "UE 5.8.2 supports this flow" (vorixo). "hotfixes 5.8.1 and 5.8.2 are out" (Masterofowls). **Pista nova:** um repositório de terceiros diz que o anúncio do 5.8.2 no fórum é de **25/08/2026** e cita o known issue `UE-377426` (Xcode 26.4+). Data do 5.8.1: NÃO CONFIRMADA. Se há hotfix mais recente em set/2026: NÃO CONFIRMADO. | H [pista] | sustentada (pista) | [vorixo (fonte .md)](https://github.com/vorixo/devtricks/blob/master/_posts/2024-05-04-phys-prediction-use.md) ([página](https://vorixo.github.io/devtricks/phys-prediction-use/) bloqueada); [pista] [Masterofowls](https://github.com/Masterofowls/Unreal_Files/blob/HEAD/Docs/UE58_Guide.md); [pista] [JsizzleR UNREAL-AUTOMATION.md](https://github.com/JsizzleR/mobile-forces-2027/blob/HEAD/docs/archive/v0.1-network-plan/docs/research/UNREAL-AUTOMATION.md) | [Fórum: 5.8.1 Hotfix](https://forums.unrealengine.com/t/5-8-1-hotfix-released/2738864) e [5.8.2 Hotfix](https://forums.unrealengine.com/t/5-8-2-hotfix-released/2746335); Epic Games Launcher |
| UE-15 | 5.8 como último UE5 / UE6 | Tom Looman: "The release of UE 5.8 marks the final release before Epic Games is moving development efforts to Unreal Engine 6". Vídeo oficial "Unreal Engine 6 \| State of Unreal" (2026-06-24): "UE6 is about evolving how we ship and operate games". Digest de terceiros: "final major update of the UE5 generation (with the option to ship 5.9 if needed)" e, citando OC3D, "late-2027 Early Access, mid-2029 full release". Cronograma do UE6 em fonte oficial: NÃO CONFIRMADO. | E3 (Looman; texto oficial via espelho); digest = [pista] | sustentada (ver D-02 e D-03) | [Tom Looman (fonte .md)](https://github.com/tomlooman/tomlooman.github.io/blob/main/_posts/2026-08-05-unreal-engine-5-8-performance-highlights.md); [YouTube mGuaRAWdXPA](https://www.youtube.com/watch?v=mGuaRAWdXPA) via [espelho 2026-06-24](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/06/2026-06-24/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json); [pista] [swil-news digest](https://github.com/Supwils/swil-news/blob/HEAD/NEWS/gaming/en/2026-06-17_gaming-digest.md) | [epic.gm/road-to-ue6](https://epic.gm/road-to-ue6) (blog oficial, não lido) |
| UE-19 | Steam Frame | Título da notícia: "Unreal Engine 5.8 adds experimental Steam Frame support". Só o título e o resumo foram lidos, não o corpo. | E3 | sustentada | [GamingOnLinux 2026-05-13](https://www.gamingonlinux.com/2026/05/unreal-engine-5-8-adds-experimental-steam-frame-support-qualcomm-give-the-steam-frame-a-dedicated-page) via [espelho](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/05/2026-05-13/https...www.gamingonlinux.com.article_rss.php_entries.json) | Release notes 5.8 |

### 2.2 Unreal Engine 5.8: agentes de IA, automação e testes

| ID | Tópico | Afirmação (versão verificada) | Nível | Status | Fonte(s) | Como confirmar (fonte original) |
|---|---|---|---|---|---|---|
| UE-05 | MCP no editor | Descrições oficiais (via espelho): "Unreal Engine 5.8 ships with experimental Model Context Protocol (MCP) server support" (2026-06-23); "the new MCP plugin for integrating models like Claude" (Feature Highlights, 2026-06-17); "the Experimental MCP Plugin in Unreal Engine 5.8" (2026-09-07). Sessão "From Words to Worlds: Integrating MCP into the Unreal Editor" (2026-08-03): "Unreal Engine 5.8 is introducing an official Model Context Protocol (MCP) integration". | E3 | sustentada | [YouTube F2cWJFcTft4](https://www.youtube.com/watch?v=F2cWJFcTft4); [ExFF5gXVhDU](https://www.youtube.com/watch?v=ExFF5gXVhDU); [k0tgmrBuIJc](https://www.youtube.com/watch?v=k0tgmrBuIJc); [lDf_y-YPELo](https://www.youtube.com/watch?v=lDf_y-YPELo) (URL não citada pelo produtor); espelhos [06-17](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/06/2026-06-17/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json), [06-23](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/06/2026-06-23/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json), [08-03](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/08/2026-08-03/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json), [09-07](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/09/2026-09-07/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json) | Release notes 5.8; doc do plugin MCP em dev.epicgames.com |
| UE-06 | Plugin oficial Epic para Claude Code | O repositório "Unreal Engine Skills for Claude Code" foi criado em 2026-06-08T19:59:22Z. `plugin.json`: versão **3.1.1**, `license: MIT`, autor com e-mail `@epicgames.com`. Requisitos: plugins **ModelContextProtocol** e **AllToolsets** habilitados ("the server exposes none without it") e editor em execução. Porta padrão **8000**, caminho `/mcp`, ligado a `localhost:8000`. "Tool search" expõe 3 meta-ferramentas (`list_toolsets`, `describe_toolset`, `call_tool`). `ModelContextProtocol.GenerateClientConfig` suporta `ClaudeCode`, `Cursor`, `VSCode`, `Gemini` e `Codex`. Proxy opcional com binários Windows x64, macOS arm64, Linux x64 e Linux arm64. "`ProgrammaticToolset.execute_tool_script` executes arbitrary Python inside the editor process". | E2 | sustentada | [README](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin); [setup.md](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin/blob/main/skills/unreal-mcp/references/setup.md); [plugin.json](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin/blob/main/.claude-plugin/plugin.json) | O repositório não declara a versão mínima do UE. A ligação com o 5.8 vem de UE-05 (E3). Ver N-03. |
| UE-07 | Testes headless / CI | Skill oficial `create-toolset`: "When no editor is running, the command line launches a headless editor instance ... (~30 seconds) ... useful in CI". Exemplo: `UnrealEditor-Cmd.exe <Project>.uproject -ExecCmds="Automation RunTests AI.MyToolset;quit" -Unattended -NullRHI`. Os testes C++ usam `BEGIN_DEFINE_SPEC`/`END_DEFINE_SPEC`. Via MCP, o `AutomationTestToolset` expõe `DiscoverTests`, `ListTests`, `RunTests`, `GetTestStatus` e `GetTestResults`. | E2 | sustentada | [create-toolset SKILL.md](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin/blob/main/skills/create-toolset/SKILL.md) | O exemplo é Windows (`.exe`). Execução equivalente em Linux sem GPU: NÃO CONFIRMADA. |
| N-03 | MCP em pasta "Experimental" (**novo**) | O README oficial do plugin cita o caminho `Engine/Plugins/Experimental/ModelContextProtocol/Extras/Proxy`. A skill `create-toolset` manda ler testes em `Plugins/Experimental/Toolsets`. É coerente com o rótulo "experimental" de UE-05. | E2 | acrescentada nesta verificação | [README](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin); [create-toolset SKILL.md](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin/blob/main/skills/create-toolset/SKILL.md) | Release notes 5.8 (status oficial do plugin) |
| UE-18 | Epic Lore (VCS) | Repositório `EpicGames/lore` criado em 2026-05-21T19:32:07Z; linguagem **Rust**; licença **MIT**; README: "Next-generation open source version control", "optimized for projects that combine code with large binary assets". Phoronix (2026-06-17): "Epic Games announced today they have created a new version control system that is now open-source as Lore." | E2 (repositório); E3 (Phoronix via espelho) | sustentada | [EpicGames/lore](https://github.com/EpicGames/lore); [Phoronix](https://www.phoronix.com/news/Epic-Games-Lore-VCS) via [espelho](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/06/2026-06-17/https...www.phoronix.com.rss.php_entries.json) | [epicgames.github.io/lore](https://epicgames.github.io/lore/) (não lido) |
| UE-20 | Disco para build em contêiner | A documentação do ue4-docker (ferramenta comunitária, não oficial) exige "Minimum 800GB available disk space for building container images". O documento não é específico do 5.8. | E3 | sustentada com ressalva | [ue4-docker configuring-linux.adoc](https://github.com/adamrehn/ue4-docker/blob/HEAD/docs/configuring-linux.adoc) | Requisitos oficiais de hardware/disco do UE 5.8 (dev.epicgames.com, bloqueado) |

### 2.3 Unreal Engine 5.8: renderização, física, rede e consoles

| ID | Tópico | Afirmação (versão verificada) | Nível | Status | Fonte(s) | Como confirmar (fonte original) |
|---|---|---|---|---|---|---|
| UE-08 | MegaLights, Lumen Lite, Nanite | Tom Looman (post de 05-08-2026, citando as release notes): "MegaLights is now production ready"; **Lumen Lite** vem habilitado na escalabilidade "Medium", é "twice as fast as Lumen high quality", e "Epic still labels this as Beta"; "Significantly improved performance of Nanite rasterization & culling on handheld platforms". A descrição oficial "Feature Highlights" (via espelho) cita "production-ready MegaLights". | E3 | sustentada | [Tom Looman (fonte .md)](https://github.com/tomlooman/tomlooman.github.io/blob/main/_posts/2026-08-05-unreal-engine-5-8-performance-highlights.md); [YouTube ExFF5gXVhDU](https://www.youtube.com/watch?v=ExFF5gXVhDU) via [espelho 06-17](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/06/2026-06-17/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json) | [Release notes 5.8](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-5-8-release-notes) |
| UE-09 | Física em rede / ressimulação | Looman: "Optimize network overhead for replicated Input and State properties via the "legacy" RepGraph or Iris Last Resort replication in NetworkPhysicsComponent". vorixo: "UE 5.8 adds actions alongside inputs and states"; ligar **Enable Physics Prediction**; "Physics Replication Mode = Resimulation"; `UChaosVehicleMovementComponent` aparece entre os "systems from the engine that use this technology". Sample "Experimental Arcade Vehicle Sample Project": "Unreal Engine **5.8**". | E3 | sustentada | [Tom Looman](https://github.com/tomlooman/tomlooman.github.io/blob/main/_posts/2026-08-05-unreal-engine-5-8-performance-highlights.md); [vorixo (fonte .md)](https://github.com/vorixo/devtricks/blob/master/_posts/2024-05-04-phys-prediction-use.md); [ExperimentalArcadeVehicleSampleProject](https://github.com/vorixo/ExperimentalArcadeVehicleSampleProject) | Seção "Networked Physics" das release notes 5.8 |
| UE-10 | Chaos Modular Vehicles | Resumo em chinês, feito por terceiros, das release notes (captura de 2026-07-14): "**Chaos Modular Vehicles** \| 动态 Scene Graph 组件拼装车辆，客户端预测 + 服务端权威物理". A linha **não** traz rótulo de maturidade. | H [pista] | sustentada (pista) | [ImChong/Robotics_Notebooks](https://github.com/ImChong/Robotics_Notebooks/blob/HEAD/sources/sites/unreal-engine-5-8-docs.md) | Release notes 5.8 |
| N-01 | Pasta dos plugins Chaos Vehicles e Mover (**novo**) | Documento de terceiros "written 2026-09-06 ... against ... the Launcher 5.8 engine" lista "Chaos Vehicles (Experimental/ChaosVehiclesPlugin)" e "Mover 2.0 (Experimental/Mover, ChaosMover)". Cita também `UChaosWheeledVehicleMovementComponent` (`CHAOSVEHICLES_API`). Estar em pasta `Experimental` **não prova** o rótulo oficial de maturidade. | H [pista] | acrescentada nesta verificação | [HTRMC/mcp-unreal incomplete.txt](https://github.com/HTRMC/mcp-unreal/blob/HEAD/incomplete.txt) | Release notes 5.8; pasta `Engine/Plugins` de uma instalação 5.8 |
| UE-11 | Iris | Pistas **divergentes**. "Production Ready": unreal-sidekick (tabela "Iris Replication \| Beta \| **Production Ready**", arquivo com `verified: no` e `sources: []`), ImChong ("Iris \| Production Ready") e scenario-labs ("Iris is Production Ready for licensees in 5.8, generic replication still the default"). "Experimental": ue-is-renderer ("**still Experimental in 5.7/5.8**"; referência "(Experimental)"). Status oficial: NÃO CONFIRMADO. | H [pista] | sustentada (pista) (ver D-04) | [pista] [barrozo3d/unreal-sidekick](https://github.com/barrozo3d/unreal-sidekick/blob/HEAD/references/release-notes-ue58.md); [pista] [ImChong](https://github.com/ImChong/Robotics_Notebooks/blob/HEAD/sources/sites/unreal-engine-5-8-docs.md); [pista] [scenario-labs procedures.md](https://github.com/scenario-labs/skills/blob/HEAD/skills/game-engines/unreal/scenario-unreal-gameplay/references/procedures.md); [pista] [baadc0de/ue-is-renderer](https://github.com/baadc0de/ue-is-renderer/blob/HEAD/docs/evaluation.md) | Release notes 5.8 e página do Iris em dev.epicgames.com |
| UE-12 | Mover / Network Prediction | scenario-labs: "Mover still Experimental". mcp-unreal: "Mover 2.0 (Experimental/Mover, ChaosMover)" com "network prediction backends". Status oficial do Mover e do plugin Network Prediction: NÃO CONFIRMADO. | H [pista] | sustentada com ressalva | [pista] [scenario-labs SKILL.md](https://github.com/scenario-labs/skills/blob/HEAD/skills/game-engines/unreal/scenario-unreal-gameplay/SKILL.md); [pista] [HTRMC/mcp-unreal](https://github.com/HTRMC/mcp-unreal/blob/HEAD/incomplete.txt) | Release notes 5.8; documentação do Mover |
| UE-13 | Chaos: desempenho | Palestra oficial (via espelho, 2026-08-18): "up to 40% performance gains in targeted scenarios". Não cita versão exata. | E3 | sustentada | [YouTube wL5Hf1hT6c4](https://www.youtube.com/watch?v=wL5Hf1hT6c4) via [espelho 08-18](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/08/2026-08-18/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json) | Vídeo completo / release notes |
| UE-14 | Xbox / GDK | Descrição oficial (via espelho, 2026-08-08): "The Microsoft GDK plugins for Unreal Engine, publicly available in UE 5.8, give you a single path to build on Win64". Acesso a SDKs de PlayStation e Nintendo exige NDA com os fabricantes (não verificado para UE nesta pesquisa). | E3 | sustentada | [YouTube fQY2UzpTMsY](https://www.youtube.com/watch?v=fQY2UzpTMsY) via [espelho 08-08](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/08/2026-08-08/https...youtube.com.channel.UCBobmJyzsJ6Ll7UbfhI4iwQ_entries.json) | Documentação de plataformas em dev.epicgames.com |

### 2.4 Unreal Engine: licença

| ID | Tópico | Afirmação (versão verificada) | Nível | Status | Fonte(s) | Como confirmar (fonte original) |
|---|---|---|---|---|---|---|
| UE-16 | Licença / royalty | O perfil oficial da Epic no GitHub (último commit no README em 2026-08-17) diz que o UE "is free to get started (a 5% royalty only kicks in when your title earns over $1 million USD)". Os repositórios de código do UE exigem "Epic account linkage and acceptance of the applicable Epic license agreement". | E2 | sustentada | [EpicGames/.github profile README](https://github.com/EpicGames/.github/blob/main/profile/README.md) | [EULA](https://www.unrealengine.com/eula/unreal) (bloqueado) |
| UE-17 | Royalty 3,5% ("Launch Everywhere with Epic") | Post no r/Games (captura de 2025-01-01), citando o post oficial no X: o programa "reduces the fee on every sale on every platform including consoles from 5% to 3.5%" para jogos lançados na Epic Games Store ao mesmo tempo que em outras lojas. Documento de terceiros: "cuts it to **3.5%** for titles that launch on EGS day-and-date (from 2025-01-01)". | H [pista] (rebaixado de E3) | sustentada com ressalva | [pista] [captura r/Games](https://github.com/rumca-js/RSS-Link-Database-2025/blob/HEAD/2025/01/2025-01-01/https...www.reddit.com.r.Games..rss_entries.md); [pista] [r-melvin UNREAL_SPIKE.md](https://github.com/r-melvin/krakow-1795/blob/HEAD/docs/UNREAL_SPIKE.md) | [EULA](https://www.unrealengine.com/eula/unreal); [post oficial no X](https://x.com/UnrealEngine/status/1874470746921066890) (ambos bloqueados) |
| N-02 | Receita da EGS fora do royalty (**novo**) | Documento de terceiros que diz ter lido a EULA em 2026-09-05: "**Epic Games Store sales are excluded from Royalty Revenue entirely**"; "A 3.5% tier exists (EULA update 20)"; "The first $1,000,000 in lifetime gross revenue for each Royalty Product is excluded"; a exclusão trimestral abaixo de US$ 10.000 é um "cliff". | H [pista] | acrescentada nesta verificação | [pista] [austintheriot/dotfiles game-engines.md](https://github.com/austintheriot/dotfiles/blob/HEAD/.claude/rules/game-engines.md) | EULA completa |

### 2.5 Unity 6

| ID | Tópico | Afirmação (versão verificada) | Nível | Status | Fonte(s) | Como confirmar (fonte original) |
|---|---|---|---|---|---|---|
| UY-01 | Versões atuais | Datas dos commits das tags no UnityCsReference (**data do commit do código de referência, não data oficial de release**): `6000.7.0b2` 2026-09-23; `6000.6.3f1` 2026-09-24; `6000.6.0f1` 2026-08-31; `6000.5.11f1` 2026-09-02; `6000.5.0f1` 2026-06-15; `6000.4.12f1` 2026-06-17; `6000.4.0f1` 2026-03-18; `6000.3.25f1` 2026-09-24; `6000.3.0f1` 2025-12-03; `6000.0.84f1` 2026-09-16. Pelo `git ls-remote`, essas são as maiores tags de cada linha. | E2 | sustentada | [UnityCsReference tags](https://github.com/Unity-Technologies/UnityCsReference/tags) | [unity.com/releases/editor/archive](https://unity.com/releases/editor/archive) (bloqueado) |
| UY-02 | LTS e nomenclatura | O README do arfoundation-samples traz "Unity 6.3 LTS (6000.3)" e "Unity 6.0 LTS (6000.0)". Na mesma tabela aparece "Unity 6.5 beta (6000.5)", que está desatualizado em relação a UY-01. Se o 6.6 é LTS: NÃO CONFIRMADO. | E2 | sustentada | [arfoundation-samples README](https://github.com/Unity-Technologies/arfoundation-samples/blob/main/README.md) | Página de releases da Unity |
| UY-03 | Runtime Fee | Arquivo HN: "[2024-09-12, 14:49:08] ... Unity is cancelling the runtime fee (unity.com/blog/unity-is-canceling-the-runtime-fee)". O productarena cita o blog da Unity palavra por palavra. O mesmo documento registra a alegação de reintrodução (HN 44973269, 2025-08-21) e diz que a página Industry "contains NO 'runtime fee'/'per-install' wording" (verificado em 2026-09-15). | E3; productarena = [pista] | sustentada | [kherrick/hacker-news 2024-09-12](https://github.com/kherrick/hacker-news/blob/HEAD/archives/2024/2024-09-12/index.md); [pista] [productarena](https://github.com/ultrametricai/productarena/blob/HEAD/.pa-tmp/research-game-engines.md) | [Blog Unity](https://unity.com/blog/unity-is-canceling-the-runtime-fee); [unity.com/pricing](https://unity.com/pricing) |
| UY-04 | Preços | "Unity pricing verified at unity.com/pricing (Personal free below $200K; Pro $210/month or $2,310/year; 6.3 LTS)", segundo verificação de terceiro em 2026-09-05. Outra pista cita 80.lv sobre um aumento de 5% em Pro/Enterprise para 2026. | H [pista] | sustentada (pista) | [pista] [austintheriot/dotfiles](https://github.com/austintheriot/dotfiles/blob/HEAD/.claude/rules/game-engines.md); [pista] [best-engine app.js](https://github.com/Almas-ultra-net/best-engine/blob/HEAD/src/app.js) | [unity.com/pricing](https://unity.com/pricing) |
| UY-05 | Netcode for GameObjects | CHANGELOG: "## [2.13.3] - 2026-09-14"; o `package.json` da tag exige `"unity": "6000.0"`. README: "Windows, MacOS, and Linux", "iOS and Android", "Most closed platforms, such as consoles". O CHANGELOG cita "distributed authority" em 44 linhas. Branch `develop-3.x.x`: `"version": "3.0.1"`, `"unity": "6000.7"`. | E2 | sustentada | [CHANGELOG v2.13.3](https://github.com/Unity-Technologies/com.unity.netcode.gameobjects/blob/v2.13.3/com.unity.netcode.gameobjects/CHANGELOG.md); [README](https://github.com/Unity-Technologies/com.unity.netcode.gameobjects/blob/develop-2.0.0/README.md); [package.json develop-3.x.x](https://github.com/Unity-Technologies/com.unity.netcode.gameobjects/blob/develop-3.x.x/com.unity.netcode.gameobjects/package.json) | Predição/rollback de física de veículos no NGO: NÃO CONFIRMADO. |
| UY-06 | Netcode for Entities / DOTS | `manifest.json` do NetcodeSamples: `com.unity.netcode` 1.12.0, `com.unity.entities` 1.4.4, `com.unity.physics` 1.4.4. `ProjectVersion.txt`: 6000.3.9f1. O README raiz diz "use Unity 6.2". | E2 | sustentada (ver D-07) | [manifest.json](https://github.com/Unity-Technologies/EntityComponentSystemSamples/blob/master/NetcodeSamples/Packages/manifest.json); [ProjectVersion.txt](https://github.com/Unity-Technologies/EntityComponentSystemSamples/blob/master/NetcodeSamples/ProjectSettings/ProjectVersion.txt); [README](https://github.com/Unity-Technologies/EntityComponentSystemSamples/blob/master/README.md) | Documentação do Netcode for Entities |
| UY-07 | Split-screen | `PlayerInputManager.cs` tem `public bool splitScreen`, `splitScreenArea` e `JoinPlayer(int playerIndex = -1, int splitScreenIndex = -1, ...)`. | E2 | sustentada | [PlayerInputManager.cs](https://github.com/Unity-Technologies/InputSystem/blob/develop/Packages/com.unity.inputsystem/InputSystem/Runtime/Plugins/PlayerInput/PlayerInputManager.cs) | Manual do Input System |
| UY-08 | WheelCollider | `Modules/PhysicsEditor/WheelColliderEditor.cs` existe na tag `6000.6.3f1` (`[CustomEditor(typeof(WheelCollider))]`). Comportamento, limitações e backend de física (PhysX, versão): NÃO CONFIRMADOS. | E2 | sustentada | [WheelColliderEditor.cs @6000.6.3f1](https://github.com/Unity-Technologies/UnityCsReference/blob/6000.6.3f1/Modules/PhysicsEditor/WheelColliderEditor.cs) | Manual Unity (WheelCollider, Physics) |
| UY-09 | Plugin oficial / MCP / CLI | `unity-agent-plugin`: criado em 2026-08-06T14:55:01Z; "Unity's official game development plugin"; "Available for **Claude Code** and **Codex**"; versão exibida `0.1.6-beta`; "Works with: Unity 6+". A Unity CLI está em beta (CHANGELOG: "CLI `1.0.0-beta.10` (2026-09-14)"; instalação com `UNITY_CLI_CHANNEL=beta`). `unity mcp`: "starts a Model Context Protocol server, built into the `unity` binary"; stdio; `mcp configure` com "16 clients". `unity command eval` executa C# no editor vivo. Exige `com.unity.pipeline` "(Unity 6.0+)". O repositório `Unity-Technologies/skills` foi criado em 2026-05-05T09:18:23Z. | E2 | sustentada | [README](https://github.com/Unity-Technologies/unity-agent-plugin); [integration-advanced.md](https://github.com/Unity-Technologies/unity-agent-plugin/blob/main/skills/unity-cli/references/integration-advanced.md); [CHANGELOG](https://github.com/Unity-Technologies/unity-agent-plugin/blob/main/skills/unity-cli/CHANGELOG.md); [unity-cli SKILL.md](https://github.com/Unity-Technologies/unity-agent-plugin/blob/main/skills/unity-cli/SKILL.md); [Unity-Technologies/skills](https://github.com/Unity-Technologies/skills) | [docs.unity.com/en-us/unity-cli](https://docs.unity.com/en-us/unity-cli) (bloqueado) |
| UY-10 | Testes/builds headless e licença | `unity test` "launches the editor's built-in test runner in batch mode (`-runTests -testPlatform <mode> -testResults <path> -testFilter <pattern>`)", gera relatório JUnit e aceita `--shard N/M`. `unity run ... -- -nographics` executa headless. Editor residente com `-batchmode` e sem `-quit`. "A resident Editor (headless or GUI) holds a license seat until it exits". CI usa `UNITY_SERVICE_ACCOUNT_ID`/`_SECRET`. Executável no Linux: `<editor>/Editor/Unity`. | E2 | sustentada | [build-run-test.md](https://github.com/Unity-Technologies/unity-agent-plugin/blob/main/skills/unity-cli/references/build-run-test.md); [integration-advanced.md](https://github.com/Unity-Technologies/unity-agent-plugin/blob/main/skills/unity-cli/references/integration-advanced.md); [SKILL.md](https://github.com/Unity-Technologies/unity-agent-plugin/blob/main/skills/unity-cli/SKILL.md) (variáveis de service account) | Documentação oficial da Unity CLI |
| UY-11 | Unity AI e plataformas | GamingOnLinux, 2026-05-05: "Unity has rolled out Unity AI in Open Beta". GamingOnLinux, 2026-03-11: "For GDC 2026, Unity revealed expanded official support **is coming** for Steam. This includes Native Linux, Steam Deck, Steam Machine and more." | E3 | sustentada com ressalva | [GOL 2026-05-05](https://www.gamingonlinux.com/2026/05/unity-ai-out-in-open-beta-to-give-developers-the-fabled-make-game-button) via [espelho](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/05/2026-05-05/https...www.gamingonlinux.com.article_rss.php_entries.json); [GOL 2026-03-11](https://www.gamingonlinux.com/2026/03/unity-announce-expanded-supported-for-steam-linux-steam-deck-and-steam-machine) via [espelho](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/03/2026-03-11/https...www.gamingonlinux.com.article_rss.php_entries.json) | Blog/press release da Unity |
| UY-12 | Built-in Render Pipeline | Os templates `com.unity.template.3d`/`2d` são do Built-in RP, "deprecated from Unity 6.5, gone in 6.7". A skill manda o agente usar os templates URP como padrão. | E2 | sustentada com ressalva | [unity-cli SKILL.md](https://github.com/Unity-Technologies/unity-agent-plugin/blob/main/skills/unity-cli/SKILL.md) | Release notes do Unity 6.5 e 6.7 |

### 2.6 Godot

| ID | Tópico | Afirmação (versão verificada) | Nível | Status | Fonte(s) | Como confirmar (fonte original) |
|---|---|---|---|---|---|---|
| GD-01 | Versões | `versions.yml` do site oficial: **4.7.2 stable em "18 August 2026"**; 4.7.1 em "14 July 2026"; 4.7 em "18 June 2026"; 4.8 com `flavor: "dev6"` em "15 September 2026". O artigo do 4.6 tem `date: 2026-01-26 17:00:00`. Phoronix, 2026-06-18: "Godot 4.7 is out today". | E2 (Phoronix E3) | sustentada | [versions.yml](https://github.com/godotengine/godot-website/blob/master/_data/versions.yml); [artigo 4.6](https://github.com/godotengine/godot-website/blob/master/collections/_article/godot-4-6-all-about-your-flow.md); [Phoronix](https://www.phoronix.com/news/Godot-4.7-Released) via [espelho](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/06/2026-06-18/https...www.phoronix.com.rss.php_entries.json) | [godotengine.org/download](https://godotengine.org/download/) (bloqueado) |
| GD-02 | Jolt Physics | Doc: "The Jolt physics engine was added as an alternative ... in 4.4"; "By default, new projects will use it"; a extensão está em "maintenance mode"; há propriedades de joints "not supported"; os nós de joint da extensão não existem no módulo. Features do 4.6: "remove the experimental label and make Jolt the default physics engine for all new 3D projects"; "Existing projects aren't affected". | E2 | sustentada | [features 4.6](https://github.com/godotengine/godot-website/blob/master/_data/release_4_6/features.yml); [using_jolt_physics.rst](https://github.com/godotengine/godot-docs/blob/master/tutorials/physics/using_jolt_physics.rst) | Doc estável 4.7 |
| GD-03 | VehicleBody3D | "It is based on the raycast vehicle system". "[b]Note:[/b] This class has known issues and isn't designed to provide realistic 3D vehicle physics. If you want advanced vehicle physics, you may have to write your own physics integration using [CharacterBody3D] or [RigidBody3D]." | E2 | sustentada | [VehicleBody3D.xml](https://github.com/godotengine/godot/blob/master/doc/classes/VehicleBody3D.xml) | Class reference 4.7 |
| GD-04 | Headless / CI | `--headless` = "--display-driver headless --audio-driver Dummy". A doc diz: "**required** on platforms that do not have GPU access (such as continuous integration)". Exportação: `godot --headless --export-release <preset> <path>`. Servidor dedicado: "run Godot with the `headless` ... argument, or running a project exported as dedicated server". Testes unitários: doctest, `scons tests=yes`, "export templates cannot be tested currently". | E2 | sustentada | [command_line_tutorial.rst](https://github.com/godotengine/godot-docs/blob/master/tutorials/editor/command_line_tutorial.rst); [exporting_for_dedicated_servers.rst](https://github.com/godotengine/godot-docs/blob/master/tutorials/export/exporting_for_dedicated_servers.rst); [unit_testing.rst](https://github.com/godotengine/godot-docs/blob/master/engine_details/architecture/unit_testing.rst) | Doc estável 4.7 |
| GD-05 | TSCN em texto | "TSCN files have the advantage of being mostly human-readable and easy for version control systems to manage". Godot 4.x usa `format=3`. | E2 | sustentada | [tscn.rst](https://github.com/godotengine/godot-docs/blob/master/engine_details/file_formats/tscn.rst) | — |
| GD-06 | Split-screen | Demo oficial 2D: `viewport_2.world_2d = viewport_1.world_2d`. `Viewport.xml` lista o tutorial "Dynamic Split Screen Demo" (asset 2806). Demo oficial de split-screen **3D com 4 jogadores**: NÃO CONFIRMADO. | E2 | sustentada | [game_splitscreen.gd](https://github.com/godotengine/godot-demo-projects/blob/master/2d/platformer/game_splitscreen.gd); [Viewport.xml](https://github.com/godotengine/godot/blob/master/doc/classes/Viewport.xml) | Asset Library 2806 |
| GD-07 | Rede | A API de alto nível "provides an implementation based on ENet (ENetMultiplayerPeer)", além de peers WebRTC e WebSocket. RPC `"authority"`: "The authority is the server by default, but can be changed per-node". As classes `MultiplayerSpawner`, `MultiplayerSynchronizer` e `SceneMultiplayer` existem em `modules/multiplayer/doc_classes`. Predição/rollback nativos: NÃO CONFIRMADO. | E2 | sustentada | [high_level_multiplayer.rst](https://github.com/godotengine/godot-docs/blob/master/tutorials/networking/high_level_multiplayer.rst); [MultiplayerSpawner.xml](https://github.com/godotengine/godot/blob/master/modules/multiplayer/doc_classes/MultiplayerSpawner.xml); [MultiplayerSynchronizer.xml](https://github.com/godotengine/godot/blob/master/modules/multiplayer/doc_classes/MultiplayerSynchronizer.xml); [SceneMultiplayer.xml](https://github.com/godotengine/godot/blob/master/modules/multiplayer/doc_classes/SceneMultiplayer.xml) | — |
| GD-08 | Consoles / W4 Games | Página de consoles: "the Godot Foundation does not maintain official console ports" (motivos: MIT e NDAs). Lista **8 provedores**. Texto: "W4 Games offers official middleware ports for Nintendo Switch, Xbox Series X/S, and PlayStation 5". Artigo de 2024-09-03: "the Godot Foundation does not have active plans to work on console platform ports". | E2 | sustentada (ver D-05) | [pages/consoles.html](https://github.com/godotengine/godot-website/blob/master/pages/consoles.html); [About Official Console Ports](https://github.com/godotengine/godot-website/blob/master/collections/_article/about-official-console-ports.md) | [godotengine.org/consoles](https://godotengine.org/consoles/) (bloqueado); site da W4 Games |
| GD-09 | W4 Games: financiamento | "With an extra $18 million raised, W4 Games plan to continue..." (título cita a Tencent), 2026-08-25. | E3 | sustentada | [GOL](https://www.gamingonlinux.com/2026/08/w4-games-the-company-formed-by-godot-engine-veterans-gets-help-and-funding-from-tencent) via [espelho](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/08/2026-08-25/https...www.gamingonlinux.com.article_rss.php_entries.json) | Comunicado da W4 Games |
| GD-10 | Política de IA para contribuições upstream | Artigo "Changes to our Contribution Policies" (2026-06-30). Diz que a política "will" ser alterada "Shortly" e passará a incluir: "**No autonomous AI agent use or vibe coding**" (isso "already leads to an auto-ban from our GitHub repository") e "No use of AI to generate substantial pieces of code". É uma política **de contribuição** aos repositórios do Godot. | E2 | sustentada com ressalva | [contribution-policy-2026.md](https://github.com/godotengine/godot-website/blob/master/collections/_article/contribution-policy-2026.md) | [contribution_rules](https://contributing.godotengine.org/en/latest/development/contribution_rules.html) (texto vigente, não lido) |
| GD-11 | Novidades 4.7 | Títulos oficiais incluem "HDR output support", "Enter the Asset Store", "`AreaLight3D`...", "New nearest-neighbor scaling option for viewports", "Offset transform of `Control` nodes", "Built-in virtual joystick" e "Add gyro aiming support". | E2 | sustentada | [features 4.7](https://github.com/godotengine/godot-website/blob/master/_data/release_4_7/features.yml) | — |
| GD-12 | Binários oficiais | O `SHA512-SUMS.txt` do release `4.7.2-stable` traz `9aa00f7a…9ed54c65  Godot_v4.7.2-stable_linux.x86_64.zip` e `1855960b…8402d13  Godot_v4.7.2-stable_mono_linux_x86_64.zip`. | E2 | sustentada | [godot-builds 4.7.2-stable](https://github.com/godotengine/godot-builds/releases/tag/4.7.2-stable) | — |

### 2.7 Outras engines

| ID | Tópico | Afirmação (versão verificada) | Nível | Status | Fonte(s) | Como confirmar (fonte original) |
|---|---|---|---|---|---|---|
| OT-01 | O3DE | A tag `2605.0` aponta para o commit de 2026-05-27T09:35:03-07:00. `LICENSE.txt`: "default license ... Apache License, Version 2.0 ... you may elect at your option to use ... under the MIT License". Phoronix, 2026-05-28: "Out this week is O3DE 26.05". | E2 (Phoronix E3) | sustentada (ver D-09) | [tag 2605.0](https://github.com/o3de/o3de/releases/tag/2605.0); [LICENSE.txt](https://github.com/o3de/o3de/blob/2605.0/LICENSE.txt); [Phoronix](https://www.phoronix.com/news/O3DE-26.04-Released) via [espelho](https://github.com/rumca-js/RSS-Link-Database-2026/blob/main/2026/05/2026-05-28/https...www.phoronix.com.rss.php_entries.json) | o3de.org (bloqueado) |
| OT-02 | Bevy | Índice do crates.io: `0.19.0`, `0.19.1` e `0.20.0-rc.1` (não yanked). Commits das tags: `v0.19.0` 2026-06-17T18:22:47-07:00; `v0.19.1` 2026-08-12T16:59:51-07:00. README: "still in the early stages of development. Important features are missing"; versão com breaking changes "approximately once every 3 months"; MIT/Apache-2.0. | E2 | sustentada | [crates.io index](https://index.crates.io/be/vy/bevy); [README](https://github.com/bevyengine/bevy/blob/main/README.md) | — |
| OT-03 | Stride | NuGet `stride.engine`: a maior versão estável é **4.3.0.2507** (publicada 2025-11-16T09:41Z); `4.4.0-beta8` publicada em 2026-09-21T17:09Z. | E2 | sustentada (ver D-10) | [NuGet registration](https://api.nuget.org/v3/registration5-gz-semver2/stride.engine/index.json) | — |
| OT-04 | Flax | A tag `1.12.6912` aponta para o commit de 2026-05-13T22:40:54+02:00. README: "full source code ... (excluding NDA-protected platforms support)"; "Using Flax source code is strictly governed by the Flax Engine End User License Agreement". | E2 | sustentada | [FlaxEngine README](https://github.com/FlaxEngine/FlaxEngine/blob/master/README.md) | [flaxengine.com/licensing](https://flaxengine.com/licensing/) (não lido). Pista sem verificação: [austintheriot](https://github.com/austintheriot/dotfiles/blob/HEAD/.claude/rules/game-engines.md) cita "4% royalty above $250,000 per calendar quarter". |

### 2.8 Ambiente desta sessão (nuvem, sem GPU)

| ID | Tópico | Afirmação (versão verificada) | Nível | Status | Fonte(s) | Como confirmar (fonte original) |
|---|---|---|---|---|---|---|
| ENV-01 | Godot headless e render por CPU | A doc prevê `--headless` sem GPU (GD-04). **Reproduzido de forma independente em 2026-09-27**, com projeto próprio desta verificação. O SHA-512 do zip é idêntico ao oficial (`9aa00f7a…`). `--headless --version` retornou `4.7.2.stable.official.ed1daf0bf`. Um `VehicleBody3D` com 4 `VehicleWheel3D` acelerou, e 4 `SubViewport` compartilharam o `world_3d`. 300 ticks de física levaram **5,2 s** reais. A velocidade final (2,5 m/s aqui, 14,6 m/s no teste do produtor) depende dos parâmetros e **não é comparável**. Com `xvfb-run` + Mesa **llvmpipe**, foi gerado um PNG 640×360 com grade 2×2 em `opengl3/gl_compatibility` (OpenGL 4.5, Mesa 25.2.8) e em `vulkan/forward_plus` (Vulkan 1.4.318, llvmpipe). | E2 (doc) + observação direta reproduzida | sustentada | [command_line_tutorial.rst](https://github.com/godotengine/godot-docs/blob/master/tutorials/editor/command_line_tutorial.rst); [godot-builds 4.7.2-stable](https://github.com/godotengine/godot-builds/releases/tag/4.7.2-stable) | Desempenho e fidelidade visual do render por CPU × GPU real: NÃO medidos. `physics/3d/physics_engine` apareceu como `DEFAULT`; qual servidor de física isso resolve continua NÃO CONFIRMADO. |

**Fatos do container observados nesta verificação:** 4 vCPU, 15 GiB de RAM, disco `/dev/vda` 252 GB com **25 GB livres** (o produtor registrou 29 GB), sem `/dev/dri` e sem `nvidia-smi`.

---

## 3. Divergências entre fontes

Nenhum lado foi escolhido.

| ID | Tópico | Lado A | Lado B | Observação |
|---|---|---|---|---|
| D-01 | Data de lançamento do UE 5.8 | **17/06/2026**: vídeo oficial do State of Unreal ("released Unreal Engine 5.8", via espelho); [Masterofowls](https://github.com/Masterofowls/Unreal_Files/blob/HEAD/Docs/UE58_Guide.md); [JsizzleR](https://github.com/JsizzleR/mobile-forces-2027/blob/HEAD/docs/archive/v0.1-network-plan/docs/research/UNREAL-AUTOMATION.md) (anúncio do fórum "dated June 17, 2026") | **23/06/2026**: [austintheriot](https://github.com/austintheriot/dotfiles/blob/HEAD/.claude/rules/game-engines.md) ("stable is 5.8 (released 2026-06-23)") [pista] | **Nova.** O produtor disse "Nenhuma divergência de data encontrada". O clipe oficial "Unreal Engine 5.8 Is Now Available" foi publicado em 23/06, e isso pode explicar a confusão. **Não foi escolhido lado.** |
| D-02 | 5.8 é o último UE5? | Looman: "final release before Epic Games is moving development efforts to Unreal Engine 6"; austintheriot: "there is no 5.9" | swil-news: "with the option to ship 5.9 if needed" | Nenhuma fonte oficial lida. |
| D-03 | Cronograma do UE6 | swil-news citando OC3D: "late-2027 Early Access, mid-2029 full release" | austintheriot: "early access targeted around the end of 2027 and full release around 2029" (no changelog: "UE6 targeting roughly 2029") | **Correção:** os dois lados **convergem** (EA no fim de 2027, versão completa em ~2029). Só a precisão muda ("mid-2029" × "around 2029"). Não há fonte oficial. |
| D-04 | Status do Iris no UE 5.8 | "Production Ready": unreal-sidekick (sem fontes, `verified: no`), ImChong, scenario-labs ("for licensees", replicação genérica continua padrão) | "Experimental": ue-is-renderer ("still Experimental in 5.7/5.8") | Looman não informa o status. |
| D-05 | W4 Games: plataformas | Texto da página oficial: Switch, Xbox Series X/S, PS5 (3) | Dados da mesma página: `switch`, `switch-2`, `xbox-series`, `playstation-5` (4) | Mesma fonte, inconsistência interna. |
| D-06 | Unity Runtime Fee | Cancelado em set/2024 (HN; blog da Unity citado pelo productarena) | HN 44973269 (2025-08-21) alega reintrodução pela licença Industry | O productarena diz que a página Industry não tinha esse texto em 2026-09-15. A captura "mywiki" com data 2025-01-01 **não foi verificada** (sem URL). |
| D-07 | Versão dos samples DOTS | README raiz: "use Unity 6.2" | `ProjectVersion.txt` do NetcodeSamples: `6000.3.9f1` | Mesmo repositório. |
| D-08 | MCP oficial da Unity | Pista [frederico-kluser](https://github.com/frederico-kluser/unity-gamedev-agent-skill/blob/HEAD/README.md): relay do `com.unity.ai.assistant` "DEPRECATED (doc 2.18.0-pre.2, 2026-08-18)" em favor de `unity mcp` | A documentação oficial lida (unity-agent-plugin) aponta para a Unity CLI e **não menciona** a deprecação | Confirmar na doc do `com.unity.ai.assistant`. |
| D-09 | O3DE 26.05 | URL da Phoronix: `O3DE-26.04-Released` | Título e texto: "O3DE 26.05" | A tag oficial é `2605.0`. |
| D-10 | Stride: "última estável" | Maior versão estável: `4.3.0.2507` (2025-11-16) | Estável publicada por último: `4.2.1.2487` (**2025-12-02**, manutenção da linha 4.2) | **Nova.** Os dois critérios dão respostas diferentes. |
| D-11 | README AR Foundation × tags Unity | README: "Unity 6.5 beta (6000.5)" | UnityCsReference: `6000.5.0f1` (2026-06-15) até `6000.5.11f1` | O README está desatualizado. |

---

## 4. O que a verificação mudou (resumo das ressalvas)

| ID | Mudança |
|---|---|
| UE-02 | Saiu a nota "Nenhuma divergência de data encontrada" (ver D-01). As pistas "davidbuenov/ai-courses-catalog" e "DreamLab-AI/Vitrine" foram citadas **sem URL** e não foram verificadas. |
| UE-04 | Entrou uma pista nova de data do 5.8.2 (25/08/2026, JsizzleR). Continua H. |
| UE-05 | Entrou a URL da sessão "From Words to Worlds" (lDf_y-YPELo), que não tinha sido citada. |
| UE-09 / UE-04 | O post do vorixo foi lido na **fonte Markdown** no GitHub (o site está bloqueado). |
| UE-12 | Saiu "backends ... standalone": as fontes citadas não dizem isso. |
| UE-15 | A divergência do cronograma do UE6 foi corrigida para convergência (D-03). |
| UE-17 | **Rebaixada de E3 para H.** As fontes são um post de fórum e um documento de terceiros, não "várias fontes secundárias independentes". Saiu "isenção de royalty sobre vendas na EGS", que não está nas fontes citadas; o tema foi para N-02 com outra fonte. |
| UE-20 | Saiu "amplamente usada": a fonte não diz isso. |
| UY-10 | Entrou `SKILL.md` como fonte das variáveis de service account. |
| UY-11 | O suporte ampliado a Steam/Linux foi **anunciado como futuro** ("is coming"). |
| UY-12 | "Padrão de novos projetos é URP" virou "a skill manda o agente usar os templates URP como padrão". |
| GD-10 | O artigo de 30/06/2026 **anuncia** a mudança ("Shortly ... will include"). O uso de agente autônomo já leva a banimento. O trecho "não para jogos feitos com Godot" saiu como afirmação da fonte: é inferência pelo escopo (política de contribuição). |
| N-01, N-02, N-03 | Novos itens, com URL. N-03 é E2; N-01 e N-02 são H. |

---

## 5. Lacunas

### 5.1 O que só o jogo / arquivo original pode responder

Estas perguntas definem **quais requisitos** a engine precisa cumprir no Modo Clássico. Nenhuma fonte pública lida aqui responde a elas, e **não devem ser presumidas**:

- **Modelo de física dos veículos** do original: aceleração, derrapagem, colisão entre karts e com a pista, pulos, atrito por superfície. Isso decide se `VehicleBody3D` (raycast), `WheelCollider`, Chaos Vehicles ou física própria servem. NÃO CONFIRMADO.
- **Taxa de quadros e tick de simulação** do original em NTSC e PAL, e se a física depende do framerate. NÃO CONFIRMADO.
- **Split-screen do original:** existe? Com quantos jogadores e com que layout? Há divergência pública (1 × 2 jogadores; ver D-03 em [tecnico_versoes.md](tecnico_versoes.md)). Isso afeta o requisito de split-screen local. NÃO CONFIRMADO.
- **Câmera** (distância, FOV, comportamento em curvas e colisões), **resolução interna** e **proporção de tela**. NÃO CONFIRMADO.
- **Escala e tamanho das pistas**, número de corredores por corrida e comportamento da IA dos oponentes. NÃO CONFIRMADO.
- **Formatos de dados** (DAT/RAW/AXE/MDL): o que pode ser importado e medido para comparar com a reconstrução. Só é possível com a cópia do proprietário.

### 5.2 Lacunas de fontes oficiais (não dependem do jogo)

- **Release notes oficiais do UE 5.8** (dev.epicgames.com) não foram lidas por causa do bloqueio de egress. Falta confirmar lá o status (Experimental/Beta/Production) de Chaos Vehicles, Chaos Modular Vehicles, Mover, Network Prediction, Iris, física em rede e do plugin MCP.
- **UE:** suporte nativo a split-screen local (2, 3 ou 4 jogadores): nenhuma URL lida. Investigar na doc oficial.
- **UE:** status do Gauntlet, da API Python do editor e de commandlets no 5.8: nenhuma URL lida.
- **UE:** se o plugin MCP funciona com editor sem GPU (`-NullRHI`/`-RenderOffscreen`) em Linux: NÃO CONFIRMADO.
- **UE:** datas e número dos hotfixes 5.8.x. Só há pistas (UE-04).
- **UE:** EULA completa e termos de consoles (PS5, Switch 2, Xbox). Ler unrealengine.com/eula.
- **UE:** requisitos oficiais de hardware/GPU de Lumen, Nanite e MegaLights, e se funcionam com rasterização por CPU (lavapipe/WARP).
- **UE:** não foi possível obter binários nesta sessão (fonte gated no GitHub, launcher/CDN bloqueados). Execução headless neste container: **não testada**. Pela pista UE-20, o build em contêiner exige ≥800 GB, e há 25 GB livres.
- **Unity:** datas oficiais de lançamento do 6.4, 6.5 e 6.6 (UY-01 traz datas de commit). Não se sabe se o 6.6 é LTS.
- **Unity:** preços e termos atuais (unity.com/pricing) e status do Runtime Fee na licença Industry.
- **Unity:** comportamento e limitações do `WheelCollider`; backend e versão do PhysX.
- **Unity:** predição/rollback de física no NGO e no Netcode for Entities, e limite de jogadores por sessão, para uma meta de 12 a 16 jogadores.
- **Unity:** status do MCP do `com.unity.ai.assistant` (D-08).
- **Unity:** não testada nesta sessão (CDN da Unity CLI bloqueada, daemon Docker parado, ativação de licença exigida).
- **Godot:** predição/rollback nativos no multiplayer. Addons comunitários (ex.: netfox) não foram consultados.
- **Godot:** demo oficial de split-screen 3D, e custo de 4 `SubViewport` 3D em hardware-alvo (precisa de benchmark com GPU real).
- **Godot:** preços e termos da W4 Games para consoles; data do 4.8 estável.
- **Godot:** qual servidor de física roda com `physics_engine = DEFAULT` sem configuração no `project.godot` (ENV-01).
- **O3DE, Bevy, Stride, Flax:** física de veículos, split-screen, rede e consoles não foram investigados. Termos de royalty da Flax: só pista.

---

## 6. Afirmações rejeitadas

**Nenhuma afirmação foi rejeitada inteira.** Os trechos abaixo saíram do corpo porque a fonte citada não os sustenta:

| ID | Trecho retirado | Motivo |
|---|---|---|
| UE-02 (nota de conflito) | "Nenhuma divergência de data encontrada." | Uma pista lida nesta verificação ([austintheriot](https://github.com/austintheriot/dotfiles/blob/HEAD/.claude/rules/game-engines.md)) dá 2026-06-23 (D-01). |
| UE-02 (nota de conflito) | Convergência atribuída a "davidbuenov/ai-courses-catalog" e "DreamLab-AI/Vitrine" | Citadas sem URL; não verificadas. |
| UE-12 | "...com backends Network Prediction, física em rede do Chaos (ChaosMover) **ou standalone**" | "standalone" não aparece nas fontes citadas (scenario-labs, mcp-unreal). O resto continua como pista. |
| UE-15 (nota de conflito) | "outra pista (austintheriot) diz 'UE6 targeting roughly 2029'" como divergência | O mesmo arquivo diz "early access ... end of 2027 and full release around 2029", o que converge com OC3D. Corrigido em D-03. |
| UE-17 | "Várias fontes secundárias independentes" e nível E3 | As fontes são um post de fórum (captura r/Games) e um documento de terceiros. O nível passou para H [pista]. |
| UE-17 | "...e isenção de royalty sobre vendas na EGS" | Não está nas duas fontes citadas. Tema movido para N-02 (outra fonte, H). |
| UE-20 | "Ferramenta comunitária **amplamente usada**" | A fonte não diz isso. |
| UY-11 | "anunciou suporte oficial ampliado" (no presente) | A fonte diz que o suporte "is coming" (futuro). |
| UY-12 | "padrão de novos projetos é URP" (como padrão da Unity) | A fonte é uma instrução da skill ao agente ("Default to the URP templates"), não uma afirmação sobre o padrão do editor. |
| GD-10 | "Desde 2026-06-30, a política ... proíbe" | O artigo de 2026-06-30 diz que a política **será** alterada "Shortly". Só o uso de agente autônomo já leva a banimento. |
| GD-10 | "Isso vale para contribuições à engine, não para jogos feitos com Godot" (como afirmação da fonte) | A fonte não diz isso explicitamente. É inferência pelo fato de ser uma política de contribuição. |

---

## 7. Fontes consultadas

**Projeto**
- [docs/PROMPT_MASTER.md](../../docs/PROMPT_MASTER.md) (seções 0, 10, 12 a 15, 56 e 70)
- [LegacyReference/research/tecnico_versoes.md](tecnico_versoes.md) (divergência de número de jogadores)

**Epic Games / Unreal (repositórios oficiais, E2)**
- [EpicGames/PixelStreamingInfrastructure, branch UE5.8, DEVELOPING.md](https://github.com/EpicGames/PixelStreamingInfrastructure/blob/UE5.8/DEVELOPING.md) e [tag UE5.8-0.1.0](https://github.com/EpicGames/PixelStreamingInfrastructure/tree/UE5.8-0.1.0)
- [npm @epicgames-ps/lib-pixelstreamingfrontend-ue5.8](https://registry.npmjs.org/@epicgames-ps/lib-pixelstreamingfrontend-ue5.8)
- [EpicGames/unreal-engine-skills-for-claude-code-plugin](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin): README, [setup.md](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin/blob/main/skills/unreal-mcp/references/setup.md), [create-toolset SKILL.md](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin/blob/main/skills/create-toolset/SKILL.md), [plugin.json](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin/blob/main/.claude-plugin/plugin.json)
- [EpicGames/.github profile README](https://github.com/EpicGames/.github/blob/main/profile/README.md)
- [EpicGames/lore](https://github.com/EpicGames/lore)

**Textos oficiais lidos por espelho RSS de terceiros (E3)**
- Canal YouTube Unreal Engine, via [rumca-js/RSS-Link-Database-2026](https://github.com/rumca-js/RSS-Link-Database-2026): dias 2026-06-17, 06-23, 06-24, 08-03, 08-08, 08-18 e 09-07 (links nas tabelas)
- Phoronix (2026-05-28, 06-17, 06-18) e GamingOnLinux (2026-03-11, 05-05, 05-13, 08-25), pelo mesmo espelho
- [Captura r/Games 2025-01-01 (RSS-Link-Database-2025)](https://github.com/rumca-js/RSS-Link-Database-2025/blob/HEAD/2025/01/2025-01-01/https...www.reddit.com.r.Games..rss_entries.md) [pista]

**Especialistas (E3)**
- [Tom Looman: UE 5.8 Performance Highlights (fonte .md)](https://github.com/tomlooman/tomlooman.github.io/blob/main/_posts/2026-08-05-unreal-engine-5-8-performance-highlights.md)
- [vorixo: Networked Physics ... UE 5.8 (fonte .md)](https://github.com/vorixo/devtricks/blob/master/_posts/2024-05-04-phys-prediction-use.md) ([página](https://vorixo.github.io/devtricks/phys-prediction-use/) bloqueada)
- [vorixo/ExperimentalArcadeVehicleSampleProject](https://github.com/vorixo/ExperimentalArcadeVehicleSampleProject)
- [adamrehn/ue4-docker configuring-linux.adoc](https://github.com/adamrehn/ue4-docker/blob/HEAD/docs/configuring-linux.adoc)

**Pistas (H)**
- [the-machine-herald (artigo gerado por IA)](https://github.com/the-machine-herald/machineherald.io/blob/HEAD/src/content/articles/2026-05/22-unreal-engine-58-preview-arrives-with-mesh-terrain-metahuman-crowds-and-a-new-lumen-performance-mode.md)
- [Masterofowls/Unreal_Files UE58_Guide.md](https://github.com/Masterofowls/Unreal_Files/blob/HEAD/Docs/UE58_Guide.md)
- [JsizzleR/mobile-forces-2027 UNREAL-AUTOMATION.md](https://github.com/JsizzleR/mobile-forces-2027/blob/HEAD/docs/archive/v0.1-network-plan/docs/research/UNREAL-AUTOMATION.md)
- [ImChong/Robotics_Notebooks](https://github.com/ImChong/Robotics_Notebooks/blob/HEAD/sources/sites/unreal-engine-5-8-docs.md)
- [barrozo3d/unreal-sidekick](https://github.com/barrozo3d/unreal-sidekick/blob/HEAD/references/release-notes-ue58.md)
- [scenario-labs/skills SKILL.md](https://github.com/scenario-labs/skills/blob/HEAD/skills/game-engines/unreal/scenario-unreal-gameplay/SKILL.md) e [procedures.md](https://github.com/scenario-labs/skills/blob/HEAD/skills/game-engines/unreal/scenario-unreal-gameplay/references/procedures.md)
- [baadc0de/ue-is-renderer evaluation.md](https://github.com/baadc0de/ue-is-renderer/blob/HEAD/docs/evaluation.md)
- [HTRMC/mcp-unreal incomplete.txt](https://github.com/HTRMC/mcp-unreal/blob/HEAD/incomplete.txt)
- [Supwils/swil-news digest 2026-06-17](https://github.com/Supwils/swil-news/blob/HEAD/NEWS/gaming/en/2026-06-17_gaming-digest.md)
- [r-melvin/krakow-1795 UNREAL_SPIKE.md](https://github.com/r-melvin/krakow-1795/blob/HEAD/docs/UNREAL_SPIKE.md)
- [austintheriot/dotfiles game-engines.md](https://github.com/austintheriot/dotfiles/blob/HEAD/.claude/rules/game-engines.md)
- [Almas-ultra-net/best-engine app.js](https://github.com/Almas-ultra-net/best-engine/blob/HEAD/src/app.js)
- [ultrametricai/productarena](https://github.com/ultrametricai/productarena/blob/HEAD/.pa-tmp/research-game-engines.md)
- [kherrick/hacker-news 2024-09-12](https://github.com/kherrick/hacker-news/blob/HEAD/archives/2024/2024-09-12/index.md)
- [frederico-kluser/unity-gamedev-agent-skill](https://github.com/frederico-kluser/unity-gamedev-agent-skill/blob/HEAD/README.md)

**Unity (repositórios oficiais, E2)**
- [UnityCsReference (tags)](https://github.com/Unity-Technologies/UnityCsReference/tags) e [WheelColliderEditor.cs @6000.6.3f1](https://github.com/Unity-Technologies/UnityCsReference/blob/6000.6.3f1/Modules/PhysicsEditor/WheelColliderEditor.cs)
- [arfoundation-samples README](https://github.com/Unity-Technologies/arfoundation-samples/blob/main/README.md)
- [com.unity.netcode.gameobjects](https://github.com/Unity-Technologies/com.unity.netcode.gameobjects) (CHANGELOG v2.13.3, README develop-2.0.0, package.json develop-3.x.x)
- [EntityComponentSystemSamples](https://github.com/Unity-Technologies/EntityComponentSystemSamples) (NetcodeSamples manifest.json, ProjectVersion.txt, README)
- [InputSystem PlayerInputManager.cs](https://github.com/Unity-Technologies/InputSystem/blob/develop/Packages/com.unity.inputsystem/InputSystem/Runtime/Plugins/PlayerInput/PlayerInputManager.cs)
- [unity-agent-plugin](https://github.com/Unity-Technologies/unity-agent-plugin) (README, unity-cli SKILL.md, CHANGELOG, integration-advanced.md, build-run-test.md) e [Unity-Technologies/skills](https://github.com/Unity-Technologies/skills)

**Godot (repositórios oficiais, E2)**
- [godot-website](https://github.com/godotengine/godot-website): `_data/versions.yml`, `release_4_6/features.yml`, `release_4_7/features.yml`, `pages/consoles.html`, artigos do 4.6, "About Official Console Ports" e "contribution-policy-2026"
- [godot-docs](https://github.com/godotengine/godot-docs): using_jolt_physics, command_line_tutorial, exporting_for_dedicated_servers, unit_testing, tscn, high_level_multiplayer
- [godot](https://github.com/godotengine/godot): `doc/classes/VehicleBody3D.xml`, `Viewport.xml`, `modules/multiplayer/doc_classes/*.xml`
- [godot-demo-projects game_splitscreen.gd](https://github.com/godotengine/godot-demo-projects/blob/master/2d/platformer/game_splitscreen.gd)
- [godot-builds 4.7.2-stable (SHA512-SUMS.txt)](https://github.com/godotengine/godot-builds/releases/tag/4.7.2-stable)

**Outras engines (E2)**
- [o3de/o3de tag 2605.0 e LICENSE.txt](https://github.com/o3de/o3de/blob/2605.0/LICENSE.txt)
- [bevyengine/bevy README](https://github.com/bevyengine/bevy/blob/main/README.md) e [índice crates.io](https://index.crates.io/be/vy/bevy)
- [NuGet stride.engine](https://api.nuget.org/v3/registration5-gz-semver2/stride.engine/index.json)
- [FlaxEngine README](https://github.com/FlaxEngine/FlaxEngine/blob/master/README.md)

**Tentadas e bloqueadas nesta verificação:** youtube.com, vorixo.github.io, godotengine.org (WebFetch `EGRESS_BLOCKED`); dev.epicgames.com, unrealengine.com, unity.com, phoronix.com, gamingonlinux.com, reddit.com, x.com, news.ycombinator.com, tomlooman.com (curl sem resposta); endpoints de repositório da api.github.com (fora da sessão); WebSearch (cota 200/200).
