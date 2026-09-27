"""Geração dos relatórios (JSON, CSV e Markdown em português).

Os relatórios contêm metadados (nomes, tamanhos, hashes, formatos, posições
LBA) e, por pedido explícito da especificação do inventário, pequenos trechos:
os 16 primeiros bytes de cada arquivo em hexadecimal (em arquivos de até 16
bytes, isso é o arquivo inteiro), campos de cabeçalho (ex.: marcador ASCII do
PS-X EXE, nome do VAG), valores do SYSTEM.CNF e comandos REM/TITLE/PERFORMER
do CUE. Nenhum outro conteúdo de arquivo é copiado.

Gravação (``write_reports``): os três arquivos são renderizados em memória,
gravados em temporários e só então publicados; antes de substituir qualquer
um, confere que todos os destinos podem ser substituídos (ex.: CSV aberto e
travado pelo Excel no Windows). Em falha, os temporários são apagados e a
exceção informa quais arquivos já tinham sido substituídos.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

from .fsutil import ensure_dir, fs, remove_quietly

JSON_NAME = "forensic_inventory.json"
CSV_NAME = "forensic_inventory.csv"
MD_NAME = "FORENSIC_INVENTORY.generated.md"
CUSTODY_NAME = "custody_log.jsonl"

CSV_COLUMNS = [
    "tipo",
    "caminho_logico",
    "tamanho",
    "crc32",
    "md5",
    "sha1",
    "sha256",
    "formato",
    "categoria",
    "entropia",
    "entropia_metodo",
    "primeiros_16_bytes_hex",
    "lba",
    "setores",
    "setores_form2",
    "data",
    "observacoes",
]


def _json_default(value):
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return sorted(value)
    return str(value)


def to_json(inventory: dict) -> str:
    return json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=False, default=_json_default) + "\n"


def to_csv(rows: Iterable[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        flat = dict(row)
        flat["observacoes"] = " | ".join(list(row.get("observacoes") or []) + list(row.get("indicios") or []))
        writer.writerow({k: ("" if flat.get(k) is None else flat.get(k)) for k in CSV_COLUMNS})
    return buffer.getvalue()


# ---------------------------------------------------------------- markdown helpers


_CONTROL_CHARS = re.compile("[\x00-\x08\x0b-\x1f\x7f\x85  ]")


def _one_line(value: str) -> str:
    """Uma linha só: CR sozinho também é fim de linha no CommonMark (quebraria
    tabelas/listas); demais caracteres de controle (ex.: nomes corrompidos de
    uma imagem danificada) aparecem escapados como ``\\xNN``."""
    value = value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return _CONTROL_CHARS.sub(lambda m: "\\x%02x" % ord(m.group()) if ord(m.group()) < 0x100
                              else "\\u%04x" % ord(m.group()), value)


def code(text) -> str:
    if text is None or text == "":
        return "—"
    value = _one_line(str(text).replace("`", "'").replace("|", "\\|"))
    return f"`{value}`"


def cell(text) -> str:
    if text is None or text == "":
        return "—"
    value = str(text)
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _one_line(value.replace("|", "\\|"))


def human_size(size) -> str:
    if size is None:
        return "—"
    size = int(size)
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{size} B"
            return f"{size} B ({value:.2f} {unit})"
        value /= 1024
    return f"{size} B"  # pragma: no cover


def table(headers: List[str], rows: List[List[str]]) -> List[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def _counts_table(counter: Dict[str, int], label: str) -> List[str]:
    if not counter:
        return ["_Nenhum._", ""]
    rows = [[cell(k), str(v)] for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))]
    return table([label, "Quantidade"], rows) + [""]


def to_markdown(inv: dict) -> str:
    out: List[str] = []
    kit = inv.get("kit", {})
    out.append("# Inventário forense — gerado automaticamente")
    out.append("")
    out.append(
        f"> Gerado por {cell(kit.get('kit'))} {cell(kit.get('kit_version'))} em {cell(inv.get('gerado_em_utc'))} "
        f"(Python {cell(kit.get('python'))}, py7zr {cell(kit.get('py7zr'))}, pycdlib {cell(kit.get('pycdlib'))}); "
        f"sessão {code(inv.get('sessao'))}."
    )
    out.append("> NÃO editar à mão: execute `python -m tsr_forensics intake` novamente para regenerar.")
    out.append(
        "> Contém metadados (nomes, tamanhos, hashes, formatos, posições) e, por pedido da especificação, pequenos "
        "trechos: os 16 primeiros bytes de cada arquivo em hexadecimal (em arquivos de até 16 bytes, o arquivo "
        "inteiro), campos de cabeçalho (ex.: marcador ASCII do PS-X EXE, nome do VAG), valores do SYSTEM.CNF e "
        "comandos REM/TITLE/PERFORMER do CUE. Nenhum outro conteúdo de arquivo."
    )
    out.append("")
    integrity = inv.get("integridade") or {}
    problems = integrity.get("problemas") or []
    if any(p.get("nivel") == "erro" for p in problems):
        out.append(
            "> **ALERTA DE INTEGRIDADE: a imagem está INCOMPLETA ou CORROMPIDA** — ver a seção "
            "\"Integridade da imagem\". Não use este inventário como referência do jogo antes de resolver isso."
        )
        out.append("")

    original = inv.get("original") or {}
    hashes = original.get("hashes") or {}
    copy = original.get("copia") or {}
    out.append("## 1. Identificação do original")
    out.append("")
    rows = [
        ["Arquivo", code(original.get("nome_arquivo"))],
        ["Caminho registrado", code(original.get("caminho_registrado"))],
        ["Tamanho", cell(human_size(original.get("tamanho")))],
        ["Formato (magic bytes)", cell(f"{original.get('formato_detectado')} — {original.get('evidencia_formato')}")],
        ["Fonte da assinatura", cell(original.get("fonte_assinatura"))],
        ["CRC32", code(hashes.get("crc32"))],
        ["MD5", code(hashes.get("md5"))],
        ["SHA-1", code(hashes.get("sha1"))],
        ["SHA-256", code(hashes.get("sha256"))],
        [
            "Integridade do original",
            cell(
                "INALTERADO (tamanho, mtime e hashes iguais antes e depois do intake)"
                if original.get("inalterado")
                else "ALTERADO OU NÃO VERIFICADO — ver avisos"
            ),
        ],
        ["Última modificação (mtime, UTC)", cell((original.get("stat_antes") or {}).get("mtime_utc"))],
        [
            "Cópia de trabalho",
            cell(
                f"{copy.get('caminho')} — situação: {copy.get('situacao')} — hashes conferem: "
                f"{'sim' if copy.get('hashes_conferem') else 'NÃO'} — somente leitura: "
                f"{'sim' if copy.get('somente_leitura') else 'NÃO'}"
            ),
        ],
    ]
    out += table(["Campo", "Valor"], rows)
    out.append("")

    out.append("## 2. Integridade da imagem")
    out.append("")
    out.append(f"Situação: **{cell(integrity.get('situacao') or 'não avaliada')}**")
    out.append("")
    if problems:
        rows = [[cell("ERRO" if p.get("nivel") == "erro" else "indício"), code(p.get("origem")), cell(p.get("detalhe"))] for p in problems]
        out += table(["Nível", "Origem", "Detalhe"], rows)
        out.append("")
    if integrity.get("observacao"):
        out.append(cell(integrity.get("observacao")))
        out.append("")

    out.append("## 3. Nível de evidência e proveniência")
    out.append("")
    for line in inv.get("nota_evidencia", []):
        out.append(f"- {cell(line)}")
    out.append("")

    out.append("## 4. Estrutura: arquivos compactados")
    out.append("")
    containers = inv.get("conteineres") or []
    if not containers:
        out.append("_Nenhum arquivo compactado processado._")
        out.append("")
    for container in containers:
        out.append(f"### {code(container.get('caminho_logico'))} ({cell(container.get('formato'))})")
        out.append("")
        info = container.get("info") or {}
        if info:
            out.append("- Informações: " + ", ".join(f"{cell(k)}: {cell(v)}" for k, v in info.items()))
        out.append(f"- Situação: {cell(container.get('situacao'))}")
        if container.get("destino"):
            out.append(f"- Destino da extração: {code(container.get('destino'))}")
        out.append("")
        entries = container.get("entradas") or []
        if entries:
            rows = []
            for e in entries:
                rows.append(
                    [
                        code(e.get("nome")),
                        cell("diretório" if e.get("diretorio") else e.get("tamanho")),
                        cell(e.get("tamanho_compactado")),
                        code(e.get("crc32")),
                        cell(e.get("data")),
                        cell(e.get("metodo")),
                        cell(e.get("status") or ("—" if e.get("diretorio") else "")),
                        cell(
                            "; ".join(
                                str(x)
                                for x in (e.get("motivo_recusa"), e.get("nome_no_disco"), e.get("tamanho_compactado_observacao"))
                                if x
                            )
                            or None
                        ),
                    ]
                )
            out += table(["Entrada", "Tamanho", "Compactado", "CRC32", "Data", "Método", "Situação", "Obs."], rows)
            out.append("")
        for item in container.get("descartadas") or []:
            out.append(
                f"- Dados fora do plano (descartados, não gravados): {code(item.get('nome_py7zr'))} — "
                f"{cell(item.get('tamanho'))} bytes — SHA-256 {code(item.get('sha256'))}"
            )
        if container.get("descartadas"):
            out.append("")

    out.append("## 5. Discos")
    out.append("")
    discs = inv.get("discos") or []
    if not discs:
        out.append("_Nenhuma imagem de disco encontrada._")
        out.append("")
    for disc in discs:
        out += _disc_markdown(disc)

    out.append("## 6. Contagens")
    out.append("")
    counts = inv.get("contagens") or {}
    out.append("### Arquivos do sistema de arquivos do disco (ISO9660) por categoria")
    out.append("")
    out += _counts_table((counts.get("arquivos_de_disco") or {}).get("por_categoria", {}), "Categoria")
    out.append("### Arquivos do sistema de arquivos do disco (ISO9660) por formato")
    out.append("")
    out += _counts_table((counts.get("arquivos_de_disco") or {}).get("por_formato", {}), "Formato")
    out.append("### Arquivos extraídos de compactados por formato")
    out.append("")
    out += _counts_table((counts.get("extraidos") or {}).get("por_formato", {}), "Formato")

    out.append("## 7. Arquivos de formato desconhecido")
    out.append("")
    unknown = inv.get("desconhecidos") or []
    if unknown:
        rows = [[code(u.get("caminho_logico")), cell(u.get("tamanho")), cell(u.get("entropia")), code(u.get("primeiros_16_bytes_hex")), cell("; ".join(u.get("indicios") or []))] for u in unknown]
        out += table(["Caminho", "Tamanho", "Entropia (bits/byte)", "Primeiros 16 bytes", "Indícios"], rows)
    else:
        out.append("_Nenhum._")
    out.append("")
    out.append(
        "Formato \"desconhecido\" significa apenas que nenhuma assinatura documentada foi reconhecida; "
        "não é conclusão sobre o conteúdo. Entropia próxima de 8 bits/byte é compatível com dados comprimidos "
        "ou cifrados, mas não prova nenhum dos dois."
    )
    out.append("")

    out.append("## 8. Comparação com DAT Redump (opcional)")
    out.append("")
    redump = inv.get("redump")
    if not redump:
        out.append("_Não executada (nenhum --redump-dat informado)._")
    elif redump.get("erro"):
        out.append(f"Erro: {cell(redump.get('erro'))}")
    else:
        header = redump.get("cabecalho") or {}
        out.append(f"- DAT: {cell(header.get('name'))} — versão {cell(header.get('version'))} — ROMs: {cell(redump.get('roms_no_dat'))}")
        out.append("")  # sem linha em branco a tabela viraria continuação do item de lista (CommonMark/GFM)
        matches = redump.get("correspondencias") or []
        if matches:
            rows = [
                [code(m.get("item")), cell(m.get("jogo_dat")), code(m.get("rom_dat")), cell("sim" if m.get("correspondencia_total") else "parcial"),
                 cell(", ".join(f"{k}={'ok' if v else ('—' if v is None else 'DIFERENTE')}" for k, v in (m.get("campos") or {}).items()))]
                for m in matches
            ]
            out += table(["Item", "Jogo no DAT", "ROM no DAT", "Total", "Campos"], rows)
        else:
            out.append("_Nenhuma correspondência de hash com o DAT fornecido._")
        out.append("")
        out.append(cell(redump.get("observacao")))
    out.append("")

    out.append("## 9. Avisos")
    out.append("")
    warnings = inv.get("avisos") or []
    out += [f"- {cell(w)}" for w in warnings] or ["_Nenhum._"]
    out.append("")
    out.append("## 10. Erros")
    out.append("")
    errors = inv.get("erros") or []
    out += [f"- {cell(e)}" for e in errors] or ["_Nenhum._"]
    out.append("")
    return "\n".join(out)


def _disc_markdown(disc: dict) -> List[str]:
    out: List[str] = []
    out.append(f"### {cell(disc.get('id'))} — origem {code(disc.get('origem'))} (layout: {cell(disc.get('layout'))})")
    out.append("")
    detection = disc.get("deteccao")
    if detection:
        out.append(f"- Detecção sem CUE: {cell(detection.get('evidencia'))}; tipo de faixa assumido pelo conteúdo: {cell(detection.get('tipo_faixa'))}")
        out.append("")
    for note in disc.get("observacoes") or []:
        out.append(f"- {cell(note)}")
    if disc.get("observacoes"):
        out.append("")
    tracks = disc.get("faixas") or []
    out.append("#### Faixas")
    out.append("")
    if tracks:
        rows = []
        for t in tracks:
            h = t.get("hashes") or {}
            rows.append(
                [
                    cell(t.get("numero")),
                    cell(t.get("tipo")),
                    code(t.get("arquivo")),
                    cell(t.get("setores")),
                    cell(
                        f"{t.get('duracao_msf')} ({t.get('duracao_segundos')} s; "
                        f"{t.get('duracao_a_partir_index01_segundos')} s a partir do INDEX 01)"
                        if t.get("setores") is not None
                        else None
                    ),
                    cell(t.get("setores_pregap_no_arquivo")),
                    cell(t.get("lba_index01")),
                    code(h.get("crc32")),
                    code(h.get("sha1")),
                ]
            )
        out += table(["Nº", "Tipo", "Arquivo", "Setores", "Duração", "Pregap no arquivo", "LBA INDEX 01", "CRC32", "SHA-1"], rows)
        out.append("")
        for t in tracks:
            stats = t.get("estatisticas") or {}
            if stats:
                out.append(f"- Faixa {cell(t.get('numero'))}: " + ", ".join(f"{cell(k)}={cell(v)}" for k, v in stats.items()))
            for w in t.get("avisos") or []:
                out.append(f"- Faixa {cell(t.get('numero'))} (aviso): {cell(w)}")
        out.append("")
    else:
        out.append("_Nenhuma faixa._")
        out.append("")
    audio = disc.get("faixas_audio") or []
    out.append(f"- Faixas de áudio (CD-DA): {len(audio)}")
    out.append("")

    iso = disc.get("iso9660")
    out.append("#### Volume ISO9660")
    out.append("")
    if not iso:
        out.append("_Não lido._")
        out.append("")
    elif iso.get("erro"):
        out.append(f"Erro: {cell(iso.get('erro'))}")
        out.append("")
    else:
        pvd = iso.get("pvd") or {}
        keys = [
            ("identificador_sistema", "Identificador de sistema"),
            ("identificador_volume", "Identificador de volume"),
            ("tamanho_volume_blocos", "Tamanho do volume (blocos)"),
            ("tamanho_bloco_logico", "Tamanho do bloco lógico"),
            ("identificador_editor", "Editor"),
            ("identificador_preparador", "Preparador de dados"),
            ("identificador_aplicacao", "Aplicação"),
            ("data_criacao", "Data de criação do volume"),
            ("data_modificacao", "Data de modificação do volume"),
            ("assinatura_cd_xa", "Assinatura CD-XA (400h)"),
        ]
        out += table(["Campo", "Valor"], [[label, code(pvd.get(key))] for key, label in keys])
        out.append("")
        for anomaly in iso.get("anomalias") or []:
            out.append(f"- Anomalia ISO9660 ({cell(anomaly.get('tipo'))}): {cell(anomaly.get('detalhe'))}")
        cross = iso.get("verificacao_pycdlib") or {}
        out.append(
            f"- Verificação cruzada com pycdlib: {cell(cross.get('status'))}"
            + (f" ({cell(cross.get('arquivos_comparados'))} arquivos comparados)" if cross.get("arquivos_comparados") is not None else "")
            + (f" — {cell(cross.get('erro'))}" if cross.get("erro") else "")
        )
        out.append(f"- Arquivos: {cell(iso.get('total_arquivos'))}; diretórios: {cell(iso.get('total_diretorios'))}")
        out.append(f"- Arquivos extraídos em: {code(iso.get('destino_extracao'))}")
        for w in iso.get("avisos") or []:
            out.append(f"- Aviso ISO9660: {cell(w)}")
        out.append("")

    cnf = disc.get("system_cnf")
    out.append("#### SYSTEM.CNF")
    out.append("")
    if not cnf:
        out.append(cell(disc.get("system_cnf_observacao") or "SYSTEM.CNF não encontrado."))
        out.append("")
    else:
        rows = [
            ["BOOT (bruto)", code(cnf.get("BOOT"))],
            ["Executável de boot", code(cnf.get("boot_executavel"))],
            ["Executável presente no disco", cell({True: "sim", False: "NÃO"}.get(cnf.get("boot_executavel_presente")))],
            ["Formato do executável", cell(cnf.get("boot_executavel_formato"))],
            ["Código de produto derivado", cell(f"{cnf.get('codigo_produto_derivado')} — {cnf.get('codigo_produto_observacao')}")],
            ["TCB", code(cnf.get("TCB"))],
            ["EVENT", code(cnf.get("EVENT"))],
            ["STACK", code(cnf.get("STACK"))],
            ["Chaves desconhecidas", cell(", ".join(cnf.get("chaves_desconhecidas") or []) or None)],
        ]
        out += table(["Campo", "Valor"], rows)
        out.append("")

    sub = disc.get("arquivos_subcanal") or []
    out.append("#### Arquivos de subcanal (.sbi/.sub)")
    out.append("")
    if sub:
        rows = [[code(s.get("nome")), cell(s.get("tamanho")), code(s.get("sha1")), cell(s.get("observacao"))] for s in sub]
        out += table(["Arquivo", "Tamanho", "SHA-1", "Observação"], rows)
    else:
        out.append("_Nenhum encontrado junto à imagem._")
    out.append("")

    tree = disc.get("arvore") or []
    out.append("#### Árvore do disco")
    out.append("")
    if tree:
        rows = []
        for node in tree:
            if node.get("diretorio"):
                rows.append([code(node.get("caminho")), cell(node.get("lba")), cell("diretório"), cell(node.get("data")), cell("—"), cell(None)])
            else:
                notes = list(node.get("observacoes") or [])
                rows.append(
                    [
                        code(node.get("caminho")),
                        cell(node.get("lba")),
                        cell(node.get("tamanho")),
                        cell(node.get("data")),
                        cell(node.get("formato")),
                        cell("; ".join(notes) if notes else None),
                    ]
                )
        out += table(["Caminho", "LBA", "Tamanho", "Data", "Formato", "Obs."], rows)
    else:
        out.append("_Vazia ou não lida._")
    out.append("")
    return out


def counts_for(rows: List[dict], tipo: str) -> dict:
    selected = [r for r in rows if r.get("tipo") == tipo]
    return {
        "total": len(selected),
        "por_categoria": dict(Counter(r.get("categoria") or "desconhecido" for r in selected)),
        "por_formato": dict(Counter(r.get("formato") or "desconhecido" for r in selected)),
    }


class ReportWriteError(OSError):
    """Falha ao gravar os relatórios; ``replaced`` lista os que já tinham sido substituídos."""

    def __init__(self, message: str, replaced: List[str]):
        super().__init__(message)
        self.replaced = replaced


def _check_replaceable(path: Path) -> None:
    """Levanta OSError se ``path`` existir e não puder ser substituído agora."""
    if not os.path.lexists(fs(path)):
        return
    if os.path.isdir(fs(path)) and not os.path.islink(fs(path)):
        raise IsADirectoryError(f"o destino é uma pasta: {path.name}")
    # Abrir para escrita SEM gravar nada detecta arquivo travado (ex.: Excel no
    # Windows) ou sem permissão, antes de qualquer substituição.
    with open(fs(path), "r+b"):
        pass


def write_reports(inventory: dict, out_dir: Path) -> Dict[str, Path]:
    out_dir = Path(out_dir)
    paths = {
        "json": out_dir / JSON_NAME,
        "csv": out_dir / CSV_NAME,
        "md": out_dir / MD_NAME,
    }
    rendered = {
        "json": (to_json(inventory), "utf-8"),
        "csv": (to_csv(inventory.get("arquivos") or []), "utf-8-sig"),
        "md": (to_markdown(inventory), "utf-8"),
    }
    temps: Dict[str, Path] = {key: path.with_name(path.name + ".tmp-tsr") for key, path in paths.items()}
    replaced: List[str] = []
    try:
        ensure_dir(out_dir)
        for key, path in paths.items():
            try:
                _check_replaceable(path)
            except OSError as exc:
                raise ReportWriteError(
                    f"{path.name} não pode ser substituído ({type(exc).__name__}: {exc}); feche o arquivo "
                    "(ex.: no Excel) e rode de novo — nenhum relatório foi alterado",
                    replaced,
                ) from exc
        for key, (text, encoding) in rendered.items():
            with open(fs(temps[key]), "w", encoding=encoding, newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
        for key in ("json", "csv", "md"):
            os.replace(fs(temps[key]), fs(paths[key]))
            replaced.append(paths[key].name)
    except ReportWriteError:
        raise
    except OSError as exc:
        state = ("já substituídos: " + ", ".join(replaced)) if replaced else "nenhum relatório foi alterado"
        raise ReportWriteError(f"{type(exc).__name__}: {exc} ({state})", replaced) from exc
    finally:
        for tmp in temps.values():
            remove_quietly(tmp)
    return paths
