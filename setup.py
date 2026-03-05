"""setup.py — Configura a base de conhecimento do LION.

Cria uma base dedicada, faz upload de todos os documentos
da pasta docs/ como fontes e salva o notebook_id em .env.

Uso:
    python setup.py
    python setup.py --notebook-id <id_existente>  # Reaproveita base existente
    python setup.py --list                         # Lista bases disponíveis
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

try:
    import html2text as _html2text
except ImportError:  # pragma: no cover
    _html2text = None

DOCS_DIR = Path(__file__).parent / "docs"
ENV_FILE = Path(__file__).parent / ".env"
NOTEBOOK_TITLE = "LION"


async def list_notebooks() -> None:
    """Lista todas as bases de conhecimento disponíveis."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        if not notebooks:
            print("Nenhuma base de conhecimento encontrada.")
            return
        print(f"\n{'ID':<40} {'Nome':<50} {'Fontes':>6}")
        print("-" * 100)
        for nb in notebooks:
            print(f"{nb.id:<40} {nb.title:<50} {nb.sources_count:>6}")
        print()


def convert_html_to_txt() -> None:
    """Converte todos os .html da pasta docs/ para .txt (UTF-8).

    Tenta decodificar o HTML como UTF-8; se falhar, usa latin-1.
    Arquivos já convertidos são sobrescritos para garantir consistência.
    """
    if _html2text is None:
        print("[AVISO] html2text não instalado — pulando conversão de HTML.")
        return

    html_files = list(DOCS_DIR.glob("*.html"))
    if not html_files:
        return

    h = _html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True

    print(f"Convertendo {len(html_files)} arquivo(s) HTML para TXT...")
    for html_file in sorted(html_files):
        txt_file = html_file.with_suffix(".txt")
        try:
            content = html_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = html_file.read_text(encoding="latin-1")
        txt_file.write_text(h.handle(content), encoding="utf-8")
        print(f"  ✔  {html_file.name} → {txt_file.name}")
    print()


async def setup_notebook(notebook_id: str | None = None, notebook_title: str | None = None) -> str:
    """Cria (ou reaproveita) a base de conhecimento e importa todos os docs como fontes.

    Returns:
        str: ID da base de conhecimento configurada.
    """
    from notebooklm import NotebookLMClient

    title = notebook_title or NOTEBOOK_TITLE

    convert_html_to_txt()
    doc_files = sorted(DOCS_DIR.glob("*.md")) + sorted(DOCS_DIR.glob("*.pdf")) + sorted(DOCS_DIR.glob("*.txt"))
    if not doc_files:
        print(f"[ERRO] Nenhum documento encontrado em {DOCS_DIR}")
        sys.exit(1)

    async with await NotebookLMClient.from_storage() as client:

        # ── Base de conhecimento ─────────────────────────────────────────
        if notebook_id:
            nb = await client.notebooks.get(notebook_id)
            print(f"\u2714 Usando base existente: {nb.title} ({nb.id})")
        else:
            print(f"Criando base de conhecimento '{title}'...")
            nb = await client.notebooks.create(title)
            print(f"\u2714 Base criada: {nb.id}")

        # ── Fontes já existentes ──────────────────────────────────────────────
        existing_sources = await client.sources.list(nb.id)
        existing_titles = {s.title for s in existing_sources}

        # ── Upload dos documentos ─────────────────────────────────────────────
        print(f"\nImportando {len(doc_files)} documento(s) para o notebook...")
        added = 0
        skipped = 0

        for doc in doc_files:
            title = doc.stem.replace("-", " ").replace("_", " ").title()

            if title in existing_titles:
                print(f"  ⏭  {doc.name} — já importado, pulando")
                skipped += 1
                continue

            print(f"  ↑  {doc.name}...", end=" ", flush=True)
            try:
                source = await client.sources.add_file(nb.id, doc)
                print(f"✔ ({source.id[:8]}…)")
                added += 1
            except Exception as e:
                print(f"✗ Erro: {e}")

        print(f"\n\u2714 {added} adicionado(s), {skipped} já existia(m).")

        # ── Salva configuração no .env ────────────────────────────────
        _save_env(nb.id)
        print(f"\n\u2714 Configuração salva em {ENV_FILE}")
        print(f"  CHATBOT_NOTEBOOK_ID={nb.id}")
        print("\nAgora execute:\n  python app.py\n")

        return nb.id


def _save_env(notebook_id: str) -> None:
    """Persiste o notebook_id no arquivo .env da demo."""
    lines: list[str] = []
    found = False

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("CHATBOT_NOTEBOOK_ID="):
                lines.append(f"CHATBOT_NOTEBOOK_ID={notebook_id}")
                found = True
            else:
                lines.append(line)

    if not found:
        lines.append(f"CHATBOT_NOTEBOOK_ID={notebook_id}")

    ENV_FILE.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LION — Configura a base de conhecimento e indexa os documentos."
    )
    parser.add_argument(
        "--notebook-id",
        metavar="ID",
        help="ID de uma base existente para reaproveitar.",
    )
    parser.add_argument(
        "--name",
        metavar="NOME",
        help="Nome da base de conhecimento (ignora a pergunta interativa).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista todas as bases de conhecimento disponíveis e sai.",
    )
    args = parser.parse_args()

    if args.list:
        asyncio.run(list_notebooks())
        return

    # Determina o nome da base (somente quando criar uma nova)
    if not args.notebook_id:
        if args.name:
            notebook_title = args.name.strip()
        else:
            resposta = input(
                f"Nome da base de conhecimento [{NOTEBOOK_TITLE}]: "
            ).strip()
            notebook_title = resposta if resposta else NOTEBOOK_TITLE
    else:
        notebook_title = None  # reaproveita o nome já existente

    asyncio.run(setup_notebook(notebook_id=args.notebook_id, notebook_title=notebook_title))


if __name__ == "__main__":
    main()
