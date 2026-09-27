# Fontes primárias (E2)

- **Data:** 2026-09-27
- **Dimensão:** fontes primárias (E2): manuais, material oficial, identificação da mídia, datas, classificação etária e recepção contemporânea (versões PlayStation e Game Boy Color)
- **Papel deste documento:** verificação adversarial independente das 27 afirmações (E2P-001 a E2P-027) levantadas por outro agente de pesquisa.

> **Pesquisa pública — PISTAS DE INVESTIGAÇÃO, não prova. Nada aqui é E1.**
>
> Nenhuma fonte primária (E2) foi lida nesta rodada. Nenhuma linha deste arquivo pode virar implementação do Modo Clássico (Prompt Master, seções 0, 13, 14 e 56). O jogo original e o material original têm precedência sobre tudo o que está aqui.

---

## Método

### O que foi tentado

1. **Leitura direta das URLs citadas.** As 24 URLs que aparecem nas afirmações foram testadas, 21 pelo WebFetch e 3 pelo `curl`. **Nenhuma abriu**: os 19 hosts envolvidos responderam `EGRESS_BLOCKED` ou `CONNECT 403` no proxy de saída do ambiente. A lista completa está na seção 6.
2. **Outros hosts úteis** (redump.org, esrb.org, usk.de, pegi.info, web.archive.org, activision.com, igdb.com, giantbomb.com e buscadores) também deram `CONNECT 403`.
3. **Busca na web (WebSearch):** indisponível. A cota da sessão (200/200) já estava esgotada.
4. **Nenhum contorno:** não foram usados espelhos, leitores ou tradutores de terceiros para chegar a páginas bloqueadas. Isso seria contornar a política de rede.

### Via que funcionou

Só a infraestrutura do GitHub respondeu (`raw.githubusercontent.com`). Por ela foram lidos **arquivos de texto com metadados**: nomes, seriais, tamanhos e hashes. Nenhum dado de jogo foi baixado. As cópias ficaram só no scratchpad da sessão, fora do repositório. Os links apontam para commits fixos:

| Base | O que é | Commit / versão |
|---|---|---|
| [DAT Redump de PlayStation (espelho libretro)][redump-dat] | Conversão da base Redump.org feita pelo projeto libretro-dats. Cabeçalho `version "2026.08.01"` | libretro-database `d5bae90` |
| [Metadados PS derivados do psxdatacenter][psxdc-snap] | Conversão dos dados do psxdatacenter. Cabeçalho `version "2020.3.19"`, homepage `robloach/libretro-database-psxdatacenter` | libretro-database `d5bae90` |
| [DAT No-Intro de Game Boy Color][nointro-gbc] e metadados GBC ([dev][gbc-dev], [pub][gbc-pub], [ano][gbc-year], [mês][gbc-month], [serial][gbc-serial], [jogadores][gbc-users]) | Conversão da base No-Intro, mais metadados comunitários sem fonte por entrada | libretro-database `d5bae90` |
| [gamedb.yaml do DuckStation][duck] | Base de compatibilidade de um emulador de PS1, com metadados por serial | duckstation `a2edf2d` |

### Auditoria interna

Cada afirmação foi comparada, frase por frase, com o trecho que o próprio produtor apresentou no campo `quote`. Esses trechos são **resumos do mecanismo de busca, não citações literais**, e o produtor avisou disso. Quando um detalhe da afirmação **não aparece em nenhum trecho apresentado**, ele saiu do corpo e foi para a seção 5 (Afirmações rejeitadas). A rejeição é **provisória**: o detalhe volta quando a fonte for lida e confirmar.

### Regras de nível aplicadas

- Fonte citada inacessível → **H / NÃO CONFIRMADO** (regra do coordenador), mesmo quando o produtor propôs E3. O nível proposto aparece na coluna de status.
- Espelho de base séria (Redump, No-Intro) lido → **E3**.
- Conversão de 2020 dos dados do psxdatacenter → **E3 (derivado)**. A página atual do psxdatacenter não foi lida.
- Base de emulador ou comunitária sem fonte por entrada (gamedb do DuckStation, metadados GBC do libretro) → **H (pista)**.
- Wiki, fandom, fórum, guia de usuário, TV Tropes e anúncio de varejo → **no máximo pista (H)**.
- **Nenhuma afirmação é E1 nem E2.**

### Legenda de status

| Status | Significado |
|---|---|
| **sustentada** | A fonte citada foi lida e diz isso. *Nenhuma afirmação chegou a este status: nenhuma URL citada abriu.* |
| **sustentada por fonte alternativa** | A URL citada não abriu, mas outra fonte lida (com URL) diz o mesmo. |
| **fonte inacessível** | A fonte não abriu e o conteúdo só existe nos resumos de busca do produtor. Fica como H. |
| **fonte inacessível + parcial** | Idem, e parte do texto foi retirada por falta de trecho de apoio (seção 5). |
| **divergente** | Uma fonte lida diz outra coisa. As duas versões ficam registradas, sem escolher lado (seção 3). |
| **não sustentada** | A fonte diz outra coisa. Removida do corpo (seção 5). |

---

## 1. Resumo

- Foram verificadas **27 afirmações**. **Nenhuma das 24 URLs citadas abriu**, e nenhuma fonte primária (E2) foi lida. Os dois manuais localizados pelo produtor (PS PAL espanhol e GBC EUA) continuam **não lidos**.
- **3 afirmações foram sustentadas em parte por fonte alternativa** lida no GitHub:
  - seriais e regiões PS (E2P-003);
  - desenvolvedora e publicadora PS (E2P-007);
  - hashes do SLES-03396 (E2P-009). **Os três valores (CRC32, MD5, SHA-1) batem caractere a caractere com a DAT do Redump.** A DAT também diz a que arquivo eles se referem.
- A **distribuição de idiomas por serial**, antes em aberto, agora tem apoio E3: SLES-03396 sem etiqueta de idioma, SLES-03397 "(Fr,De)", SLES-03398 "(Es,It,Nl)".
- Os **hashes de referência dos 4 discos PS e dos 2 cartuchos GBC** foram registrados (seção 2.9). Servem para identificar, no futuro, qual versão está no arquivo do proprietário (E1).
- **12 afirmações** tinham detalhes sem nenhum trecho de apoio. Esses detalhes foram retirados (seção 5).
- **Novas divergências:**
  - datas: as bases lidas dão **2001-02-28 para os 4 seriais PS**, contra 5/6 e 23 de março nos resumos;
  - SLES-03398: "versão espanhola" contra "(Europe) (Es,It,Nl)";
  - **número de jogadores PS: 1 contra 2**;
  - data GBC: 28/02 contra março.
- **Próximo passo de maior valor:** ler os dois manuais e as páginas bloqueadas numa rede que as alcance, ou pelo proprietário. A confirmação real (E1) só vem do arquivo original.

---

## 2. Afirmações

### 2.1 Manuais e material primário

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| E2P-001 | Manual PS PAL espanhol | Existe no Internet Archive um item intitulado "Disney-Pixar Toy Story Racer - Manual (Spain) SLES-03398 800dpi 48bit". Só o título foi visto (resultado de busca do produtor). O conteúdo não foi lido. | H | fonte inacessível (produtor propôs E3; o conteúdo, se lido, seria E2). Ver D-04 sobre o SKU SLES-03398. | [archive.org][a-manual] | Abrir fora desta rede e conferir páginas, idioma e se é mesmo o manual do SLES-03398. Só referenciar a URL; não baixar para o repositório. |
| E2P-002 | Manual GBC EUA | Existe um PDF "Toy Story Racer (USA)" no videogamemanual.com. O conteúdo não foi lido. | H | fonte inacessível | [videogamemanual.com (PDF)][vgm] | Abrir fora desta rede e conferir se é o manual oficial (logotipos, código de produto). Comparar com o código BT5E da No-Intro (N-05). Só referenciar; não versionar. |

### 2.2 Identificação da mídia e proteção

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| E2P-003a | Seriais PS | Existem quatro discos PS: SLUS-01214 (EUA) e SLES-03396, SLES-03397 e SLES-03398 (Europa). | E3 | **sustentada por fonte alternativa**: a DAT Redump (linhas 17403–17424) lista exatamente esses 4 seriais, com região "USA" para SLUS-01214 e "Europe" para os três SLES. | [psxdatacenter SLUS-01214][psxdc-slus], [psxdatacenter SLES-03396][psxdc-sles96], [SerialStation][serialstation] (inacessíveis); [DAT Redump][redump-dat] (lida) | Ler o serial impresso no disco e no arquivo `SYSTEM.CNF` da imagem do proprietário (E1). |
| E2P-003b | Idiomas por serial | DAT Redump: SLES-03397 "(Fr,De)", SLES-03398 "(Es,It,Nl)", SLES-03396 e SLUS-01214 sem etiqueta de idioma. gamedb do DuckStation: SLES-03396 e SLUS-01214 English; SLES-03397 French, German; SLES-03398 Dutch, Italian, Spanish. Somados, são os 6 idiomas citados pelo produtor. | E3 (Redump) / H (DuckStation) | **sustentada por fonte alternativa**. Preenche a lacuna "distribuição de idiomas por serial NÃO CONFIRMADA". | [DAT Redump][redump-dat]; [gamedb DuckStation][duck] (linhas 44562–44649) | Menu de idiomas e arquivos de texto e voz do disco original (E1); verso da caixa de cada SKU (E2). |
| E2P-003c | "SLES-03398 = versão espanhola" | SerialStation (via resumo) chamaria o SLES-03398 de versão espanhola. | H | fonte inacessível + **divergente** (D-04) | [SerialStation][serialstation] | Caixa e manual do SLES-03398: idiomas impressos e países de venda. |
| E2P-003d | IDs digitais | SerialStation (via resumo) listaria NPEF-00094 e NPUJ-01214. Os dois IDs não aparecem nas bases lidas. | H | fonte inacessível | [SerialStation][serialstation] | Registro na PlayStation Store. É fora do período 2000–2002, só contexto. |
| E2P-008 | LibCrypt | Um post de verificação no fórum do Redump diria "LibCrypt: No", sem anti-modchip, para o SLES-03396. Os demais seriais não foram verificados. | H (fórum) | fonte inacessível. Pista adicional: a gamedb do DuckStation marca `libcrypt: true` em 225 seriais e em **nenhum** dos 4 deste jogo. **Ausência de marcação não prova ausência de proteção.** | [fórum Redump][redump-forum]; [gamedb DuckStation][duck] | Campo LibCrypt da página de cada disco em redump.org (4 seriais). Apenas registrar; não contornar nenhuma proteção. |
| E2P-009a | Hashes SLES-03396 | O arquivo "Disney-Pixar Toy Story Racer (Europe).bin" (SLES-03396, 259.157.472 bytes) tem CRC32 `6A58A1C0`, MD5 `4B3CE4C59D9157A092E322DA10A51787` e SHA-1 `40CBE537780059F94D91EB783E63E4017ED8E366`. Os três valores do produtor batem caractere a caractere, o que responde "a qual arquivo se referem": ao `.bin` da imagem no padrão Redump. | E3 | **sustentada por fonte alternativa** (DAT Redump, linha 17406) | [fórum Redump][redump-forum] (inacessível); [DAT Redump][redump-dat] (lida) | Calcular os hashes do `.bin` do arquivo do proprietário (E1) e comparar com a tabela 2.9. Só há correspondência se a imagem estiver no formato Redump (bin/cue bruto). |
| E2P-009b | Detalhes do dump | Dump de 2026-05-16, feito com Redumper b706, C2 = 0. | H | fonte inacessível. Esses dados não constam na DAT. | [fórum Redump][redump-forum] | Ler o post. Não afeta o jogo em si. |
| E2P-027 | Código de barras | O título de um anúncio do eBay traz "47875800113" junto do nome da versão PS. Se é o UPC (sem o zero inicial): **NÃO CONFIRMADO**. | H (anúncio) | fonte inacessível | [eBay][ebay] | Código de barras da contracapa NTSC-U original. |

### 2.3 Datas de lançamento

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| E2P-004 | PS NTSC-U | Os resumos dão 5/3/2001 (TCRF), 6/3/2001 (psxdatacenter/SerialStation) e só "março de 2001" (Wikipedia). Data exata: **NÃO CONFIRMADA**. | H | fonte inacessível + **divergente** (D-01). Os metadados derivados do psxdatacenter (2020) e a gamedb do DuckStation dão **2001-02-28** para o SLUS-01214. | [psxdatacenter SLUS-01214][psxdc-slus], [TCRF][tcrf-ps], [Wikipedia][wiki-en] (inacessíveis); [dados psxdatacenter 2020][psxdc-snap], [gamedb DuckStation][duck] (lidos) | Press release da Activision de 2001 ou anúncio em revista da época (E2). |
| E2P-005 | PS PAL | 23/3/2001, segundo o TCRF e o psxdatacenter (SLES-03398), ambos via resumo. | H | fonte inacessível + **divergente** (D-02). As mesmas bases lidas dão **2001-02-28** para os três SLES. | [TCRF][tcrf-ps], [psxdatacenter SLES-03398][psxdc-sles98] (inacessíveis); [dados psxdatacenter 2020][psxdc-snap], [gamedb DuckStation][duck] | Material da Activision UK/Europa de 2001; revistas europeias de março de 2001. |
| E2P-006 | GBC | Europa em 28/2/2001 (MobyGames, via resumo); "março de 2001" sem região (Wikipedia, via resumo). | H | fonte inacessível + **divergente** (D-03). Os metadados GBC do libretro dão ano 2001 e mês 3 para "Toy Story Racer (Europe) (En,Fr,De)". | [MobyGames GBC][moby-gbc], [Wikipedia][wiki-en] (inacessíveis); [libretro GBC ano][gbc-year], [mês][gbc-month] (pista) | Catálogo Nintendo ou Activision da época (E2). |

### 2.4 Desenvolvedora e publicadora

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| E2P-007a | PS | Desenvolvida pela Traveller's Tales e publicada pela Activision. | E3 (derivado) | **sustentada por fonte alternativa**: os metadados derivados do psxdatacenter (2020) dão developer "Traveller's Tales" e publisher "Activision" para os 4 seriais; a gamedb do DuckStation (pista) diz o mesmo. | [psxdatacenter SLUS-01214][psxdc-slus] (inacessível); [dados psxdatacenter 2020][psxdc-snap] (linhas 5744–5760 e 132183–132236); [gamedb DuckStation][duck] | Tela de créditos (E1); página de copyright do manual e logotipos da caixa (E2). |
| E2P-007b | GBC | Desenvolvida pela Tiertex Design Studios (MobyGames, via resumo). Os metadados GBC do libretro dão developer "Tiertex" e publisher "Activision" para os 2 cartuchos. | H | fonte inacessível. A corroboração vem só de base comunitária sem fonte declarada. | [MobyGames GBC][moby-gbc] (inacessível); [libretro GBC dev][gbc-dev], [pub][gbc-pub] | Manual GBC (E2P-002); tela de título e créditos do cartucho. |
| E2P-007c | Papel da Disney Interactive | Wikis citam "Activision and Disney Interactive Studios". Se a Disney Interactive foi co-publicadora ou licenciadora: **NÃO CONFIRMADO**. | H (wiki) | fonte inacessível | [Disney Wiki][disney-wiki] | Logotipos na caixa e no manual; tela de abertura do jogo. |

### 2.5 Classificação etária

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| E2P-010 | ESRB | "Everyone" (E) com o descritor "Comic Mischief", segundo resumos de fontes não oficiais. Classificação oficial: **NÃO CONFIRMADA**. | H | fonte inacessível. Os metadados ESRB de PS1 do libretro não têm entrada para este jogo (ausência não prova nada). | [GameSpot][gs-game]; [eBay][ebay] | Banco da ESRB (esrb.org) ou selo na capa NTSC-U. |
| E2P-011 | USK | USK 0 ("ohne Altersbeschränkung") na Alemanha. A atribuição à URL já era incerta. | H | fonte inacessível | [Wikidata][wikidata] | Banco da USK ou selo na capa da versão com alemão (SLES-03397, segundo a DAT Redump). |

### 2.6 Conteúdo (PlayStation e Game Boy Color)

Todos os itens abaixo vêm de resumos de busca. Nenhum pode orientar o Modo Clássico; o documento `conteudo.md` trata esta dimensão em detalhe.

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| E2P-016 | PS, visão geral | Kart com 12 personagens de Toy Story em 18 percursos baseados em locais do filme (MobyGames, via resumo). | H | fonte inacessível (produtor propôs E3) | [MobyGames PS][moby-ps] | Manual PS e contracapa (E2); contagem no jogo (E1). |
| E2P-017 | PS, personagens | A Wikipedia (via resumo) lista 12 nomes: Woody, Buzz Lightyear, Bo Peep, RC, Mr. Potato Head, Slinky Dog, Hamm, Rex, Little Green Man, Rocky Gibraltar, Lenny e Babyface. | H (wiki) | fonte inacessível + parcial (R-07) | [Wikipedia][wiki-en] | Seção de personagens do manual e tela de seleção no jogo (E1). |
| E2P-018 | PS, pistas e arenas | A Wikipedia (via resumo) dá 18 percursos: 11 pistas de corrida e 7 "smash arenas". Um skate park serve como pista e como arena. Se ele é contado duas vezes: **NÃO CONFIRMADO**. | H (wiki) | fonte inacessível + parcial (R-08) | [Wikipedia][wiki-en] | Nomes oficiais no manual e no jogo. Não completar a lista de memória. |
| E2P-019 | PS, tipos de evento | Knockout Race: o brinquedo em último lugar é eliminado a cada volta (Pixar Wiki, via resumo). | H (wiki) | fonte inacessível + parcial (R-09) | [Pixar Wiki][pixar-wiki] | Seção de modos do manual e teste no jogo (E1). |
| E2P-020 | PS, controles | Guia do GameFAQs (via resumo): direção no direcional ou no analógico; X acelera; O freia e dá ré; botões de ombro usam itens. Pixar Wiki (via resumo): segurar X quando o macaco amarelo das "monkey lights" acender. | H (guia/wiki) | fonte inacessível + parcial (R-10) | [GameFAQs][gamefaqs]; [Pixar Wiki][pixar-wiki] | Seção de controles do manual (E2P-001); medir no jogo (E1). |
| E2P-021 | PS, itens | "eight items that can be used against opponents" (Pixar Wiki) contra "7 types of weapons" (guia do GameFAQs), ambos via resumo. | H (wiki/guia) | fonte inacessível + parcial (R-11); ver D-09 | [GameFAQs][gamefaqs]; [Pixar Wiki][pixar-wiki] | Seção de itens do manual; inventário no jogo (E1). |
| E2P-014 | GBC, review da GameSpot | 4 personagens iniciais (Buzz Lightyear, Woody, Bo Peep, Mr. Potato Head); outros são desbloqueados vencendo corridas no modo torneio e coletando moedas (via resumo). | H | fonte inacessível + parcial (R-05) (produtor propôs E3) | [GameSpot GBC][gs-gbc] | Manual GBC (E2P-002); teste no cartucho. |
| E2P-015 | GBC, descrição no MobyGames | Progresso do torneio salvo por senhas; dificuldade selecionável; corridas de 3 ou 5 voltas (via resumo). O produtor avisa que o resumo misturou MobyGames e StrategyWiki. | H | fonte inacessível + parcial (R-06) | [MobyGames GBC][moby-gbc] | Manual GBC (E2P-002); teste no cartucho. |

### 2.7 Recepção

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| E2P-012 | Metacritic | Versão PS: Metascore 76 com base em 8 críticas (via resumo). | H | fonte inacessível (produtor propôs E3) | [Metacritic][metacritic] | Abrir a página e listar as 8 críticas com as notas. |
| E2P-013 | GameSpot, PS | A review cita "mais de 100 desafios" e corridas que não se limitam a quatro voltas numa pista (via resumo). | H | fonte inacessível + parcial (R-01 a R-04) (produtor propôs E3) | [GameSpot PS][gs-ps] | Abrir a review e confirmar autoria, data, nota e frases. |
| E2P-022 | Revista do Reino Unido | O Everygamegoing reproduz uma review da *Official UK PlayStation 2 Magazine* com a frase "With classic power-ups, loads of challenges and a respectable two-player mode, Toy Story Racer is a slice of the good cake." É indício de modo para dois jogadores. | H | fonte inacessível + parcial (R-12); ver D-05 (produtor propôs E3) | [Everygamegoing][everygame] | Edição original da revista: número, data e plataforma. Modo para 2 jogadores: testar no jogo (E1). |
| E2P-023 | Revistas dos EUA | Segundo a Wikipedia, três críticos da *Electronic Gaming Monthly* deram 5/10, 4,5/10 e 6/10 à versão PS. | H (wiki) | fonte inacessível + parcial (R-13) | [Wikipedia][wiki-en] | Edição original da EGM. |

### 2.8 Outros

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| E2P-024 | Créditos | Os créditos PS no MobyGames incluem 96 pessoas (via resumo). Nomes e cargos não foram lidos. | H | fonte inacessível (produtor propôs E3) | [MobyGames créditos][moby-credits] | Tela de créditos do jogo (E1) e créditos do manual (E2). |
| E2P-025 | Conteúdo não usado | Segundo o TCRF (via resumo), existe uma fala de derrota do Woody que nunca toca. | H (wiki) | fonte inacessível + parcial (R-14) | [TCRF PS][tcrf-ps] | Análise forense do arquivo original (E1). |
| E2P-026 | Relançamentos (fora de 2000–2002) | Wikipedia (via resumo): relançamento publicado nos EUA em 27 de julho e na Europa em 25 de agosto; o ano não consta no trecho. Uma página do PS Deals tem o título "(PSOne Classic)". TV Tropes (via resumo): remaster em HD dentro da coletânea "Toy Story: Retro Roundup!" (Atari/Digital Eclipse), previsto para 15/10/2026. | H (wiki) | fonte inacessível + parcial (R-15) | [Wikipedia][wiki-en]; [PS Deals][psdeals]; [TV Tropes][tvtropes] | Anúncio oficial da Atari/Digital Eclipse (relevante para o registro de riscos de propriedade intelectual) e página da PlayStation Store. |

### 2.9 Achados novos desta verificação

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| N-01 | Estrutura da imagem PS | Na DAT Redump, cada um dos 4 discos tem **um único arquivo `.bin`**, sem o sufixo "(Track N)" que a mesma DAT usa em discos com várias trilhas. Se isso significa disco de trilha única (sem trilhas de áudio CD-DA): **H**. | E3 (o que a DAT lista) / H (a interpretação) | lida | [DAT Redump][redump-dat] (linhas 17403–17424) | Ler o `.cue` do arquivo do proprietário (E1). |
| N-02 | Hashes de referência PS e GBC | Ver a tabela 2.10. | E3 | lida | [DAT Redump][redump-dat]; [DAT No-Intro GBC][nointro-gbc] | Comparar com os hashes do arquivo original (E1). |
| N-03 | Dados derivados do psxdatacenter (2020) | Os 4 seriais PS têm developer "Traveller's Tales", publisher "Activision", data 2001-02-28 (**a mesma para os quatro**) e `users "2"`. | E3 (derivado) | lida; divergente em data (D-01, D-02) e em jogadores (D-05) | [dados psxdatacenter 2020][psxdc-snap] | Caixa e manual (E2); jogo (E1). |
| N-04 | gamedb do DuckStation | Nos 4 seriais: controles AnalogController, DigitalController e NeGcon; `vibration: true`; `minBlocks`/`maxBlocks` 1; `maxPlayers: 1`; `multitap: false`; data 2001-02-28; publisher "Activision"; developer "Traveller's Tales"; sem `libcrypt: true`. | H (pista) | lida; divergente em jogadores (D-05) e em data (D-01, D-02) | [gamedb DuckStation][duck] (linhas 44562–44649) | Ícones de compatibilidade na contracapa (E2); teste com cada controle e blocos de Memory Card no jogo (E1). |
| N-05 | Cartuchos GBC (No-Intro) | Duas entradas: "Toy Story Racer (USA, Europe)", serial `BT5E`, e "Toy Story Racer (Europe) (En,Fr,De)", sem serial na DAT. As duas têm 2.097.152 bytes. | E3 | lida. Preenche em parte a lacuna "seriais GBC não localizados". | [DAT No-Intro GBC][nointro-gbc] (linhas 11038–11048) | Etiqueta do cartucho e caixa (E2). |
| N-06 | Metadados GBC (libretro) | Serial `CGB-BT5P-EUR` para "(Europe) (En,Fr,De)"; developer "Tiertex" e publisher "Activision" para os dois cartuchos; `users 1` para os dois; ano 2001 e mês 3 só para "(Europe) (En,Fr,De)". | H (pista) | lida; divergente em data (D-03) | [serial][gbc-serial], [dev][gbc-dev], [pub][gbc-pub], [jogadores][gbc-users], [ano][gbc-year], [mês][gbc-month] | Etiqueta, caixa e manual GBC (E2). |

### 2.10 Hashes de referência (metadados; nenhum dado de jogo)

Os hashes servem para **identificar qual versão** está no arquivo do proprietário, quando ele for aberto num ambiente autorizado (Prompt Master, seções 12 e 70). Esta tabela não substitui o cálculo sobre o arquivo original.

**PlayStation (DAT Redump, versão 2026.08.01, espelho libretro `d5bae90`)**

| Serial | Nome na DAT | Bytes | CRC32 | MD5 | SHA-1 |
|---|---|---|---|---|---|
| SLES-03396 | Disney-Pixar Toy Story Racer (Europe) | 259157472 | `6A58A1C0` | `4B3CE4C59D9157A092E322DA10A51787` | `40CBE537780059F94D91EB783E63E4017ED8E366` |
| SLES-03397 | Disney-Pixar Toy Story Racer (Europe) (Fr,De) | 266787360 | `730124EE` | `B4A5A4147FABB677990C476118DFDA86` | `34F64759499DD1EA77E6F348DCC664C260AD9C77` |
| SLES-03398 | Disney-Pixar Toy Story Racer (Europe) (Es,It,Nl) | 269120544 | `B3A09F39` | `7DB3B977777ED5541869D0A4C780EC18` | `9BEDA518522895AA8450EB6A37CC7DF7EE9CA19E` |
| SLUS-01214 | Disney-Pixar Toy Story Racer (USA) | 259183344 | `C155FE5C` | `C09C5B2234744CF96837CA8B659B219B` | `D094DDD08F1C74FBF7DE8D04CFF98AB8129CDE47` |

**Game Boy Color (DAT No-Intro, versão 2026.08.01, espelho libretro `d5bae90`)**

| Serial | Nome na DAT | Bytes | CRC32 | MD5 | SHA-1 |
|---|---|---|---|---|---|
| BT5E | Toy Story Racer (USA, Europe) | 2097152 | `D911DD97` | `01A67ED2DC935044BA69EDA42BDDEBF3` | `5DEB31321A86B260AA84CAB5E45A3FA36CE5EFBD` |
| (não consta na DAT; `CGB-BT5P-EUR` segundo os metadados libretro) | Toy Story Racer (Europe) (En,Fr,De) | 2097152 | `F660ED94` | `3E3C0FF63A8F5DE3C13A60B82CEA89D9` | `1D06B1B563EC34014A8EABFD557E20EE03154FF9` |

---

## 3. Divergências entre fontes

Nenhuma divergência foi resolvida. As versões estão registradas sem escolher lado.

| ID | Tema | Versão A | Versão B | Versão C | Situação |
|---|---|---|---|---|---|
| D-01 | Data PS NTSC-U | 5/3/2001: [TCRF][tcrf-ps] (resumo) | 6/3/2001: [psxdatacenter][psxdc-slus] e [SerialStation][serialstation] (resumo); "março de 2001": [Wikipedia][wiki-en] (resumo) | **2001-02-28**: [dados psxdatacenter 2020][psxdc-snap] e [DuckStation][duck] (lidos) | **Nova.** A versão C vem de dados derivados do próprio psxdatacenter, a quem o resumo atribuiu "6 de março". As causas possíveis (página alterada depois de 2020, atribuição errada no resumo, erro na conversão) não podem ser distinguidas sem ler a página. NÃO CONFIRMADA. |
| D-02 | Data PS PAL | 23/3/2001: [TCRF][tcrf-ps] e [psxdatacenter SLES-03398][psxdc-sles98] (resumo) | **2001-02-28** para os três SLES: [dados psxdatacenter 2020][psxdc-snap] e [DuckStation][duck] (lidos) | — | **Nova.** NÃO CONFIRMADA. |
| D-03 | Data GBC | Europa em 28/2/2001: [MobyGames GBC][moby-gbc] (resumo) | "março de 2001", sem região: [Wikipedia][wiki-en] (resumo) | 2001, mês 3, para "(Europe) (En,Fr,De)": [libretro GBC][gbc-month] (lido; pista) | **Ampliada.** NÃO CONFIRMADA. |
| D-04 | Natureza do SLES-03398 | "Versão espanhola": [SerialStation][serialstation] (resumo); manual "(Spain) SLES-03398": [archive.org][a-manual] (título) | "(Europe) (Es,It,Nl)": [DAT Redump][redump-dat] (lida); Dutch/Italian/Spanish: [DuckStation][duck] (lida) | — | **Nova.** Não é necessariamente contradição: um SKU multilíngue pode ter manual impresso para a Espanha. NÃO CONFIRMADA. |
| D-05 | Número de jogadores PS | "respectable two-player mode": [Everygamegoing/OPS2M][everygame] (resumo); `users "2"`: [dados psxdatacenter 2020][psxdc-snap] (lido) | `maxPlayers: 1`: [DuckStation][duck] (lido) | — | **Nova.** NÃO CONFIRMADA. Confirmar na contracapa e no jogo (E1). |
| D-06 | Publicadora | "Activision": Wikipedia e MobyGames (resumo); [dados psxdatacenter 2020][psxdc-snap] e [DuckStation][duck] (lidos) | "Activision and Disney Interactive Studios": [Disney Wiki][disney-wiki], Pixar Wiki e TV Tropes (resumo) | — | Mantida. O papel da Disney Interactive está NÃO CONFIRMADO. |
| D-07 | Desenvolvedora por plataforma | Wikipedia (resumo): "Traveller's Tales and Tiertex Design Studios", juntas | PS = Traveller's Tales ([dados psxdatacenter 2020][psxdc-snap], lido); GBC = Tiertex ([MobyGames][moby-gbc], resumo; [libretro GBC][gbc-dev], pista) | — | Não é contradição. A divisão por plataforma deve ser confirmada nos créditos e no manual. |
| D-08 | Personagens GBC | 4 iniciais, com outros desbloqueados por vitórias e moedas: [GameSpot GBC][gs-gbc] (resumo) | "4 personagens selecionáveis", sem desbloqueio: MobyGames (segundo o produtor) | — | **Não verificável.** O lado B depende de um detalhe sem trecho de apoio (R-06). |
| D-09 | Quantidade de itens PS | "eight items": [Pixar Wiki][pixar-wiki] (resumo) | "7 types of weapons": [GameFAQs][gamefaqs] (resumo) | — | Mantida. As duas fontes são wiki/guia. |
| D-10 | Composição dos 18 percursos PS | 11 pistas + 7 arenas = 18: [Wikipedia][wiki-en] (resumo) | O skate park serve como pista e como arena (mesma fonte) | — | Mantida. Pode haver contagem dupla. NÃO CONFIRMADA. |
| D-11 | Recepção | Metacritic 76/100: [Metacritic][metacritic] (resumo) | EGM 5, 4,5 e 6/10: [Wikipedia][wiki-en] (resumo) | — | Opiniões diferentes, não contradição factual. |

---

## 4. Lacunas

### 4.1 O que só o jogo ou o arquivo original pode responder (E1)

- **Qual versão o proprietário tem.** Serial, região e idiomas saem do `SYSTEM.CNF` e da comparação de hashes com a tabela 2.10. O formato interno de "Disney_Pixar Toy Story Racer.zip.7z" (bin/cue, ISO, CHD, PBP ou outro) é desconhecido.
- **Estrutura do disco:** número de trilhas e presença de áudio CD-DA (N-01).
- **LibCrypt ou outra proteção** em cada serial. Só registrar; não contornar.
- **Número de jogadores e modos multijogador** (D-05), Multitap, blocos de Memory Card, vibração e compatibilidade com NeGcon (N-04).
- **Conteúdo:** personagens, pistas, arenas, itens, eventos, controles, largada com turbo, desbloqueios e custos. Nada disso pode vir das wikis (seções 2.6 e 5).
- **Conteúdo não usado** citado pelo TCRF (E2P-025 e R-14).
- **Créditos completos** (tela de créditos).
- **GBC** (se o proprietário tiver o cartucho): senhas, número de pistas, personagens e desbloqueios.

### 4.2 Fontes primárias (E2) ainda não obtidas

- **Manual PS PAL espanhol** (E2P-001) e **manual GBC EUA** (E2P-002): localizados, não lidos.
- **Manual PS NTSC-U** (SLUS-01214) e manuais do SLES-03396 e do SLES-03397: nenhuma digitalização localizada.
- **Caixa e contracapa** de todas as regiões: não obtidas. Contêm o selo de classificação, o número de jogadores, os ícones de compatibilidade e o código de barras.
- **Press releases** da Activision e da Disney Interactive (2000–2001): nenhum localizado.
- **Site oficial da época** (via web.archive.org): bloqueado. URL desconhecida.
- **Classificações oficiais:** ESRB, USK, ELSPA e PEGI (para PEGI, também se o sistema já existia em março de 2001) não confirmadas; OFLC e CERO não investigadas. Existência de lançamento japonês: NÃO CONFIRMADA.
- **Reviews contemporâneas no original:** EGM, *Official U.S. PlayStation Magazine*, GamePro, PSM, Nintendo Power (GBC), *Official UK PlayStation 2 Magazine* e revistas europeias. A URL original da review da IGN não foi localizada.
- **Prévias, entrevistas e demos** de 2000–2001 (E3 2000, ECTS 2000, discos de demonstração de revistas): nada localizado.
- **GBC:** data de lançamento na América do Norte e confirmação dos seriais BT5E e CGB-BT5P-EUR na embalagem.

### 4.3 Bloqueios técnicos desta sessão

- O proxy de saída bloqueia todos os hosts de pesquisa citados (seção 6.2).
- A cota de WebSearch está esgotada (200/200). Para mais buscas, o usuário precisa aumentar `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`.
- Liberar esses domínios na rede do ambiente, ou fazer a leitura fora dela, é pré-requisito para qualquer afirmação chegar a E2.

---

## 5. Afirmações rejeitadas

Motivo padrão, salvo indicação: o detalhe **não aparece em nenhum trecho apresentado pelo produtor**, e a fonte está inacessível. A rejeição é **provisória**: o detalhe pode voltar se a leitura da fonte confirmar. Enquanto isso, nada abaixo pode ser usado.

| ID | Origem | Trecho retirado | Motivo |
|---|---|---|---|
| R-01 | E2P-013 | Autoria "Tim Tracy" | Sem trecho de apoio. |
| R-02 | E2P-013 | Citação literal "it's no Crash Team Racing, but Toy Story Racer provides plenty of challenge for young and old alike" | Apresentada como citação literal sem nenhum trecho que a contenha. Não pode ficar no corpo como citação. |
| R-03 | E2P-013 | Modo de batalha numa arena circular, com o objetivo de nocautear o maior número de oponentes | Sem trecho de apoio. |
| R-04 | E2P-013 | Elogio à simplicidade dos controles | Sem trecho de apoio. |
| R-05 | E2P-014 | "10 pistas", modo "corrida rápida (quick race)", "pistas 3D com efeito de vídeo" | O trecho da GameSpot GBC só fala de personagens, torneio e moedas. |
| R-06 | E2P-015 | Dois modos; só 3 pistas iniciais na corrida rápida; 10 pistas; 4 personagens selecionáveis (lista); recordes apagados ao desligar; gráficos por vídeo pré-renderizado | Sem trecho de apoio. O próprio produtor avisa que o resumo misturou MobyGames e StrategyWiki, então a atribuição à URL também é incerta. |
| R-07 | E2P-017 | 4 personagens iniciais; desbloqueio com soldados; "200 no total" | O trecho só traz a lista de nomes. |
| R-08 | E2P-018 | Nomes dos locais (casa do Andy, vizinhança, shopping, píer, Pizza Planet, estacionamento subterrâneo, casa do Sid, quadra de basquete, boliche, cinema, posto de gasolina, rinque de gelo) | O trecho termina em "..." antes de qualquer nome. |
| R-09 | E2P-019 | Os outros 7 tipos de evento (Race, Race Tournament, Knockout Race Tournament, Lap Trial, Endurance, Collection e Target) e suas regras | O trecho só descreve o Knockout Race. |
| R-10 | E2P-020 | "e continuar segurando na largada" | O trecho diz só "hold X" quando o macaco acende. |
| R-11 | E2P-021 | Nomes dos itens (pião, foguete, choque elétrico, acelerador, pião tipo guarda-chuva, pião azul grande); caixas de quatro cores; dois itens por caixa; ovelhas da Bo Peep em caixas rosa | Sem trecho de apoio. O produtor também admite que o resumo não individualizou as fontes. |
| R-12 | E2P-022 | "Edição nº 6" e autor "Lee Hall" | O título da página só nomeia a revista. |
| R-13 | E2P-023 | IGN 8,2/10 e a citação da IGN; OPM EUA nº 44 (maio de 2001), p. 102, por Chris Baker | O trecho só traz as notas da EGM. |
| R-14 | E2P-025 | Cadeira fora dos limites na Andy's House; versão antiga da música dos créditos; variação não usada da fanfarra de vitória | O trecho só traz a fala de derrota do Woody. |
| R-15 | E2P-026 | Ano "2010" e plataformas "PS3/PSP" do relançamento | O trecho traz só dia e mês. O título do PS Deals só diz "PSOne Classic". |
| R-16 | Notas do produtor | Arenas "Backyard Brawl" e "Pizza Planet Arcade" | O produtor já tinha descartado: a origem parece ser um texto gerado por IA (Grokipedia) e o nome não aparece em nenhuma outra fonte. Descarte mantido. |
| R-17 | E2P-027 (redação) | "provável UPC" | Não foi rejeitado o dado, e sim a palavra: a regra suprema proíbe "provavelmente" e qualquer presunção. Reescrito como "se é o UPC: NÃO CONFIRMADO". |

Nenhuma afirmação foi classificada como **não sustentada** por contradição direta, porque nenhuma fonte citada pôde ser lida. As contradições encontradas em fontes alternativas estão na seção 3.

---

## 6. Fontes consultadas

### 6.1 Lidas nesta verificação

- [DAT Redump de PlayStation, espelho libretro][redump-dat]: linhas 17403–17424.
- [Metadados PS derivados do psxdatacenter (2020), libretro][psxdc-snap]: linhas 5744–5760 e 132183–132236.
- [DAT No-Intro de Game Boy Color, espelho libretro][nointro-gbc]: linhas 11038–11048.
- Metadados GBC do libretro: [developer][gbc-dev], [publisher][gbc-pub], [ano][gbc-year], [mês][gbc-month], [serial][gbc-serial], [jogadores][gbc-users].
- Metadados ESRB de PS1 do libretro ([arquivo][psx-esrb]): sem entrada para o jogo.
- [gamedb.yaml do DuckStation][duck]: linhas 44562–44649.
- Local: `docs/PROMPT_MASTER.md`, seções 0, 12, 13, 14, 15, 56 e 70.
- Local: `LegacyReference/research/conteudo.md`, só para manter o formato coerente. Nenhum dado foi trazido de lá.

### 6.2 Citadas e inacessíveis (testadas em 2026-09-27)

| Fonte | Tipo | Resultado |
|---|---|---|
| [archive.org, manual SLES-03398][a-manual] | candidata a E2 | EGRESS_BLOCKED |
| [videogamemanual.com, manual GBC (PDF)][vgm] | candidata a E2 | EGRESS_BLOCKED |
| [psxdatacenter SLUS-01214][psxdc-slus] · [SLES-03396][psxdc-sles96] · [SLES-03398][psxdc-sles98] | base de dados | EGRESS_BLOCKED / CONNECT 403 |
| [SerialStation][serialstation] | base de dados | EGRESS_BLOCKED |
| [Fórum Redump][redump-forum] | fórum | EGRESS_BLOCKED |
| [MobyGames PS][moby-ps] · [GBC][moby-gbc] · [créditos][moby-credits] | base de dados | EGRESS_BLOCKED / CONNECT 403 |
| [GameSpot review PS][gs-ps] · [review GBC][gs-gbc] · [página do jogo][gs-game] | review | EGRESS_BLOCKED / CONNECT 403 |
| [Metacritic][metacritic] | agregador | EGRESS_BLOCKED |
| [Everygamegoing][everygame] | reprodução de revista | EGRESS_BLOCKED |
| [Wikipedia][wiki-en] | wiki (pista) | EGRESS_BLOCKED |
| [TCRF PS][tcrf-ps] | wiki (pista) | EGRESS_BLOCKED |
| [Pixar Wiki][pixar-wiki] · [Disney Wiki][disney-wiki] | fandom (pista) | EGRESS_BLOCKED |
| [TV Tropes][tvtropes] | wiki (pista) | EGRESS_BLOCKED |
| [GameFAQs, guia][gamefaqs] | guia de usuário (pista) | EGRESS_BLOCKED |
| [Wikidata][wikidata] | base colaborativa | EGRESS_BLOCKED |
| [PS Deals][psdeals] | loja/agregador | EGRESS_BLOCKED |
| [eBay][ebay] | anúncio (pista) | EGRESS_BLOCKED |

Também testados sem sucesso (`CONNECT 403`): serialstation.com/titles/SLES/03398, tcrf.net (página GBC), web.archive.org, esrb.org, redump.org, usk.de, pegi.info, igdb.com, giantbomb.com, activision.com, google.com, duckduckgo.com.

### 6.3 Deliberadamente não acessadas

Estas fontes apareceram nos resultados do produtor e **não foram acessadas nem citadas** por serem ROM, ISO ou emulação: itens do archive.org com imagens do jogo, arquivos `.7z` de imagem, emuparadise, coolrom, romsgames, emulatorgames, retrostic, cdromance e sites de emulação online. As DATs lidas (seção 6.1) contêm **só metadados** (nomes, tamanhos e hashes), nenhum dado de jogo.

[a-manual]: https://archive.org/details/sles-03398-spain-manual_RAW
[vgm]: https://www.videogamemanual.com/gbc/Toy%20Story%20Racer%20%28USA%29.pdf
[psxdc-slus]: https://psxdatacenter.com/games/U/D/SLUS-01214.html
[psxdc-sles96]: https://psxdatacenter.com/games/P/D/SLES-03396.html
[psxdc-sles98]: https://psxdatacenter.com/games/P/D/SLES-03398.html
[serialstation]: https://serialstation.com/games/ce83ce34-ee68-4de4-9be7-8801db5f2feb
[redump-forum]: http://forum.redump.org/viewtopic.php?pid=139673
[tcrf-ps]: https://tcrf.net/Toy_Story_Racer_%28PlayStation%29
[wiki-en]: https://en.wikipedia.org/wiki/Toy_Story_Racer
[moby-ps]: https://www.mobygames.com/game/6486/disneypixar-toy-story-racer/
[moby-gbc]: https://www.mobygames.com/game/75534/disneypixar-toy-story-racer/
[moby-credits]: https://www.mobygames.com/game/6486/disneypixar-toy-story-racer/credits/playstation/
[disney-wiki]: https://disney.fandom.com/wiki/Toy_Story_Racer
[pixar-wiki]: https://pixar.fandom.com/wiki/Toy_Story_Racer
[gs-game]: https://gamespot.com/disney-pixar-toy-story-racer
[gs-ps]: https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/
[gs-gbc]: https://www.gamespot.com/reviews/toy-story-racer-review/1900-2696485/
[metacritic]: https://www.metacritic.com/game/disney-pixar-toy-story-racer/critic-reviews/
[everygame]: https://www.everygamegoing.com/larticle/toy-story-racer/56526/
[gamefaqs]: https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747
[wikidata]: https://www.wikidata.org/wiki/Q2447854
[tvtropes]: https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/ToyStoryRacer
[psdeals]: https://psdeals.net/us-store/game/2731/disneypixar-toy-story-racer-psone-classic
[ebay]: https://www.ebay.com/itm/406414092380
[redump-dat]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/redump/Sony%20-%20PlayStation.dat
[psxdc-snap]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/developer/Sony%20-%20PlayStation.dat
[psx-esrb]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/esrb/Sony%20-%20PlayStation.dat
[nointro-gbc]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/no-intro/Nintendo%20-%20Game%20Boy%20Color.dat
[gbc-dev]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/developer/Nintendo%20-%20Game%20Boy%20Color.dat
[gbc-pub]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/publisher/Nintendo%20-%20Game%20Boy%20Color.dat
[gbc-year]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/releaseyear/Nintendo%20-%20Game%20Boy%20Color.dat
[gbc-month]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/releasemonth/Nintendo%20-%20Game%20Boy%20Color.dat
[gbc-serial]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/serial/Nintendo%20-%20Game%20Boy%20Color.dat
[gbc-users]: https://raw.githubusercontent.com/libretro/libretro-database/d5bae90b22018ce3c9c5a8eff4141a4768c8dd5f/metadat/maxusers/Nintendo%20-%20Game%20Boy%20Color.dat
[duck]: https://raw.githubusercontent.com/stenzek/duckstation/a2edf2d0f0dc28036fb5888dab397b87e0c4ca0c/data/resources/gamedb.yaml
