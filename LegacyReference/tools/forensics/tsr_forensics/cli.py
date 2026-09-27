"""Interface de linha de comando: ``python -m tsr_forensics <comando>``."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import KIT_NAME, __version__
from .config import MIB, Limits, default_outdir, default_workdir, find_repo_root, parse_size
from .fsutil import PathRedactor

PATH_OPTIONS = {"--original", "--workdir", "--out", "--redump-dat", "--dir", "--repo", "--inventory", "--hash-list"}


def _configure_console() -> None:
    """Evita UnicodeEncodeError em consoles Windows com code page legada."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


def redact_command(argv: List[str], redactor: PathRedactor) -> List[str]:
    """Reproduz o comando sem expor caminhos absolutos (repositório público)."""
    result = ["python", "-m", "tsr_forensics"]
    expect_path = False
    for arg in argv:
        if expect_path:
            result.append(redactor(arg) or arg)
            expect_path = False
            continue
        if "=" in arg and arg.split("=", 1)[0] in PATH_OPTIONS:
            key, value = arg.split("=", 1)
            result.append(f"{key}={redactor(value)}")
            continue
        result.append(arg)
        if arg in PATH_OPTIONS:
            expect_path = True
    return result


def _size_arg(text: str) -> int:
    try:
        return parse_size(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tsr_forensics",
        description=(
            "Kit forense do projeto Toy Story Race. Registra, copia e inventaria o arquivo original "
            "SEM alterá-lo, e impede que material original seja versionado."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{KIT_NAME} {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<comando>")

    intake = sub.add_parser("intake", help="registrar, copiar, inventariar e extrair o original (área local)")
    intake.add_argument("--original", required=True, type=Path, help="caminho do arquivo original (ex.: o .7z)")
    intake.add_argument("--workdir", type=Path, help="área de trabalho local (padrão: <repo>/LegacyReference/_work)")
    intake.add_argument("--out", type=Path, help="diretório dos relatórios (padrão: <repo>/LegacyReference/inventory)")
    intake.add_argument("--redump-dat", type=Path, help="DAT XML do Redump fornecido pelo usuário (opcional)")
    defaults = Limits()
    intake.add_argument("--max-total-bytes", type=_size_arg, default=defaults.max_total_bytes,
                        help="limite total extraído de compactados (padrão 16G)")
    intake.add_argument("--max-entry-bytes", type=_size_arg, default=defaults.max_entry_bytes,
                        help="limite por entrada extraída (padrão 8G)")
    intake.add_argument("--max-ratio", type=float, default=defaults.max_ratio,
                        help="razão máxima de compressão (padrão 200)")
    intake.add_argument("--ratio-min-bytes", type=_size_arg, default=defaults.ratio_min_bytes,
                        help="a razão só é aplicada a partir deste tamanho (padrão 64M)")
    intake.add_argument("--max-entries", type=int, default=defaults.max_entries,
                        help="máximo de entradas por compactado (padrão 100000)")
    intake.add_argument("--max-depth", type=int, default=defaults.max_depth,
                        help="profundidade máxima de compactados aninhados (padrão 4)")
    intake.add_argument("--entropy-full-max-bytes", type=_size_arg, default=defaults.entropy_full_max_bytes,
                        help="entropia exata até este tamanho; acima, por amostragem declarada (padrão 64M)")
    intake.add_argument("--pycdlib-timeout", type=float, default=defaults.pycdlib_timeout_s,
                        help="tempo máximo, em segundos, da verificação cruzada com pycdlib (processo isolado; padrão 120)")
    intake.add_argument("--pycdlib-max-memory", type=_size_arg, default=defaults.pycdlib_max_memory,
                        help="memória máxima do processo isolado do pycdlib (padrão 1G)")
    intake.add_argument("--record-full-paths", action="store_true",
                        help="gravar caminhos absolutos nos relatórios (NÃO recomendado: repositório público)")
    intake.add_argument("--rebaseline", action="store_true",
                        help="aceitar que o original DIFERE da referência registrada (troca intencional do arquivo); "
                             "a cópia anterior é preservada em original_copy/substituidas/ e a troca fica no log")

    verify = sub.add_parser("verify", help="recalcular hashes do original e comparar com o registro")
    verify.add_argument("--original", required=True, type=Path)
    verify.add_argument("--out", type=Path, help="diretório dos relatórios (padrão: <repo>/LegacyReference/inventory)")
    verify.add_argument("--workdir", type=Path, help="área de trabalho (padrão: <repo>/LegacyReference/_work)")
    verify.add_argument("--record-full-paths", action="store_true")

    guard = sub.add_parser("guard", help="procurar material original em arquivos do git ou de um diretório")
    scope = guard.add_mutually_exclusive_group()
    scope.add_argument("--staged", action="store_true", help="somente arquivos staged (uso no pre-commit)")
    scope.add_argument("--dir", type=Path, help="varrer um diretório em vez do índice do git")
    guard.add_argument("--repo", type=Path, help="repositório git (padrão: raiz detectada do kit)")
    guard.add_argument("--inventory", type=Path, action="append",
                       help="forensic_inventory.json com hashes proibidos (repetível)")
    guard.add_argument("--hash-list", type=Path, action="append",
                       help="arquivo com SHA-256 proibidos, um por linha (repetível; padrão: "
                            "<repo>/LegacyReference/_work/protected_sha256.txt, se existir)")
    guard.add_argument("--max-binary-size", type=_size_arg, default=5 * MIB,
                       help="binários acima deste tamanho são acusados (padrão 5M)")
    guard.add_argument("--max-text-size", type=_size_arg, default=20 * MIB,
                       help="arquivos de TEXTO acima deste tamanho são acusados (padrão 20M)")
    guard.add_argument("--allow", action="append", default=[],
                       help="padrão glob de caminho liberado das regras de extensão/assinatura/tamanho (repetível)")
    guard.add_argument("--quiet", action="store_true")

    hook = sub.add_parser("install-hook", help="instalar pre-commit hook local que executa 'guard --staged'")
    hook.add_argument("--repo", type=Path, help="repositório git (padrão: raiz detectada do kit)")
    hook.add_argument("--force", action="store_true", help="substituir hook existente (com cópia de segurança)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    _configure_console()
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    repo = find_repo_root()

    if args.command == "intake":
        from .intake import IntakeError, IntakeOptions, OriginalDivergentError, run_intake

        workdir = Path(os.path.abspath(args.workdir or default_workdir(repo)))
        out = Path(os.path.abspath(args.out or default_outdir(repo)))
        redactor = PathRedactor([("<workdir>", workdir), ("<out>", out), ("<repo>", repo)], full=args.record_full_paths)
        limits = Limits(
            max_total_bytes=args.max_total_bytes,
            max_entry_bytes=args.max_entry_bytes,
            max_ratio=args.max_ratio,
            ratio_min_bytes=args.ratio_min_bytes,
            max_entries=args.max_entries,
            max_depth=args.max_depth,
            entropy_full_max_bytes=args.entropy_full_max_bytes,
            pycdlib_timeout_s=args.pycdlib_timeout,
            pycdlib_max_memory=args.pycdlib_max_memory,
        )
        options = IntakeOptions(
            original=args.original,
            workdir=workdir,
            out=out,
            limits=limits,
            redump_dat=args.redump_dat,
            record_full_paths=args.record_full_paths,
            command=redact_command(argv, redactor),
            rebaseline=args.rebaseline,
        )
        print(f"[intake] original: {args.original}")
        print(f"[intake] área de trabalho: {workdir}")
        print(f"[intake] relatórios: {out}")
        try:
            code = run_intake(options)
        except KeyboardInterrupt:
            print("[intake] interrompido (Ctrl+C); o aborto foi registrado no log de custódia.", file=sys.stderr)
            return 130
        except Exception as exc:  # IntakeError e falhas inesperadas: mensagem clara, sem traceback
            if isinstance(exc, OriginalDivergentError):
                print(f"[intake] ORIGINAL DIVERGE DO REGISTRO: {exc}", file=sys.stderr)
                return 3
            if isinstance(exc, IntakeError):
                print(f"[intake] ERRO FATAL: {exc}", file=sys.stderr)
            else:
                print(f"[intake] ERRO INESPERADO: {type(exc).__name__}: {exc}", file=sys.stderr)
                if os.environ.get("TSR_FORENSICS_DEBUG"):
                    raise
            print("[intake] O aborto foi registrado no log de custódia (quando a pasta --out estava acessível).", file=sys.stderr)
            return 2
        summary = {0: "concluído sem erros", 1: "concluído COM ERROS (ver relatório)", 3: "ORIGINAL ALTERADO — investigue"}
        print(f"[intake] {summary.get(code, code)}. Relatórios em {out}")
        return code

    if args.command == "verify":
        from .verify import run_verify

        workdir = Path(os.path.abspath(args.workdir or default_workdir(repo)))
        out = Path(os.path.abspath(args.out or default_outdir(repo)))
        redactor = PathRedactor([("<workdir>", workdir), ("<out>", out), ("<repo>", repo)], full=args.record_full_paths)
        return run_verify(
            args.original,
            out,
            workdir,
            command=redact_command(argv, redactor),
            record_full_paths=args.record_full_paths,
            repo_root=repo,
        )

    if args.command == "guard":
        from .guard import run_guard

        target_repo = Path(os.path.abspath(args.repo or repo))
        return run_guard(
            target_repo,
            staged=args.staged,
            directory=args.dir,
            inventories=args.inventory,
            hash_lists=args.hash_list,
            max_binary=args.max_binary_size,
            max_text=args.max_text_size,
            allow=args.allow,
            quiet=args.quiet,
        )

    if args.command == "install-hook":
        from .guard import install_hook

        target_repo = Path(os.path.abspath(args.repo or repo))
        return install_hook(target_repo, force=args.force)

    parser.print_help()  # pragma: no cover
    return 2
