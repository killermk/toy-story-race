# Conteúdo do jogo original

- **Data:** 2026-09-27
- **Dimensão:** conteúdo do jogo original (personagens, progressão, modos, pistas, arenas, itens, multiplayer, controles; versões PlayStation e Game Boy Color)
- **Papel deste documento:** verificação adversarial independente das afirmações levantadas por outro agente de pesquisa.

> **Pesquisa pública — PISTAS DE INVESTIGAÇÃO, não prova. Nada aqui é E1.**
>
> Nenhuma linha deste arquivo pode virar implementação do Modo Clássico. Tudo abaixo é **H / NÃO CONFIRMADO** até ser observado no jogo original (Prompt Master, seções 0, 13, 14 e 56).

---

## Método

### O que foi tentado

1. **Leitura direta de cada URL citada** (ferramenta WebFetch) — **nenhuma abriu**. Foram testados 30 endereços em 28 hosts: 28 bloqueados pelo proxy de saída do ambiente (`EGRESS_BLOCKED`), 1 recusado pela ferramenta (web.archive.org) e 1 com host inexistente (lista completa na seção 7).
2. **Acesso por `curl`** a 9 endereços (Wikipedia, MobyGames, Redump, fórum Redump, Nintendo Fandom, Cheats Fandom, Giant Bomb, archive.org, IGN) — todos falharam (HTTP 000).
3. **Busca na web (WebSearch)** para conferir trechos — **indisponível**: a cota de buscas da sessão (200/200) já tinha sido usada pelo agente produtor.
4. **Checagem de DNS** dos hosts citados: `www.gamefaqs.gamespot.com` **não existe** (não resolve). Os demais hosts resolvem; o bloqueio é de política de rede, não de endereço.

### Como a verificação foi feita, então

Sem acesso a nenhuma fonte, a verificação se limitou ao que dá para auditar sem abrir as páginas:

- **Auditoria interna:** cada afirmação foi comparada, frase por frase, com os trechos que o próprio produtor apresentou. Esses trechos são **resumos do mecanismo de busca, não texto literal** — o produtor avisou disso. Qualquer detalhe da afirmação que **não aparece em nenhum trecho** foi retirado do corpo e listado em "Afirmações rejeitadas".
- **Coerência cruzada:** números e nomes de uma afirmação foram conferidos contra os das outras (ex.: requisitos de desbloqueio × desafios nomeados; soma de desafios por personagem × total de soldados).
- **Reclassificação de nível:** a regra do coordenador manda que fonte inacessível fique como **H / NÃO CONFIRMADO**. Por isso, **todas** as afirmações ficaram em H, inclusive as que o produtor tinha proposto como E3 ou E2. O nível proposto aparece na coluna de status, para uso quando as fontes forem lidas.
- **URLs:** foram conferidas quanto a formato e existência do host.

### Legenda de status

| Status | Significado |
|---|---|
| **sustentada** | A fonte foi lida e diz isso. *Nenhuma afirmação chegou a este status nesta rodada.* |
| **fonte inacessível** | A fonte não pôde ser aberta. O conteúdo aparece nos resumos de busca do produtor, mas isso não é leitura direta. Fica como H. |
| **fonte inacessível + parcial** | Idem, e parte do texto original foi removida por não ter nenhum trecho de apoio (ver seção 6). |
| **não sustentada** | A fonte diz outra coisa, a URL é inválida, ou o detalhe não aparece em nenhum trecho. Removida do corpo (seção 6). |

Tipo de fonte (usado nas tabelas): **[E3?]** = candidata a E3 se lida (review contemporânea ou base de dados séria); **[pista]** = wiki, fandom, fórum, guia de usuário, blog, TV Tropes, RetroAchievements ou vídeo — nunca prova única; **[E2?]** = candidata a E2 (material oficial).

---

## 1. Resumo

- **Nenhuma** das 34 afirmações pôde ser confirmada: todas as fontes estavam bloqueadas pela rede, e a cota de buscas já estava esgotada. **Todas ficaram em H / NÃO CONFIRMADO.**
- Os trechos em que o produtor se apoiou são **resumos de busca, não citações literais**. Em pelo menos dois casos os resumos se contradizem: Rex com 17 ou 20 desafios, e requisitos 181/185 contra 175/179.
- **10 afirmações** tinham detalhes que **não aparecem em nenhum trecho apresentado** e foram parcialmente rejeitadas. Entre eles: a sequência de botões do código de depuração, a lista de plataformas do relançamento, a condição "último restante vence" no Smash e a extensão do modo reverso a knockout, tag, smash e torneios.
- Uma URL citada é **inválida**: `www.gamefaqs.gamespot.com` não existe.
- As divergências numéricas públicas continuam abertas: **12 × 10 personagens**, **18 × 19 × 20 pistas**, **"mais de 100" × 200 desafios**, e a soma por personagem dá 192 (ou 189), não 200.
- Uma **nova divergência** foi registrada sobre a condição de vitória do modo de batalha (D-10). Há também uma **observação aritmética**, só como hipótese: 11 pistas + 8 níveis de smash = 19 se a Skate park for contada duas vezes (D-02).
- **Próximo passo para esta dimensão:** liberar os domínios na rede do ambiente e repetir a leitura direta. A confirmação real (E1) só vem do jogo original ou de uma cópia legal, como a coletânea anunciada (REL-01).

---

## 2. Tabelas de afirmações

Todas as fontes abaixo estavam **inacessíveis** em 2026-09-27. "Produtor propôs" indica o nível sugerido pelo agente anterior, a reavaliar quando as fontes forem lidas.

### 2.1 Personagens — PlayStation

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| PS-CHR-01 | Contagem | A versão PS tem **12** personagens jogáveis. | H | Fonte inacessível. Produtor propôs E3. Em conflito com "10" (D-01). | [MobyGames 6486](https://www.mobygames.com/game/6486/disneypixar-toy-story-racer/) [E3?]; [gamepressure](https://www.gamepressure.com/games/toy-story-racer/z851a1) [E3?]; [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista]; [The Phoenix Remix (blog, 2020)](https://thephoenixremix.com/2020/02/16/in-the-games-corner-toy-story-racer-playstation-one/) [pista] | Com save 100%, contar os retratos na seleção de personagem. Em save novo, somar bloqueados + disponíveis. Registrar captura. |
| PS-CHR-02 | Lista nominal | Woody, Buzz Lightyear, Bo Peep, RC, Mr. Potato Head, Slinky Dog, Hamm, Rex, Little Green Man, Rocky Gibraltar, Lenny, Babyface. | H | Fonte inacessível. Lista completa só em wikis; gamepressure dá lista parcial. Grafias divergentes (D-03). | [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista]; [Disney Wiki](https://disney.fandom.com/wiki/Toy_Story_Racer) [pista]; [gamepressure](https://www.gamepressure.com/games/toy-story-racer/z851a1) [E3?] | Ler e capturar a grafia exata de cada nome na seleção e nos avisos de desbloqueio. |
| PS-CHR-03 | Iniciais | Disponíveis desde o início: **Woody, Buzz Lightyear, Bo Peep e RC**. | H | Fonte inacessível. Produtor propôs E3, mas a fonte E3 é uma **prévia** (hands-on de 07/02/2001, antes do lançamento) e o LaunchBox é base colaborativa. | [GameSpot hands-on](https://www.gamespot.com/articles/toy-story-racer-hands-on/1100-2683245/) [E3?, prévia]; [LaunchBox](https://gamesdb.launchbox-app.com/games/details/24259-disney-pixars-toy-story-racer) [pista]; [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista]; [TV Tropes](https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/ToyStoryRacer) [pista] | Save novo, sem cheats: abrir a seleção e capturar quais personagens estão liberados. |
| PS-CHR-04 | Requisitos de desbloqueio | Tabela da wiki (soldados; personagem com que se joga para liberar): Rex 20 (Buzz); Hamm 45 (Woody); Slinky Dog 70 (Bo Peep); Mr. Potato Head 95 (Woody); Little Green Men 103 (Buzz); Rocky 130 (RC); Lenny 175 (Mr. Potato Head); Babyface 179 (Rocky). **8 dos 12** são desbloqueáveis (Wikipedia). | H | Fonte inacessível. Só wiki e guia de usuário. Conflito 181/185 (D-06). Coerência interna: Rocky 130, Lenny 175 e Babyface 179 batem com os desafios de PS-CHR-05. | [Disney Wiki](https://disney.fandom.com/wiki/Toy_Story_Racer) [pista]; [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista]; [GameFAQs — guia dnextreme88](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista] | Percorrer a torre de cada personagem e anotar o requisito exibido em cada desafio que libera personagem, e qual personagem é liberado ao vencer. |
| PS-CHR-05 | Desafios que liberam personagens | Segundo resumos do guia: **Rocky** — "Parking lot parting shot!" (130 soldados, Smash Tag, Underground parking lot, 5 inimigos); **Lenny** — "Spud they like? Don't think snow!" (175, Tag, Andy's new house, 7 inimigos); **Babyface** — "Party at the Pier?" (179, Race, Pier, 5 voltas, 5 inimigos). A página de cheats diz que o desbloqueio exige completar certos desafios jogando com o personagem indicado. | H | Fonte inacessível + parcial (R-01). Desafios que liberam os outros 5 personagens: não identificados. | [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista]; [GameFAQs — cheats PS](https://gamefaqs.gamespot.com/ps/444542-disney-pixars-toy-story-racer/cheats) [pista] | Jogar cada desafio de desbloqueio e registrar em vídeo: nome, tipo, pista, voltas, oponentes, requisito e personagem liberado. |

### 2.2 Progressão — PlayStation

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| PS-PRG-01 | Soldados como recompensa | Cada vitória em desafio dá **um soldado** (green army man). É preciso acumular cada vez mais soldados para abrir novos desafios e personagens. Os desafios ficam organizados em uma "torre" por personagem. | H | Fonte inacessível. Produtor propôs E3 (GameSpot review). "Torre" vem só do TV Tropes. Termo "tokens" no LaunchBox (D-11). | [GameSpot review PS](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/) [E3?]; [TV Tropes](https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/ToyStoryRacer) [pista]; [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista] | Capturar o contador de soldados antes e depois de vencer. Verificar se algum desafio dá mais de 1. Capturar a tela de "torre". |
| PS-PRG-02 | Total | Wikipedia e Disney Wiki: **200 soldados** no PS. Fórum RetroAchievements: "200 unique challenges". GameSpot review: "more than 100 challenges". | H | Fonte inacessível + parcial (R-13). Em conflito com a soma por personagem (D-04). | [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista]; [Disney Wiki](https://disney.fandom.com/wiki/Toy_Story_Racer) [pista]; [RetroAchievements — fórum](https://retroachievements.org/forums/topic/11086) [pista]; [GameSpot review PS](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/) [E3?] | Contar todos os desafios de todas as torres e ler o máximo do contador de soldados. |
| PS-PRG-03 | Desafios por personagem | Resumos do guia: Woody 20; Buzz 22; Bo Peep 16; RC 21; Slinky Dog 20; Rex **17 ou 20**; Hamm 17; Mr. Potato Head 19; Little Green Man 13; Rocky 8; Lenny 8; Babyface 8. | H (baixa confiança) | Fonte inacessível. Os resumos se contradizem: o detalhamento de Rex com 17 é idêntico ao de Hamm. Soma = 192 (Rex 20) ou 189 (Rex 17). **Não usar sem ler o guia inteiro.** | [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista] | Capturar a torre de cada personagem e contar os desafios. |
| PS-PRG-04 | Recompensa final | Ao terminar o último desafio de um personagem, ganha-se um **distintivo de xerife** (Sheriff badge). Selecioná-lo abre um desafio secreto: um **quebra-cabeça (jigsaw)** com uma imagem do personagem no filme. O RetroAchievements lista conquistas ligadas a quebra-cabeças (Woody, Buzz, Bo Peep). | H | Fonte inacessível. Nenhuma candidata a E2/E3. | [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista]; [RetroAchievements 6808](https://retroachievements.org/game/6808) [pista] | Completar uma torre e registrar o ícone da recompensa e o minijogo (peças, tempo, recompensa). |

### 2.3 Modos — PlayStation

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| PS-MOD-01 | Modos citados por bases e reviews | **gamepressure:** Single Race, Reverse Race, Race Cup Tournament, Time Trial Laps, Knockout Race (último colocado eliminado a cada volta), Smash Challenge (eliminação de oponentes), Tag Races; solo ou 2 jogadores em tela dividida. **GameSpot review:** modo de batalha em "circular arena", arremessando itens (bolas, ovelhas) para derrubar oponentes; modo torneio com pontos em série de corridas curtas. **GameSpot hands-on:** modo tipo "destruction derby". | H | Fonte inacessível. Produtor propôs E3. Nomes variam entre fontes (ex.: "Race Cup Tournament" × "Race Tournament"; "Time Trial Laps" × "Lap Trial"). | [gamepressure](https://www.gamepressure.com/games/toy-story-racer/z851a1) [E3?]; [GameSpot review PS](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/) [E3?]; [GameSpot hands-on](https://www.gamespot.com/articles/toy-story-racer-hands-on/1100-2683245/) [E3?, prévia] | Capturar o nome exato de cada tipo de desafio nas telas de briefing e no menu de 2 jogadores. |
| PS-MOD-02 | Definições (wikis e guia) | **Race:** terminar em 1º; voltas e oponentes variam. **Knockout Race:** último de cada volta é eliminado. **Knockout (Race) Tournament:** eliminação ao fim de cada corrida. **Race Tournament:** pontos por posição. **Lap Trial:** completar a volta no tempo. **Endurance:** várias voltas dentro de um limite. **Collection:** coletar palhaços escondidos antes do tempo. **Target:** achar e destruir alvos com armas. **Countdown:** várias corridas dentro de um tempo. **Survival:** só o nome (definição rejeitada). **Super Survival:** é preciso eliminar os outros para vencer. **Tag:** vencer batendo nos outros. **Smash Tag:** eliminação por armas, não por batida. **Smash Challenge:** 4 a 8 brinquedos em disputa livre. **Smash Tournament:** pontos pelo número de "smashes". Alguns modos podem ser jogados em reverso. | H | Fonte inacessível + parcial (R-02, R-03, R-04). Só wikis e guia. Divergências de nomenclatura (D-09) e de condição de vitória (D-10). | [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista]; [Disney Wiki](https://disney.fandom.com/wiki/Toy_Story_Racer) [pista]; [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista] | Para cada tipo, jogar um desafio e registrar em vídeo: briefing, condição de vitória e derrota, tempo limite e HUD. |
| PS-MOD-03 | Agrupamento do guia | O guia agrupa os desafios em **Regular** (Single Race, reverse race, Smash Race, Knockout Race, Tag Race, Smash Tag Race), **Time-based** (Collection, Countdown Race, Endurance, Lap Trial, Super Survival Race, Survival Race, Target) e **Tournament** (Knockout Race Tournament, Race Tournament, Smash Race Tournament). | H | Fonte inacessível. Não se sabe se o agrupamento existe no jogo ou se é organização do autor do guia. | [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista] | Verificar se a torre mostra categorias ou ícones por tipo. |
| PS-MOD-04 | Reverso | Existe variante reversa: "Reverse Race" (gamepressure); pistas podem ser percorridas ao contrário (LaunchBox); o guia cita um Super Survival (reverse) no Mall e um Lap Trial (reverse) no Pier; a Wikipedia diz que "alguns" modos têm reverso. | H | Fonte inacessível + parcial (R-05). Produtor propôs E3. Nenhuma fonte cita modo espelhado (mirror). | [gamepressure](https://www.gamepressure.com/games/toy-story-racer/z851a1) [E3?]; [LaunchBox](https://gamesdb.launchbox-app.com/games/details/24259-disney-pixars-toy-story-racer) [pista]; [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista] | Jogar um desafio reverse e comparar com a mesma pista no sentido normal (direção, checkpoints, chegada). Listar quais tipos têm reverso. |
| PS-MOD-05 | Voltas e oponentes | Voltas e oponentes **variam** por desafio: a GameSpot diz que as corridas não se limitam a 4 voltas. Exemplos do guia: "Adventures in pork" (torneio, 1 volta, 7 inimigos); "Andy's super speed off" (survival race, Andy's house, 60 soldados, tempo a bater "3:11:00", 4 voltas, 7 inimigos); "Keep going if you can ranger" (2 voltas, 4 inimigos); "Party at the Pier?" (5 voltas, 5 inimigos). Nos trechos, o número de inimigos vai de 4 a 7. | H | Fonte inacessível + parcial (R-06, R-07). A variação tem apoio de candidata a E3 (GameSpot); os valores específicos vêm só do guia. O formato "3:11:00" é ambíguo. | [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista]; [GameSpot review PS](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/) [E3?]; [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista] | Registrar voltas e oponentes no briefing de cada desafio; contar carros no grid; ler o formato do tempo no HUD. |

### 2.4 Pistas e arenas — PlayStation

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| PS-TRK-01 | Contagem | MobyGames e gamepressure: **18** cursos/rotas. Wikipedia e Disney Wiki: 18 = **11 pistas de corrida + 7 arenas de smash**, com a Skate park servindo de pista e de arena. | H | Fonte inacessível. Produtor propôs E3. Conflitos 18 × 19 × 20 e ambiguidade 11+7 (D-02). | [MobyGames 6486](https://www.mobygames.com/game/6486/disneypixar-toy-story-racer/) [E3?]; [gamepressure](https://www.gamepressure.com/games/toy-story-racer/z851a1) [E3?]; [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista]; [Disney Wiki](https://disney.fandom.com/wiki/Toy_Story_Racer) [pista] | Listar todas as pistas e arenas acessíveis (menus e torneios completos) e contar os locais únicos. |
| PS-TRK-02 | Nomes das pistas de corrida | O torneio "Adventures in pork" (1 volta, 7 inimigos) passa por **11 níveis:** Andy's new house, Pier, Underground parking lot, Pizza Planet (external), Skate park, Mall, Andy's house, Sid's attic, Sid's yard, Sid's house, Andy's neighborhood. | H | Fonte inacessível + parcial (R-08). A Wikipedia nomeia só 7 locais; divergências de nome (D-15). Vídeos: só os títulos são conhecidos, não foram assistidos. | [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista]; [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista]; [TV Tropes](https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/ToyStoryRacer) [pista]; [YouTube — Sid's Attic](https://www.youtube.com/watch?v=ob0jVn8mQ5E) [pista]; [YouTube — Neighborhood](https://www.youtube.com/watch?v=CHctsdb_xKU) [pista] | Capturar o nome exato de cada pista no briefing ou na seleção e ligar cada nome ao ambiente. |
| PS-ARN-01 | Nomes das arenas | O torneio de smash "Go go K.O. ranger!" passa por **8 níveis:** Pizza Planet's diner, Pizza Planet's arcade, Ice rink, Cinema, Gas station, Basketball court, Bowling alley, Skate park. | H | Fonte inacessível + parcial (R-09). A Wikipedia nomeia só 5 arenas + Skate park (D-14). | [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista]; [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista]; [YouTube — Arcade](https://www.youtube.com/watch?v=sGMySKIqvU0) [pista]; [YouTube — Track & Arena Overviews](https://www.youtube.com/watch?v=KE0x-YZCTaY) [pista] | Jogar um Smash Tournament completo e registrar cada arena, na ordem, com o nome exibido. |
| PS-ARN-02 | Onde cada modo acontece | A GameSpot descreve a batalha numa "circular arena". O guia cita "Battlesaurus Rex" como Smash challenge no Bowling alley (80 soldados, 7 inimigos). Tag e Smash Tag também aparecem em **pistas**: Smash Tag no Underground parking lot; Tag em Andy's new house. | H | Fonte inacessível. Não se sabe se Tag e Smash Tag também ocorrem em arenas. | [GameSpot review PS](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/) [E3?]; [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista] | Para cada desafio Smash, Tag e Smash Tag, capturar se ocorre em arena ou em pista. |
| PS-TRK-03 | Detalhes de ambiente | Na pista da casa do Andy aparecem sótão, sala e cozinha (TV Tropes). Scud, o cão do Sid, aparece em alguns locais de corrida (Disney Wiki). | H | Fonte inacessível. Só wikis. | [TV Tropes](https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/ToyStoryRacer) [pista]; [Disney Wiki — Scud](https://disney.fandom.com/wiki/Scud) [pista] | Percorrer cada pista em vídeo e anotar landmarks e onde o Scud aparece. |

### 2.5 Itens — PlayStation

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| PS-ITM-01 | Caixas | Os power-ups ficam em caixas de **quatro cores**. São principalmente armas (foguetes, impulsos **eletromagnéticos**) e, às vezes, um "nitro" (gamepressure). A Wikipedia fala em **8 itens** usáveis contra oponentes, entre eles pião, foguete, eletrochoque e acelerador. | H | Fonte inacessível. Produtor propôs E3. Tradução corrigida (C-01). Nomes divergentes (D-07, D-08). | [gamepressure](https://www.gamepressure.com/games/toy-story-racer/z851a1) [E3?]; [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista] | Abrir caixas de cada cor em várias pistas e capturar ícone e nome de cada item. |
| PS-ITM-02 | Itens por cor | Disney Wiki: 8 itens (7 armas + 1 especial), 2 por cor. **Amarela:** Pixar ball, Magic 8-ball. **Azul:** Rocket, Big whipping top. **Rosa:** Little whipping top, Bo Peep's sheep. **Vermelha:** Electroshock, Battery speed boost (não disponível nas arenas de smash). O guia diz que nos desafios Target cada cor dá um item fixo: 8-ball, rocket, whipping top e electric shock. | H | Fonte inacessível. Só wikis e guia. A Pixar Wiki inclui "Roly Poly Clown" entre as armas (D-09). | [Disney Wiki](https://disney.fandom.com/wiki/Toy_Story_Racer) [pista]; [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista]; [Pixar Wiki](https://pixar.fandom.com/wiki/Toy_Story_Racer) [pista] | Registrar, por modo (corrida, smash, target), o que cada cor fornece; fazer ≥ 20 aberturas por cor. |
| PS-ITM-03 | Efeitos | Speedrun.com: a "power cell" pode ser pega só de passar perto, sem tocar; o guia chama power cell e shocker, das caixas vermelhas, de os únicos itens úteis. Guia GameFAQs: o choque elétrico serve para curta distância e é a arma mais precisa no smash; a ovelha da Bo Peep (caixa rosa) interrompe o embalo do oponente. | H | Fonte inacessível. Redação corrigida (C-02). Que a "power cell" seja o impulso de velocidade é cruzamento de fontes, não trecho único. | [Speedrun.com — guia](https://www.speedrun.com/tsr/guides/b8saf) [pista]; [GameFAQs — guia](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) [pista] | Medir cada item em captura controlada: trajetória, alcance, duração do efeito, recuperação do alvo e raio de coleta. |

### 2.6 Outros sistemas — PlayStation

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| PS-MP-01 | Multiplayer | Modo para **2 jogadores em tela dividida**. A Lollipop cita, entre as opções multiplayer, corridas padrão, rodadas de knockout e torneios que misturam tipos de corrida. | H | Fonte inacessível. Produtor propôs E3. O trecho da Lollipop não diz a plataforma. A lista exata de modos para 2P não está confirmada. | [gamepressure](https://www.gamepressure.com/games/toy-story-racer/z851a1) [E3?]; [Lollipop Magazine (fev/2002)](https://lollipopmagazine.com/2002/02/toy-story-racer-review/) [E3?]; [LaunchBox](https://gamesdb.launchbox-app.com/games/details/24259-disney-pixars-toy-story-racer) [pista] | Com 2 controles, abrir o menu de 2 jogadores e capturar modos, pistas e arenas disponíveis. |
| PS-CTL-01 | Controles e largada | GameSpot: direção por D-pad ou analógico; **X** acelera; **O** freia e dá ré; botões de ombro usam itens. GameRevolution (dica): quando o macaco amarelo das "monkey lights" acende, segurar X e manter ao começar a corrida. | H | Fonte inacessível + parcial (R-10). Produtor propôs E3. O hands-on (prévia) achou o analógico "overly sensitive". | [GameSpot review PS](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/) [E3?]; [GameRevolution — cheats PS](https://www.gamerevolution.com/guides/31692-toy-story-racer-ps-cheats) [pista] | Conferir o mapeamento no menu de opções. Medir quadro a quadro a janela da largada e o efeito de segurar X. |
| PS-VEH-01 | Veículos e diferenciação | Premissa (LaunchBox): Andy ganha vários carrinhos de controle remoto, usados pelos brinquedos para correr. Pixar Wiki: RC é o único personagem que é o próprio carro, sem piloto. A **diferença de atributos** entre personagens **diverge** nas fontes (D-12). | H | Fonte inacessível + parcial (R-14: uma das URLs é inválida). | [LaunchBox](https://gamesdb.launchbox-app.com/games/details/24259-disney-pixars-toy-story-racer) [pista]; [Pixar Wiki — RC Car](https://pixar.fandom.com/wiki/RC_Car) [pista]; [Pixar Wiki](https://pixar.fandom.com/wiki/Toy_Story_Racer) [pista]; [GameFAQs — review de usuário 171481](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/reviews/171481) [pista] | Medir velocidade máxima, aceleração e raio de curva de cada personagem na mesma pista. Capturar o modelo de veículo de cada um. |
| PS-PHY-01 | Terreno | Velocidade e dirigibilidade mudam com o terreno: subidas reduzem bastante a velocidade; em pista externa, cimento dá mais controle que grama alta. | H | Fonte inacessível. Produtor propôs E3. A atribuição à review vem de resumo de busca. | [GameSpot review PS](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/) [E3?] | Medir a velocidade em grama, cimento e rampa, com captura controlada. |
| PS-AI-01 | IA | A descrição da Amazon fala em IA que ajusta a competitividade dos oponentes à habilidade de cada jogador. A Lollipop diz que a IA parece facilitar a vitória do jogador. | H | Fonte inacessível. O texto da Amazon também aparece ligado à página do GBC: versão incerta. O trecho da Lollipop não diz a plataforma. | [Amazon — PS (texto editorial)](https://www.amazon.com/Toy-Story-Racer/dp/B00005AQRE) [E3?, loja]; [Lollipop Magazine](https://lollipopmagazine.com/2002/02/toy-story-racer-review/) [E3?] | Comparar tempos e posições da IA com o jogador liderando e com o jogador atrás, em testes repetidos. |
| PS-DBG-01 | Código de depuração | Existe um código de entrada na tela de título. Feito corretamente, toca um som e permite ir a qualquer desafio não vencido e apertar **Quadrado** para completá-lo (TCRF). SuperCheats: na tela de desafios, apertar Quadrado em qualquer desafio. | H | Fonte inacessível + parcial (R-11). Serve **só para QA e auditoria**, não para gameplay. Há um tópico no fórum do speedrun.com relatando que o cheat não funciona. | [TCRF — PS](https://tcrf.net/Toy_Story_Racer_(PlayStation)) [pista]; [SuperCheats](https://www.supercheats.com/playstation/toystoryracer.htm) [pista] | Testar e registrar o efeito exato no contador de soldados e nos desbloqueios. |

### 2.7 Game Boy Color

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| GBC-CHR-01 | Personagens | **4 iniciais:** Buzz, Woody, Bo Peep, Mr. Potato Head. Vencendo corridas no modo torneio e juntando muitas moedas, liberam-se um little green man e um soldado do exército de plástico. Disney Wiki: o RC Car aparece como veículo dirigido pelo Woody. | H | Fonte inacessível. Produtor propôs E3 (GameSpot GBC). Conflitos na D-16. | [GameSpot review GBC](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2696485/) [E3?]; [MobyGames 75534](https://www.mobygames.com/game/75534/disneypixar-toy-story-racer/) [E3?]; [TV Tropes](https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/ToyStoryRacer) [pista]; [Disney Wiki — RC Car](https://disney.fandom.com/wiki/RC_Car) [pista] | Capturar a seleção de personagem no início e depois dos desbloqueios. |
| GBC-TRK-01 | Pistas | **10 pistas** em Andy's house, Pizza Planet e ruas do bairro, feitas com vídeo pré-renderizado (FMV) e sprites por cima. Nomes citados: Bedroom Bash, Pepperoni Extreme, Gas Pump Pressure. | H | Fonte inacessível. Produtor propôs E3. Conflitos na D-17. | [MobyGames 75534](https://www.mobygames.com/game/75534/disneypixar-toy-story-racer/) [E3?]; [GameSpot review GBC](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2696485/) [E3?]; [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista] | Listar todas as pistas nos modos Quick Race e Tournament. |
| GBC-MOD-01 | Modos e regras | Modos **Quick Race** e **Tournament** (Nintendo Fandom). MobyGames: corridas contra 3 oponentes; 3 ou 5 voltas; dificuldade selecionável; um personagem é removido se chegar em 4º ou não completar a volta no tempo, e pode ser recomprado com moedas; game over se os 4 forem removidos; progresso do torneio por senha; recordes apagados ao desligar. | H | Fonte inacessível. Produtor propôs E3. Não foi verificado a qual plataforma cada entrada do MobyGames (6486 × 75534) corresponde (D-20). | [MobyGames 75534](https://www.mobygames.com/game/75534/disneypixar-toy-story-racer/) [E3?]; [Nintendo Fandom](https://nintendo.fandom.com/wiki/Toy_Story_Racer) [pista] | Capturar o menu principal, as opções e o comportamento de eliminação e recompra. |
| GBC-ITM-01 | Moedas e ícones | Moedas espalhadas na pista aumentam a pontuação. Ícones coletáveis dão efeito aleatório: podem desacelerar ou dar invencibilidade ou velocidade máxima temporária. | H | Fonte inacessível. Só wiki. Função das moedas diverge (D-18). | [Wikipedia](https://en.wikipedia.org/wiki/Toy_Story_Racer) [pista] | Coletar moedas e ícones e registrar efeitos e usos das moedas. |
| GBC-PWD-01 | Senhas | O menu tem a opção "Restore" (senha). A senha Shooting Star ×3 + Flower ×3 ativa um cheat: pausar e apertar Select pula de nível. | H | Fonte inacessível. A URL é de uma página de "GameShark Codes", mas o trecho descreve uma senha: conferir se a página é mesmo essa. | [Game Cheats Wiki (GBC)](https://cheats.fandom.com/wiki/Toy_Story_Racer_GBC_GameShark_Codes) [pista] | Conferir o menu Restore e os símbolos de senha. |

### 2.8 Relançamento oficial (caminho legal para observação direta)

| ID | Tópico | Afirmação | Nível | Status verificação | Fonte(s) | Como confirmar no original |
|---|---|---|---|---|---|---|
| REL-01 | Coletânea | Segundo resumo de busca do press release, a coletânea **"Toy Story: Retro Roundup!"** (Digital Eclipse/Atari) inclui Toy Story Racer, com lançamento digital em "15th October". A URL da Game Informer tem a data 2026/06/02. A Wikipedia diz que "ambas as versões" do jogo serão relançadas em 2026 na coletânea. | H (candidata a E2 se o press release for lido) | Fonte inacessível + parcial (R-12). O ano do lançamento (2026) é inferido, não está no trecho. A URL do Games Press parece **truncada**. O trecho "both versions" parece vir do artigo do jogo, não da página da coletânea: atribuição a conferir. | [Games Press — press release](https://www.gamespress.com/Digital-Eclipse-and-Atari-Announce-Companion-Toy-Story-Titles-Toy-Stor) [E2?]; [Game Informer (02/06/2026)](https://gameinformer.com/2026/06/02/digital-eclipse-reveals-toy-story-retro-collection-and-toy-story-3-remaster) [E3?]; [Wikipedia — Retro Roundup](https://en.wikipedia.org/wiki/Toy_Story:_Retro_Roundup!) [pista] | Ler o press release na íntegra. Depois do lançamento, o proprietário pode adquirir a coletânea legalmente e observar o jogo, registrando as diferenças entre a emulação oficial e o original. |

---

## 3. Divergências entre fontes

Nenhum lado foi escolhido. Todas as entradas seguem **NÃO CONFIRMADO**.

| ID | Tópico | Versões encontradas (com fonte) | Observação |
|---|---|---|---|
| D-01 | Personagens (PS) | **12:** MobyGames 6486, gamepressure, Wikipedia, Phoenix Remix. **10:** texto editorial da [Amazon](https://www.amazon.com/Toy-Story-Racer/dp/B00005AQRE). **"ten available characters":** atribuído em resumos à [GameSpot review PS](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/) e repetido na Pixar Wiki. | Só a contagem no jogo resolve. |
| D-02 | Pistas (PS) | **18:** MobyGames, gamepressure, Wikipedia, LaunchBox, Disney Wiki. **19 níveis:** [GameSpot hands-on](https://www.gamespot.com/articles/toy-story-racer-hands-on/1100-2683245/) (prévia). **20 racetracks:** Amazon. Composição: "11 corrida + 7 smash, Skate park nos dois" (Wikipedia, Disney Wiki) × 11 corrida + 8 smash com a Skate park nas duas listas (guia). | **Observação aritmética (H, não é resolução):** 11 + 8 = 19 se a Skate park for contada duas vezes; 11 + 8 − 1 = 18 locais únicos; 11 + 7 = 18 se as "7 arenas" não incluírem a Skate park. As contagens podem refletir formas diferentes de contar, mas isso é NÃO CONFIRMADO. |
| D-03 | Grafia de nomes (PS) | "Little Green Man" (Wikipedia) × "Little Green Men" (Disney Wiki). "Rocky Gibraltar" × "Rocky Gibrator" (trecho atribuído ao TV Tropes). | Capturar a grafia exibida no jogo. |
| D-04 | Total de desafios e soldados (PS) | "more than 100 challenges" (GameSpot) × 200 soldados (Wikipedia, Disney Wiki) × "200 unique challenges" (fórum RetroAchievements) × soma por personagem nos resumos do guia = 192 (ou 189). | "Mais de 100" não contradiz 200, mas também não confirma. |
| D-05 | Desafios de Rex (PS) | 17 × 20 em resumos do mesmo guia. O detalhamento de 17 é idêntico ao de Hamm. | Indica erro no resumidor da busca. |
| D-06 | Requisitos de desbloqueio (PS) | Rocky 130, Lenny 175, Babyface 179 (Disney Wiki; trechos do guia por desafio) × Lenny 181 e Rocky 185 (outro resumo do mesmo guia). 181 aparece como requisito do desafio "Strongman contest Rocky". | Ler o guia; confirmar no jogo. |
| D-07 | Item de impulso (PS) | "nitro" (gamepressure) / "speed booster" (Wikipedia) / "Battery speed boost" (Disney Wiki) / "power cell" (guia speedrun.com) / "dynamite speed boost" (trecho sem fonte atribuível). | Nome oficial desconhecido. |
| D-08 | Arma de choque (PS) — **nova** | "electromagnetic impulses" (gamepressure) / "electroshock" (Wikipedia, Disney Wiki) / "electric shock" (guia GameFAQs) / "shocker" (guia speedrun.com). | Divergência de nomenclatura; efeito não confirmado. |
| D-09 | Coletáveis e alvos (PS) | Collection: "clown weebles" (Wikipedia) × "clown squeeze toys" (TV Tropes) × "clowns" (guia). A Pixar Wiki lista "Roly Poly Clown" como **arma**. Alvos: "dart boards" (Wikipedia) × "target boards" (guia). | Os palhaços podem ser coletáveis ou arma: NÃO CONFIRMADO. |
| D-10 | Vitória no modo de batalha (PS) — **nova** | GameSpot review: derrubar "as many of your opponents as possible" (critério de quantidade). Disney Wiki: Smash Challenge como "free-for-all" (sem condição no trecho) e Smash Tournament com pontos por "smashes". A afirmação original dizia "último restante vence", o que não aparece em trecho nenhum (R-03). | A condição de vitória de cada modo de smash precisa de captura. |
| D-11 | Moeda de progressão (PS) | "green army man" / "soldiers" (GameSpot, wikis, guia) × "tokens" (LaunchBox). | O LaunchBox pode usar termo genérico; confirmar no HUD. |
| D-12 | Diferença entre personagens (PS) | A Pixar Wiki e a Amazon ("each with his or her own unique vehicle") indicam diferenças de estilo. A [review de usuário GameFAQs 171481](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/reviews/171481) diz que todos se controlam e se movem igual. | Só telemetria no jogo resolve. |
| D-13 | Filmes de base | Wikipedia: baseado principalmente no primeiro filme. GameSpot review: personagens e níveis "taken directly from the two blockbuster movies". Disney Wiki (Scud): "Andy's House (from Toy Story 2)". O guia lista "Andy's house" e "Andy's new house" como pistas distintas. | — |
| D-14 | Nomes das arenas (PS) | A Wikipedia nomeia basketball court, bowling alley, cinema, gas station, ice rink (+ skate park). O guia acrescenta Pizza Planet's diner e Pizza Planet's arcade. A gamepressure cita cinema e basketball court entre as "tracks". | — |
| D-15 | Nomes das pistas (PS) | "Pizza Planet restaurant" (Wikipedia) × "Pizza Planet (external)" (guia). "backyard" (TV Tropes) × "yard" (guia). A Wikipedia nomeia só 7 locais de corrida. | — |
| D-16 | Personagens (GBC) | 4 iniciais + 2 desbloqueáveis (GameSpot GBC, MobyGames 75534, Wikipedia, TV Tropes) × "10 characters" (Amazon, página GBC) × lista de 11 nomes (Nintendo Fandom, igual à do PS sem Babyface). | — |
| D-17 | Pistas (GBC) | 10 (MobyGames, GameSpot GBC, Wikipedia) × "only four tracks" (review de usuário GameFAQs GBC; pode se referir a locais) × 20 (Amazon GBC). Locais: 3 (Wikipedia) × "4 distinct locales" (review de usuário). | — |
| D-18 | Moedas (GBC) | Pontuação (Wikipedia) × desbloqueio de personagens (GameSpot GBC) × recompra de personagens eliminados (MobyGames). | As funções podem coexistir; NÃO CONFIRMADO. |
| D-19 | Desenvolvedora e data (PS) — fora do escopo | Traveller's Tales (Wikipedia, MobyGames, GameSpot) × Tiertex Design Studios ([Push Square](https://www.pushsquare.com/games/ps1/toy_story_racer)). Data: 2 de março de 2001 (resumo Redump/Wikipedia) × 5 de março de 2001 (Push Square). | Repassar à dimensão de metadados. |
| D-20 | Identidade das entradas MobyGames — **nova** | A 6486 foi tratada como PS e a 75534 como GBC, mas essa atribuição veio de resumos de busca. Não foi verificado se cada entrada cobre uma ou as duas plataformas. | Afeta a atribuição de PS-CHR-01, PS-TRK-01 e dos itens GBC. |

---

## 4. Lacunas

### 4.1 Só o jogo ou arquivo original pode responder (E1)

- Número exato e grafia oficial dos personagens (PS e GBC), e quais estão liberados em save novo.
- Lista completa de desafios por personagem: nome, tipo, pista, voltas, oponentes, tempo limite e soldados exigidos. Também o total real de soldados e desafios.
- Quais desafios liberam cada personagem (faltam Rex, Hamm, Slinky Dog, Mr. Potato Head e Little Green Man).
- Condição de vitória e derrota de **cada** modo, em especial Survival, Smash Challenge e Smash Tournament.
- Quais tipos de desafio têm variante reversa. Se existe modo espelhado (mirror).
- Contagem de locais únicos (pistas × arenas) e o papel duplo da Skate park.
- Conteúdo de cada cor de caixa **por modo**, nomes oficiais dos itens e efeitos medidos (trajetória, alcance, duração).
- Mapeamento de controles, janela e efeito da largada nas "monkey lights".
- Diferença (ou não) de atributos e de modelo de veículo entre personagens.
- Efeito do terreno (grama, cimento, rampa) e comportamento de ajuste da IA.
- Modos, pistas e arenas no multiplayer de 2 jogadores; suporte a multitap.
- Existência de corrida livre (Quick Race) no PS fora das torres.
- Sistema de save do PS (memory card, blocos).
- Recompensa final por personagem (Sheriff badge, quebra-cabeça) e outros extras desbloqueáveis.
- GBC: pistas, modos, regras de eliminação e recompra, usos das moedas, efeitos dos ícones, senhas.

### 4.2 Lacunas de pesquisa pública (não resolvidas nesta rodada)

- **Bloqueio de rede:** nenhuma fonte pôde ser lida. Para repetir esta verificação, o proprietário precisa liberar os domínios da seção 7 no acesso de rede do ambiente (configurações do ambiente em nuvem → Network access), ou rodar a leitura numa máquina com acesso. Documentação dos níveis de acesso: <https://code.claude.com/docs/en/claude-code-on-the-web>.
- **Manual original do PS (E2):** não consultado. O manual do GBC existe em site de digitalizações. Não foi acessado nem linkado aqui, por ser material com direitos autorais; o proprietário decide se usa uma cópia física própria.
- **Contracapa e encarte do PS (E2):** não lidos. O psxdatacenter e o MobyGames têm galerias de capa, que servem para conferir as contagens impressas na caixa.
- **Review da IGN (2001):** inacessível.
- **Press release da Activision de 2001:** não encontrado.
- **Guia dnextreme88 do GameFAQs:** precisa de leitura integral; é a fonte da maioria dos detalhes, e os resumos de busca dele se contradizem.
- **Leads repassados a outras dimensões, não verificados:** TCRF PS (conteúdo não usado: versão antiga da música de créditos, variação da fanfarra de vitória, fala não usada do Woody, objeto fora dos limites em Andy's House); TCRF GBC (debug/level select); serials SLUS-01214, SLES-03396 e SLES-03398 e a menção a LibCrypt no fórum Redump (a registrar pela dimensão técnica, sem contornar nada); RetroAchievements e speedrun.com como mapas de desafios e níveis.
- **Menção a "key-collecting challenges":** apareceu em resumo sem fonte atribuível. A investigar.
- **Vídeos do YouTube** (overviews e "All Challenges Complete"): não assistidos. Servem para pré-mapeamento, nunca como E1.

---

## 5. Observações de coerência cruzada (sem valor de prova)

- Os requisitos de PS-CHR-04 batem com os desafios nomeados em PS-CHR-05: Rocky 130, Lenny 175, Babyface 179. O título "Spud they like?…" (Lenny, liberado por Mr. Potato Head) é coerente, mas isso **não é evidência**.
- Hamm é liberado com 45 soldados (wiki); um desafio de torneio chamado "Adventures in pork" é mencionado sem requisito no trecho. Nada a concluir.
- O guia speedrun.com ("power cell e shocker das caixas vermelhas") e a Disney Wiki ("vermelha = Electroshock + Battery speed boost") são coerentes entre si. A identidade entre "power cell" e "Battery speed boost" continua H.

---

## 6. Afirmações rejeitadas (removidas do corpo)

Critério: o detalhe **não aparece em nenhum trecho** apresentado pelo produtor, ou a URL é inválida. Com todas as fontes inacessíveis, nada impede reintroduzir um item **depois** da leitura direta da fonte.

| ID | Origem | Texto removido | Motivo |
|---|---|---|---|
| R-01 | PS-CHR-05 | "(contra o personagem a ser liberado)" | Interpretação do produtor. Os trechos só mostram o nome do personagem entre parênteses, e a página de cheats diz "jogando com o personagem indicado", não "contra". |
| R-02 | PS-MOD-02 | Definição de Survival: "terminar em 1º sem ser atingido por arma, senão eliminado" | Nenhum trecho apresentado contém essa definição. |
| R-03 | PS-MOD-02 | Smash Challenge: "último restante vence, eliminação por armas" | Não está no trecho da Disney Wiki ("free-for-all"). A única descrição citada de vitória em batalha (GameSpot) fala em derrubar o máximo de oponentes (D-10). |
| R-04 | PS-MOD-02 | Smash Tournament: "1 ponto por nocaute, soma ao longo das arenas" | O trecho diz só "points for the number of 'smashes'". O valor exato e a soma entre arenas são inferências. |
| R-05 | PS-MOD-04 | Reverso aplicável a "knockout, tag, smash, torneios" | Nenhum trecho cita reverso nesses tipos. Só aparecem reverse race, super survival (reverse), lap trial (reverse) e "alguns modos". |
| R-06 | PS-MOD-05 | "Shop till you drop Buzz" (2 voltas, 7 inimigos); "A stranger from the outside" (3 voltas, 7 inimigos) | Os valores de voltas e inimigos não aparecem em nenhum trecho. |
| R-07 | PS-MOD-05 | "até 8 carros na pista" | Cálculo do produtor (7 inimigos + jogador), não citação. |
| R-08 | PS-TRK-02 | "Adventures in pork" atribuído a Hamm, com 46 soldados | O trecho do torneio não traz personagem nem requisito. |
| R-09 | PS-ARN-01 | "Wild wild Woody" (Smash tournament, 75 soldados, 6 inimigos, lista de 5 arenas) | Nenhum trecho apresentado sobre esse desafio. |
| R-10 | PS-CTL-01 | "segurar X no momento certo dá turbo inicial" | O trecho só descreve o procedimento (segurar X quando o macaco amarelo acende). O efeito (turbo) não aparece. |
| R-11 | PS-DBG-01 | Sequência exata de botões (Círculo, Triângulo, Círculo, Quadrado, X, Quadrado, X, Triângulo, Triângulo, X, Quadrado, Círculo) | A sequência não aparece em nenhum trecho apresentado (TCRF nem SuperCheats). |
| R-12 | REL-01 | Plataformas "PS4, PS5, Xbox Series X/S, Switch, Switch 2, PC" e data "02/06/2026" como data do anúncio | As plataformas não aparecem em nenhum trecho. A data vem só do caminho da URL da Game Informer. |
| R-13 | PS-PRG-02 | "equivalente a 200 desafios, 1 soldado cada, segundo fórum RetroAchievements" | O trecho do RetroAchievements diz "200 unique challenges", sem "1 soldado cada". A equivalência combina fontes diferentes. |
| R-14 | PS-VEH-01 | Fonte "GameFAQs — página do jogo (descrição)" em `https://www.gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer` | **URL inválida:** o host `www.gamefaqs.gamespot.com` não resolve em DNS (conferido em 2026-09-27). O host do GameFAQs é `gamefaqs.gamespot.com`; a página correta não foi verificada. |

### Correções de redação (sem remover conteúdo)

| ID | Origem | Antes | Depois | Motivo |
|---|---|---|---|---|
| C-01 | PS-ITM-01 | "impulsos elétricos" | "impulsos eletromagnéticos" | O trecho da gamepressure diz "electromagnetic impulses". |
| C-02 | PS-ITM-03 | "impulso vermelho ('power cell') acelera e pode ser coletado só por proximidade" | "power cell (caixa vermelha) pode ser pega só de passar perto, sem tocar" | O trecho diz que ela pode ser pega "also by being just near", e não diz que acelera; a ligação com o impulso de velocidade é cruzamento de fontes. |
| C-03 | Todas | Níveis E3 e E2 propostos | H | Regra do coordenador: fonte inacessível fica em H / NÃO CONFIRMADO. |

---

## 7. Fontes consultadas

Estado de acesso em **2026-09-27**. "Bloqueado" = WebFetch devolveu `EGRESS_BLOCKED`. "Domínio bloqueado" = outra página do mesmo host foi testada e bloqueada. Nenhuma fonte foi lida diretamente. Não foram consultados nem linkados sites de ROM/ISO/BIOS, rips de assets ou uploads de mídia do jogo.

**Candidatas a E3 (reviews e bases de dados)**
- [GameSpot — review PS (Tim Tracy)](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2689044/) — bloqueado (também via web.archive.org, recusado).
- [GameSpot — review GBC](https://www.gamespot.com/reviews/toy-story-racer-review/1900-2696485/) — domínio bloqueado.
- [GameSpot — hands-on (07/02/2001, prévia)](https://www.gamespot.com/articles/toy-story-racer-hands-on/1100-2683245/) — bloqueado.
- [MobyGames 6486](https://www.mobygames.com/game/6486/disneypixar-toy-story-racer/) — bloqueado (WebFetch e curl).
- [MobyGames 75534](https://www.mobygames.com/game/75534/disneypixar-toy-story-racer/) — domínio bloqueado.
- [gamepressure](https://www.gamepressure.com/games/toy-story-racer/z851a1) — bloqueado.
- [Lollipop Magazine (fev/2002)](https://lollipopmagazine.com/2002/02/toy-story-racer-review/) — bloqueado.
- [Amazon — PS](https://www.amazon.com/Toy-Story-Racer/dp/B00005AQRE) — bloqueado. [Amazon — GBC](https://www.amazon.com/Toy-Story-Racer-game-boy-color/dp/B00005AKUR) — domínio bloqueado.
- [Push Square](https://www.pushsquare.com/games/ps1/toy_story_racer) — bloqueado.
- [Game Informer (02/06/2026)](https://gameinformer.com/2026/06/02/digital-eclipse-reveals-toy-story-retro-collection-and-toy-story-3-remaster) — bloqueado.
- [psxdatacenter — SLUS-01214](https://psxdatacenter.com/games/U/D/SLUS-01214.html) — bloqueado.

**Candidata a E2**
- [Games Press — press release Digital Eclipse/Atari](https://www.gamespress.com/Digital-Eclipse-and-Atari-Announce-Companion-Toy-Story-Titles-Toy-Stor) — bloqueado; a URL parece truncada.

**Pistas (wikis, fandom, fóruns, guias, blogs, vídeos)**
- [Wikipedia — Toy Story Racer](https://en.wikipedia.org/wiki/Toy_Story_Racer) — bloqueado (WebFetch e curl).
- [Wikipedia — Toy Story: Retro Roundup!](https://en.wikipedia.org/wiki/Toy_Story:_Retro_Roundup!) — bloqueado.
- [HandWiki](https://handwiki.org/wiki/Software:Toy_Story_Racer) — bloqueado.
- [Disney Wiki — Toy Story Racer](https://disney.fandom.com/wiki/Toy_Story_Racer) — bloqueado. [RC Car](https://disney.fandom.com/wiki/RC_Car) e [Scud](https://disney.fandom.com/wiki/Scud) — domínio bloqueado.
- [Pixar Wiki — Toy Story Racer](https://pixar.fandom.com/wiki/Toy_Story_Racer) — bloqueado. [RC Car](https://pixar.fandom.com/wiki/RC_Car) — domínio bloqueado.
- [Nintendo Fandom](https://nintendo.fandom.com/wiki/Toy_Story_Racer) — bloqueado (WebFetch e curl).
- [Game Cheats Wiki — GBC](https://cheats.fandom.com/wiki/Toy_Story_Racer_GBC_GameShark_Codes) — bloqueado (WebFetch e curl).
- [TV Tropes](https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/ToyStoryRacer) — bloqueado.
- [TCRF — PS](https://tcrf.net/Toy_Story_Racer_(PlayStation)) — bloqueado. [TCRF — GBC](https://tcrf.net/Toy_Story_Racer_(Game_Boy_Color)) — domínio bloqueado.
- [GameFAQs — guia dnextreme88](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/faqs/73747) — bloqueado.
- [GameFAQs — cheats PS](https://gamefaqs.gamespot.com/ps/444542-disney-pixars-toy-story-racer/cheats), [review de usuário 171481](https://gamefaqs.gamespot.com/ps/444542-disney-pixar-toy-story-racer/reviews/171481) e [reviews GBC](https://gamefaqs.gamespot.com/gbc/472309-disney-pixar-toy-story-racer/reviews) — domínio bloqueado. Obs.: o mesmo ID 444542 aparece com dois slugs ("disney-pixar-" e "disney-pixars-").
- `www.gamefaqs.gamespot.com/...` — **host inexistente** (R-14).
- [LaunchBox Games DB](https://gamesdb.launchbox-app.com/games/details/24259-disney-pixars-toy-story-racer) — bloqueado.
- [The Phoenix Remix (blog, 2020)](https://thephoenixremix.com/2020/02/16/in-the-games-corner-toy-story-racer-playstation-one/) — bloqueado.
- [SuperCheats](https://www.supercheats.com/playstation/toystoryracer.htm) — bloqueado.
- [GameRevolution — cheats PS](https://www.gamerevolution.com/guides/31692-toy-story-racer-ps-cheats) — bloqueado.
- [Speedrun.com — guia](https://www.speedrun.com/tsr/guides/b8saf) — bloqueado. [Speedrun.com — jogo](https://www.speedrun.com/tsr) — domínio bloqueado.
- [RetroAchievements — jogo 6808](https://retroachievements.org/game/6808) — bloqueado. [Fórum 11086](https://retroachievements.org/forums/topic/11086) — domínio bloqueado.
- [Fórum Redump](https://forum.redump.org/viewtopic.php?pid=139673) — bloqueado (WebFetch e curl).
- YouTube: [Track & Arena Overviews](https://www.youtube.com/watch?v=KE0x-YZCTaY) (bloqueado), [Sid's Attic](https://www.youtube.com/watch?v=ob0jVn8mQ5E), [Neighborhood](https://www.youtube.com/watch?v=CHctsdb_xKU), [Arcade](https://www.youtube.com/watch?v=sGMySKIqvU0), [All Challenges Complete](https://www.youtube.com/watch?v=oXmWHBZJjco) — domínio bloqueado.

**Testados só por curl (falha, HTTP 000):** redump.org (busca de discos), giantbomb.com, archive.org, ign.com.

**Documento interno:** `docs/PROMPT_MASTER.md` (seções 0, 12, 13, 14, 15, 56, 70).
