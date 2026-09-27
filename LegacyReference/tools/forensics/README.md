# Kit forense `tsr_forensics`

Ferramenta de linha de comando (Python 3.10+, Windows/Linux/macOS) para a
**primeira etapa do projeto: a forense do arquivo original** (Prompt Master,
seções 12 e 70). Ela:

1. registra o arquivo original (tamanho, CRC32, MD5, SHA-1, SHA-256, formato
   pelos *magic bytes*) **sem alterá-lo**;
2. faz uma cópia de trabalho verificada e somente leitura;
3. lista (manifesto) e extrai com segurança os arquivos compactados, inclusive
   aninhados (ex.: `.zip` dentro de `.7z`);
4. lê imagens de disco (`.cue/.bin`, `.iso`, `.bin` sem `.cue`), faixas de
   dados e de áudio, o sistema de arquivos ISO9660 e o `SYSTEM.CNF`;
5. identifica o formato de cada arquivo por assinatura documentada;
6. gera relatórios **somente de metadados** e um log de cadeia de custódia;
7. oferece um `guard` (e um *pre-commit hook*) que impede versionar material
   do jogo neste repositório **público**.

## O que o kit NÃO faz

- **Não modifica o original**: abre só para leitura; nunca escreve, move,
  renomeia nem altera a data de modificação (`mtime`). Mede
  `tamanho`/`mtime`/hashes antes e depois e acusa qualquer diferença (código
  de saída 3). O horário de último acesso (`atime`) pode ser atualizado pelo
  sistema operacional ao ler o arquivo (ver "Limitações conhecidas").
- **Não troca a referência em silêncio**: se o original deixar de conferir
  com o registro (log de custódia) ou com a cópia de trabalho, o `intake`
  para com código 3 e não toca em nada; só aceita a troca com `--rebaseline`
  (ver "Rodar de novo").
- **Não contorna proteções** (ex.: LibCrypt). Arquivos `.sbi`/`.sub` são apenas
  **registrados** (nome, tamanho, hash, presença do cabeçalho `SBI\0`); o
  conteúdo não é interpretado nem usado.
- **Não sobe nada nem acessa a internet.** A comparação com Redump usa apenas
  um arquivo `.dat` que **você** fornecer.
- **Não "chuta" formatos.** Sem assinatura documentada, o arquivo fica como
  `desconhecido` (regra suprema: não inventar, não presumir).
- **Não copia conteúdo do jogo para os relatórios**, exceto pequenos trechos
  pedidos pela especificação do inventário: os 16 primeiros bytes de cada
  arquivo em hexadecimal (**em arquivos de até 16 bytes isso é o arquivo
  inteiro**; o campo `primeiros_16_bytes_sao_o_arquivo_inteiro` marca esses
  casos), campos de cabeçalho (ex.: marcador ASCII do PS-X EXE em 4Ch, até 60
  caracteres; nome do VAG), os valores do `SYSTEM.CNF` e os comandos
  `REM`/`TITLE`/`PERFORMER` do `.cue`. O resto são metadados (nomes,
  tamanhos, hashes, formatos, posições LBA). Se o proprietário decidir que
  nem esses trechos podem ir para o repositório público, isso precisa ser
  removido do código antes do commit dos relatórios.

## Instalação

Pré-requisito: Python 3.10 ou superior (<https://www.python.org/downloads/>;
no Windows marque "Add python.exe to PATH") e Git.

### Windows (PowerShell)

```powershell
cd <pasta-do-repositório>\LegacyReference\tools\forensics
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m tsr_forensics --version
```

Se o PowerShell bloquear o `Activate.ps1`, rode uma vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, ou use diretamente
`.\.venv\Scripts\python.exe` no lugar de `python`.

### Linux / macOS

```bash
cd <pasta-do-repositório>/LegacyReference/tools/forensics
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m tsr_forensics --version
```

A pasta `.venv/` já é ignorada pelo `.gitignore` da raiz.

`requirements.txt` fixa o py7zr, o pycdlib **e as dependências do py7zr**
(mesmas versões testadas). Para instalar conferindo os hashes SHA-256 dos
pacotes (recomendado), use no lugar:

```powershell
python -m pip install --require-hashes -r requirements-lock.txt
```

Os hashes foram copiados dos metadados oficiais do PyPI; wheels para Windows
64 bits existem para CPython 3.10–3.13 em todas as versões fixadas.

## Passo a passo com `Disney_Pixar Toy Story Racer.zip.7z`

Todos os comandos são executados **dentro de**
`LegacyReference/tools/forensics` (com o ambiente virtual ativo).

1. **Deixe o original fora do repositório**, numa pasta sua, por exemplo
   `C:\Jogos\Originais\` (Windows) ou `~/Originais/` (Linux). O kit
   **recusa** (código 2) um original dentro da área de trabalho (`--workdir`,
   padrão `LegacyReference/_work/`, em qualquer subpasta) ou dentro da pasta de
   relatórios (`--out`), e recusa um original dentro do repositório que não
   esteja ignorado pelo `.gitignore` (se estiver ignorado, só avisa).
   Se você escolher um `--workdir` dentro do repositório, ele **precisa** estar
   ignorado pelo `.gitignore`: o kit confere com `git check-ignore` e recusa
   caso contrário (os arquivos do jogo extraídos ali poderiam ser commitados).

2. **Rode o intake:**

   ```powershell
   python -m tsr_forensics intake --original "C:\Jogos\Originais\Disney_Pixar Toy Story Racer.zip.7z"
   ```

   (Linux: `python -m tsr_forensics intake --original ~/Originais/"Disney_Pixar Toy Story Racer.zip.7z"`)

   As aspas são necessárias por causa dos espaços no nome.

3. **Confira o resultado** em
   `LegacyReference/inventory/FORENSIC_INVENTORY.generated.md`: hashes do
   original, estrutura (7z → zip → cue/bin), faixas, árvore do disco,
   `SYSTEM.CNF`, formatos, desconhecidos, avisos e erros.

4. **Verifique a integridade quando quiser** (ex.: antes de cada sessão de
   análise):

   ```powershell
   python -m tsr_forensics verify --original "C:\Jogos\Originais\Disney_Pixar Toy Story Racer.zip.7z"
   ```

   Saída `0` = confere; `1` = ALTERADO (ou cópia/log divergente); `2` = sem
   registro.

5. **Opcional — comparar com um DAT do Redump que você já tenha baixado**
   (o kit não baixa nada):

   ```powershell
   python -m tsr_forensics intake --original "C:\Jogos\Originais\Disney_Pixar Toy Story Racer.zip.7z" --redump-dat "C:\Jogos\DATs\Sony - PlayStation.dat"
   ```

6. **Instale o hook de proteção** (uma vez por clone do repositório):

   ```powershell
   python -m tsr_forensics install-hook
   ```

7. **Commite somente os relatórios** de `LegacyReference/inventory/`
   (ver seção "O que pode ser commitado").

### Rodar de novo

Rodar o `intake` de novo com o **mesmo** original é seguro: a cópia de
trabalho é conferida por hash e reaproveitada; as entradas já extraídas dos
compactados (`extracted/`) são conferidas por tamanho + CRC32 e reaproveitadas;
os arquivos do disco (`disc_files/`) são **regravados** a cada execução (com o
mesmo conteúdo); os relatórios são regenerados; o log de custódia recebe novas
linhas (nunca é reescrito).

Se o original **mudou** (ex.: download novo, arquivo corrompido ou trocado),
o `intake` compara o arquivo com a **referência** registrada no log de
custódia (o primeiro registro daquele nome de arquivo) e com a cópia de
trabalho existente, e **para com código 3 sem alterar nada** (cópia e
relatórios anteriores continuam intactos). O `verify` usa a mesma referência,
então também continua acusando a diferença. Depois de investigar, se a troca
for intencional:

```powershell
python -m tsr_forensics intake --original "C:\Jogos\Originais\Disney_Pixar Toy Story Racer.zip.7z" --rebaseline
```

Com `--rebaseline` a troca fica registrada no log (`original.rebaseline`, com
os hashes antigo e novo) e a cópia de trabalho anterior é **preservada**
(somente leitura) em `_work/original_copy/substituidas/`. Se o original
confere com a referência mas a cópia de trabalho foi alterada, a cópia
alterada também é preservada ali, uma nova cópia é feita e o fato vira ERRO
no relatório (código 1).

### Códigos de saída do `intake`

| Código | Significado |
|---|---|
| 0 | concluído sem erros (pode haver avisos) |
| 1 | concluído com erros — ex.: **imagem incompleta/corrompida** (ver "Integridade da imagem" no relatório), compactado recusado, método de compressão não suportado, arquivo ilegível |
| 2 | erro fatal antes de concluir (ex.: original inexistente, original ou `--workdir` em local recusado, falha ao gravar os relatórios, falha inesperada) — o motivo fica no log de custódia (`intake.abortado`) e o original é reverificado |
| 3 | **o original mudou** durante o intake **ou não confere com a referência registrada/cópia de trabalho** — investigue antes de qualquer coisa (ver "Rodar de novo") |
| 130 | interrompido com Ctrl+C (registrado no log) |

**Integridade da imagem.** São ERROS (código 1), com alerta no topo do
relatório: arquivo de faixa citado no `.cue` e ausente; arquivo de faixa cujo
tamanho não é múltiplo do setor (setor final incompleto); arquivo menor que o
número de setores declarado; diretório ou arquivo do ISO9660 além do fim da
faixa de dados; LBA da faixa de dados indeterminado. "PVD declara mais blocos
que a faixa" é registrado como **indício** (pode ser truncamento, mas também
um volume declarado maior que a faixa — NÃO CONFIRMADO). EDC/ECC não são
verificados: ausência de alertas não prova integridade; compare com um DAT
Redump (`--redump-dat`).

## Onde ficam as saídas

```
LegacyReference/
├── _work/                      ← LOCAL, ignorado pelo git (NUNCA commitar)
│   ├── original_copy/          cópia verificada e somente leitura do original
│   │   └── substituidas/       cópias anteriores preservadas (rebaseline ou cópia alterada)
│   ├── extracted/              conteúdo dos compactados (aninhados em <nome>.extracted/)
│   ├── disc_files/<disco>/     arquivos extraídos do ISO9660 de cada disco
│   └── protected_sha256.txt    SHA-256 de todo material inventariado (cumulativo; usado pelo guard)
└── inventory/                  ← relatórios de METADADOS (podem ser commitados)
    ├── forensic_inventory.json         inventário completo
    ├── forensic_inventory.csv          uma linha por arquivo/faixa (UTF-8 com BOM, abre no Excel)
    ├── FORENSIC_INVENTORY.generated.md resumo legível em português
    └── custody_log.jsonl               cadeia de custódia (somente acréscimo, encadeada por SHA-256)
```

Use `--workdir` e `--out` para escolher outros locais. Caminhos locais nos
relatórios aparecem como `<workdir>/...`, `<out>/...`, `<repo>/...` ou
`<externo>/nome-do-arquivo` para não expor o seu nome de usuário. Isso vale
também para mensagens de erro do sistema (que trazem o caminho completo): elas
são limpas antes de entrar nos relatórios e no log (`<home>` no lugar da sua
pasta de usuário). `--record-full-paths` grava caminhos completos — **não
recomendado**, o repositório é público.

Os três relatórios são gravados juntos: primeiro em temporários, e só são
publicados se todos puderem ser substituídos. Se um deles estiver travado (ex.:
o CSV aberto no Excel), nada é substituído, os temporários são apagados, o
`intake` termina com código 2 e a falha fica no log (`relatorios.falha`).

## O que pode e o que NÃO pode ser commitado

Este repositório é **público** (GitHub Pages).

**Pode** (somente metadados):

- `LegacyReference/inventory/forensic_inventory.json`
- `LegacyReference/inventory/forensic_inventory.csv`
- `LegacyReference/inventory/FORENSIC_INVENTORY.generated.md`
- `LegacyReference/inventory/custody_log.jsonl`
- o próprio código do kit (`LegacyReference/tools/forensics/`)

**NUNCA**:

- o arquivo original, qualquer `.7z/.zip/.rar`, `.bin/.cue/.iso/.img/.sub/.sbi` etc.;
- qualquer coisa de `LegacyReference/_work/` (cópia, extraídos, arquivos do disco);
- executáveis, texturas, áudio, vídeo, modelos ou qualquer arquivo do jogo,
  mesmo renomeado ou convertido;
- BIOS, saves, capturas brutas.

O `.gitignore` da raiz já ignora as extensões e as pastas locais; o `guard`
é a segunda linha de defesa.

## Hook `guard` (pre-commit)

```powershell
python -m tsr_forensics install-hook          # instala .git/hooks/pre-commit
python -m tsr_forensics guard --staged        # o que o hook executa
python -m tsr_forensics guard                 # varre todos os arquivos rastreados
python -m tsr_forensics guard --dir <pasta>   # varre uma pasta qualquer
```

O `guard` lê o conteúdo **do índice do git** (o que de fato seria commitado) e
bloqueia (código 1) arquivos com:

1. extensão de imagem de disco, compactado, subcanal, formato PS1, save ou
   sobra de extração interrompida (`.tsrpart`);
2. assinatura de conteúdo PS1/disco/compactado (PS-X EXE, TIM, VAGp, pBAV,
   pQES, STR, sync de setor bruto, CD001, 7z/zip/rar/…), mesmo com extensão
   inocente;
3. binário maior que `--max-binary-size` (padrão 5 MiB) ou **texto** maior
   que `--max-text-size` (padrão 20 MiB);
4. conteúdo binário **codificado em texto**: se o arquivo começa com base64
   (inclusive `data:...;base64,`) ou hexadecimal, os bytes decodificados passam
   pelas assinaturas da regra 2; texto de 1 MiB ou mais quase só com
   caracteres base64/hex e sem espaços também é acusado;
5. SHA-256 de material original já inventariado — esta regra **nunca** é
   liberada. Fontes: `LegacyReference/inventory/forensic_inventory.json`, os
   hashes de originais e cópias do `custody_log.jsonl` ao lado dele, o
   registro local cumulativo `LegacyReference/_work/protected_sha256.txt`
   (cada `intake` acrescenta ali todos os SHA-256 inventariados, então intakes
   anteriores continuam protegidos mesmo que o inventário seja sobrescrito) e
   listas extras com `--hash-list <arquivo>` (um SHA-256 por linha; use para
   o `protected_sha256.txt` de um `--workdir` diferente do padrão).

Falsos positivos das regras 1–4 podem ser liberados com `--allow "<glob>"` ou
com um arquivo opcional `guard_allowlist.txt` nesta pasta (um padrão glob por
linha, relativo à raiz do repositório — ou à pasta varrida, no modo `--dir`). O hook falha de forma segura: se o kit
ou o Python não forem encontrados, o commit é bloqueado. O hook usa o Python
que rodou o `install-hook`; se ele não existir mais, testa `python3`, `python`
e `py`, exigindo que cada um **execute** e seja 3.10+ (no Windows, `python3`
pode ser só o atalho da Microsoft Store, que é ignorado). Se nada servir, a
mensagem manda reinstalar o hook. O git permite pular
hooks com `git commit --no-verify`; **não faça isso** com material do jogo.

Se já existir um `pre-commit` que não seja deste kit, `install-hook` recusa;
`--force` substitui guardando uma cópia `pre-commit.backup-<data>`. Se
`core.hooksPath` estiver configurado, `install-hook` também recusa (instalar
ali afetaria outros repositórios) salvo `--force`.

## Opções e limites de segurança (`intake`)

| Opção | Padrão | Função |
|---|---|---|
| `--max-total-bytes` | 16G | total que pode ser extraído de compactados no intake inteiro |
| `--max-entry-bytes` | 8G | tamanho máximo de uma entrada |
| `--max-ratio` / `--ratio-min-bytes` | 200 / 64M | razão de compressão máxima (anti-bomba), aplicada a partir do tamanho indicado |
| `--max-entries` | 100000 | entradas por compactado |
| `--max-depth` | 4 | profundidade de compactados aninhados |
| `--entropy-full-max-bytes` | 64M | acima disso a entropia é calculada por amostragem (declarada no relatório) |
| `--pycdlib-timeout` / `--pycdlib-max-memory` | 120 / 1G | limites do processo isolado da verificação cruzada com pycdlib |
| `--rebaseline` | — | aceita que o original difere da referência registrada (ver "Rodar de novo") |

Proteções de extração: nomes com `..`, caminhos absolutos, letras de unidade
(`C:`), byte nulo, links simbólicos/junções e dispositivos são **recusados**
(aviso). Entradas criptografadas, métodos de compressão que a biblioteca
padrão não lê (ex.: ZIP **Deflate64**) e entradas acima de `--max-entry-bytes`
também são recusadas, mas contam como **ERRO** (conteúdo não inventariado).
A razão de compressão é conferida por entrada (ZIP) e no **total** de cada
compactado (todos os formatos), antes (tamanhos declarados) e durante a
extração (bytes realmente descompactados, somados por compactado) — dividir o
conteúdo em muitas entradas pequenas ou declarar tamanhos falsos não contorna
o limite. Num 7z com nomes duplicados, a 1ª ocorrência é extraída; as demais
são medidas (tamanho e hashes, no relatório) e descartadas sem gravar, sem
interromper as outras entradas.
Nomes com espaços e acentos são preservados; caracteres inválidos no Windows
(`<>:"|?*`), nomes reservados (`CON`, `NUL`, `NUL .txt`, `CONIN$`, `CONOUT$`,
`COM1`–`COM9`, `COM¹`–`COM³`, `LPT…`; lista do `ntpath.isreserved` do Python
3.13, mais `COM0`/`LPT0` por precaução) e colisões de destino — maiúsculas e
minúsculas, normalização Unicode (NFC/NFD, macOS), arquivo e pasta com o mesmo
nome, e a pasta `<compactado>.extracted` reservada para compactados aninhados
— são ajustados com sufixo `~N` e o ajuste é registrado. Um destino existente
que seja "apelido" de outro nome (ex.: nome curto 8.3 do Windows) é recusado.

## Decisões técnicas

- **Formato pelos magic bytes, nunca pela extensão.** Fontes citadas no código
  (`signatures.py`, `sniff.py`) e no relatório de cada arquivo.
- **ISO9660: parser próprio + verificação cruzada com pycdlib.** O inventário
  usa um leitor mínimo e tolerante (descritores de volume + registros de
  diretório), que registra anomalias como avisos em vez de abortar, lê o campo
  CD-XA de cada registro (Form1/Form2/intercalado/CD-DA), é protegido contra
  laços e profundidade excessiva e lê no máximo 1 MiB por diretório, setor a
  setor, só do que existe na faixa (um registro com tamanho absurdo, como
  0xFFFFFFFF, não provoca alocação gigante). A mesma visão lógica é então
  aberta com `pycdlib.open_fp` e as listas (caminho, LBA, tamanho) são
  comparadas; divergências viram avisos. O pycdlib **não** se protege contra
  laços: por isso ele roda num **processo separado** com tempo (120 s) e
  memória (1 GiB) limitados, e nem é executado quando o parser próprio já
  encontrou laço, diretório gigante ou profundidade excessiva (status
  `nao_executada` no relatório).
- **STR**: setores com `STR ID` 0160h são contados em Form1 **e** Form2;
  StType 8001h (MDEC padrão) separado dos demais StType, que o psx-spx lista
  com usos variados (ex.: 0004h em setores Form2 no Final Fantasy 9). Os
  demais ficam como indício (casamento de só 2 bytes; natureza NÃO
  CONFIRMADA).
- **7z sólido**: quando vários arquivos compartilham um bloco, não existe
  tamanho compactado por arquivo; o campo fica vazio e o tamanho do bloco é
  anotado à parte.
- **Níveis de evidência no relatório**: medições sobre o arquivo = E1 (sobre
  ESTE arquivo); identificação de formato depende do psx-spx
  (<https://psx-spx.consoledev.net/>), fonte secundária (proposta E3, a
  confirmar pelo coordenador); correspondência com a mídia comercial = NÃO
  CONFIRMADA salvo DAT Redump (E3).
- **Visão lógica de 2048 bytes/setor**: Mode1/2352 → dados em 16; Mode2/2352
  (Form1) → 24; Mode2/2336 → 8; ISO → 0. Setores **Mode2 Form2** (XA-ADPCM,
  STR intercalado) têm 2324 bytes de dados; a extração pelo ISO9660 guarda só
  2048 por setor. O kit **conta** esses setores pelo *submode* do subheader e
  avisa em cada arquivo afetado (`setores_form2`); a extração bruta de Form2
  não está implementada.
- **XA-ADPCM** só é atribuído quando todos os setores do arquivo têm submode
  Audio + Form2 no disco (evidência do subheader, não do nome `.XA`).
- **Código de produto** derivado do `BOOT` do `SYSTEM.CNF` segue a convenção
  `XXXX_NNN.NN` descrita no psx-spx e fica marcado como **NÃO CONFIRMADO**.
- **Cadeia de custódia**: cada linha do `custody_log.jsonl` contém o SHA-256
  da linha anterior; `verify` confere a cadeia. Terminações CRLF (checkout no
  Windows com `autocrlf`) não quebram a verificação.
- **Relatórios com LF** em qualquer sistema (diffs estáveis); CSV em UTF-8
  com BOM (acentos corretos no Excel).

### Fontes das assinaturas

- psx-spx — <https://psx-spx.consoledev.net/> (texto em
  <https://github.com/psx-spx/psx-spx.github.io>): "CDROM File Playstation EXE
  and SYSTEM.CNF", "CDROM File PsyQ .CPE Files", "CDROM File Video Texture
  Image TIM/PXL/CLT", "CDROM File Audio Single Samples VAG", "CDROM File Audio
  Sample Sets VAB and VH/VB", "CDROM File Audio Sequences SEQ/SEP", "CDROM File
  Video Streaming STR", "CDROM Sector Encoding", "CDROM XA Subheader", "CDROM
  ISO Volume Descriptors", "CDROM ISO File and Directory Descriptors", "CDROM
  Disk Images CUE/BIN/CDT", "CDROM Disk Images CCD/IMG/SUB", SBI, ECM, CHD,
  PBP, MDS, "RIFF Headers (on PCs)", "CDROM Protection - LibCrypt".
- 7-Zip `7zFormat.txt`; PKWARE `APPNOTE.TXT`; RARLAB technote; RFC 1952
  (gzip); formato bzip2; The .xz File Format; RFC 8878 (Zstandard); POSIX
  ustar; PNG (RFC 2083); JPEG (ITU T.81); GIF87a/89a; BMP; RIFF; PE/COFF.

Observação do psx-spx registrada no código: **SEQ e SEP usam o mesmo ID
`pQES`**; o kit reporta `SEQ/SEP (pQES)` e apenas descreve o campo de versão,
sem decidir entre os dois.

## Testes

```bash
cd LegacyReference/tools/forensics
python -m unittest discover -s tests
```

Os testes geram **fixtures sintéticas em diretório temporário** (nada do jogo
real, nenhum binário versionado): ISO9660 criado com pycdlib contendo
`SYSTEM.CNF` com serial FALSO (`BOOT = cdrom:\TEST_000.00;1`), PS-X EXE, TIM,
VAG, VAB, SEQ, STR e XA falsos em subpastas; conversão para `.bin`
MODE2/2352 (sync + MSF BCD + subheader + EDC/ECC zerados) com `.cue` e faixa
AUDIO; empacotamento em `.zip` e depois em `Disney_Pixar Test Racer.zip.7z`.
Cobrem: original inalterado, cópia somente leitura, manifesto, árvore do
disco, serial, formatos, faixa de áudio, relatórios, idempotência, zip-slip
(`../evil.txt`, caminho absoluto, letra de unidade, link simbólico), bomba de
descompressão, `.iso` simples, `.bin` sem `.cue`, `verify`, DAT Redump e o
`guard`/hook num repositório git temporário. `tests/test_redteam_regressions.py`
tem um teste de regressão para cada achado da revisão (Red Team): original
alterado + `--rebaseline`, laço de diretório no ISO (pycdlib isolado),
vazamento de caminhos, bomba ZIP dividida, 7z com nomes duplicados, falhas
fora da análise (cópia, CSV travado), imagem truncada, CUE com FILE ausente,
nomes reservados do Windows, colisões de destino, 7z sólido, STR em Form2,
Deflate64, guard (texto codificado, hashes de intakes anteriores, fallback de
Python do hook) e `--workdir` não ignorado. Os testes que usam git são
pulados se o git não estiver instalado.

## Limitações conhecidas

- RAR, Zstandard, ECM, CHD, PBP, MDS/MDF e CCD/IMG são **reconhecidos** pelos
  magic bytes mas **não extraídos/lidos** (dependências limitadas a
  py7zr/pycdlib); aparecem como aviso.
- ZIP: o `zipfile` da biblioteca padrão lê os métodos stored, deflate, bzip2 e
  LZMA (e Zstandard a partir do Python 3.14). Entradas com **Deflate64**
  (método 9) ou outros métodos são recusadas como ERRO, com o método no
  manifesto; nesse caso, extraia com outra ferramenta e rode o `intake` sobre
  o resultado (ele vira o "original" registrado).
- Conteúdo Mode2 **Form2** não é extraído em forma bruta (apenas contado).
- Faixas `CDG`/`CDI` e tipos de faixa não documentados no psx-spx são apenas
  registrados; ISO9660 é lido somente na primeira faixa de dados.
- `.bin` sem `.cue` é tratado como faixa única; sem o `.cue` não há como
  delimitar faixas de áudio (os setores sem sync são apenas contados).
- Se o `--original` for um `.cue`, os `.bin` referenciados não são copiados
  para a área de trabalho — use o arquivo compactado original, um `.iso` ou um
  `.bin`.
- O horário de último acesso (atime) do original pode ser atualizado pelo
  sistema operacional ao ler o arquivo (no Linux o kit tenta `O_NOATIME`);
  `mtime`, tamanho e hashes são os valores verificados.
- Arquivos ISO9660 multi-extensão: apenas a extensão listada é lida (aviso).
- EDC/ECC dos setores não são recalculados/validados (setores corrompidos não
  são detectados por esse meio); o cabeçalho MSF de cada setor é conferido.
- O `guard` só decodifica base64/hex no **início** do arquivo; um trecho
  codificado pequeno no meio de um JSON/JS não é detectado (um grande é, pela
  regra de tamanho/densidade). Ele é a segunda linha de defesa, depois do
  `.gitignore`.
- A suíte de testes foi executada em Linux (Python 3.10, 3.11, 3.12 e 3.13). O
  código foi escrito para Windows e macOS, mas **não foi executado nesses
  sistemas** durante o desenvolvimento. São NÃO CONFIRMADOS até rodarem no seu
  PC: prefixo de caminho longo (`\\?\`), detecção de nomes curtos 8.3, efeito
  real dos nomes reservados, medição de memória do processo isolado do pycdlib
  (via `GetProcessMemoryInfo`; se falhar, só o limite de tempo vale), travas
  de arquivo do Excel e o fallback de Python do hook. Rode
  `python -m unittest discover -s tests` no seu PC antes do primeiro intake.
