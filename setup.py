"""setup.py — Configura o notebook institucional no NotebookLM.

Cria um notebook dedicado ao chatbot, faz upload de todos os documentos
técnicos da pasta docs/ como fontes e salva o notebook_id em .env.

Uso:
    python setup.py
    python setup.py --notebook-id <id_existente>  # Reaproveita notebook
    python setup.py --list                         # Lista notebooks existentes
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "docs"
ENV_FILE = Path(__file__).parent / ".env"
NOTEBOOK_TITLE = "Lion Chatbot"


async def list_notebooks() -> None:
    """Lista todos os notebooks disponíveis na conta."""
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        if not notebooks:
            print("Nenhum notebook encontrado.")
            return
        print(f"\n{'ID':<40} {'Título':<50} {'Fontes':>6}")
        print("-" * 100)
        for nb in notebooks:
            print(f"{nb.id:<40} {nb.title:<50} {nb.sources_count:>6}")
        print()


async def setup_notebook(notebook_id: str | None = None) -> str:
    """Cria (ou reaproveita) o notebook e importa todos os docs como fontes.

    Returns:
        str: ID do notebook configurado.
    """
    from notebooklm import NotebookLMClient

    doc_files = sorted(DOCS_DIR.glob("*.md")) + sorted(DOCS_DIR.glob("*.pdf"))
    if not doc_files:
        print(f"[ERRO] Nenhum documento encontrado em {DOCS_DIR}")
        sys.exit(1)

    async with await NotebookLMClient.from_storage() as client:

        # ── Notebook ──────────────────────────────────────────────────────────
        if notebook_id:
            nb = await client.notebooks.get(notebook_id)
            print(f"✔ Usando notebook existente: {nb.title} ({nb.id})")
        else:
            print(f"Criando notebook '{NOTEBOOK_TITLE}'...")
            nb = await client.notebooks.create(NOTEBOOK_TITLE)
            print(f"✔ Notebook criado: {nb.id}")

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

        print(f"\n✔ {added} adicionado(s), {skipped} já existia(m).")

        # ── Salva configuração no .env ────────────────────────────────────────
        _save_env(nb.id)
        print(f"\n✔ Configuração salva em {ENV_FILE}")
        print(f"  CHATBOT_NOTEBOOK_ID={nb.id}")
        print("\nAgora execute:\n  python chatbot.py\n")

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
        description="Configura o notebook do Lion Chatbot no NotebookLM."
    )
    parser.add_argument(
        "--notebook-id",
        metavar="ID",
        help="ID de um notebook existente para reaproveitar.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista todos os notebooks da conta e sai.",
    )
    args = parser.parse_args()

    if args.list:
        asyncio.run(list_notebooks())
        return

    asyncio.run(setup_notebook(notebook_id=args.notebook_id))


if __name__ == "__main__":
    main()
