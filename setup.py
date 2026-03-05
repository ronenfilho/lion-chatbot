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
import subprocess
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


async def setup_notebook(notebook_id: str | None = None, notebook_title: str | None = None, process_docs: bool = True) -> str:
    """Cria (ou reaproveita) a base de conhecimento e importa todos os docs como fontes.

    Returns:
        str: ID da base de conhecimento configurada.
    """
    from notebooklm import NotebookLMClient

    title = notebook_title or NOTEBOOK_TITLE

    if not process_docs:
        async with await NotebookLMClient.from_storage() as client:
            nb = await client.notebooks.get(notebook_id)
            print(f"✔ Usando base existente: {nb.title} ({nb.id})")
            _save_env(nb.id)
            print(f"\n✔ Configuração salva em {ENV_FILE}")
            print(f"  CHATBOT_NOTEBOOK_ID={nb.id}")
            print("\nAgora execute:\n  python app.py\n")
            return nb.id

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


# ── Deploy HuggingFace Spaces ───────────────────────────────────────────────────────────────

def _hf_token() -> str | None:
    token_file = Path.home() / ".cache" / "huggingface" / "token"
    if token_file.exists():
        return token_file.read_text().strip()
    return os.environ.get("HF_TOKEN")


def _hf_username(token: str) -> str | None:
    """Retorna o username do usuário autenticado no HuggingFace."""
    import urllib.request
    req = urllib.request.Request(
        "https://huggingface.co/api/whoami-v2",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("name")
    except Exception:
        return None


def _list_hf_spaces(token: str, username: str) -> list[dict]:
    """Lista os Spaces do usuário no HuggingFace."""
    import urllib.request
    url = f"https://huggingface.co/api/spaces?author={username}&limit=50"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return []


def _create_hf_space(token: str, username: str, space_name: str, private: bool = False) -> str:
    """Cria um novo Space no HuggingFace e retorna o repo_id."""
    import urllib.request
    payload = json.dumps({
        "type": "space",
        "name": space_name,
        "sdk": "gradio",
        "private": private,
    }).encode()
    req = urllib.request.Request(
        "https://huggingface.co/api/repos/create",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        return data.get("url", "").rstrip("/").split("/")[-1]


def _push_secret(token: str, space: str, key: str, value: str) -> None:
    payload = json.dumps({"key": key, "value": value}).encode()
    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://huggingface.co/api/spaces/{space}/secrets",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "--data-binary", payload.decode(),
    ], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode())


def _restart_space(token: str, space: str) -> None:
    subprocess.run([
        "curl", "-s", "-X", "POST",
        f"https://huggingface.co/api/spaces/{space}/restart",
        "-H", f"Authorization: Bearer {token}",
    ], capture_output=True)


def _update_space_readme_via_api(token: str, space: str) -> None:
    """Atualiza o campo title do frontmatter do README.md diretamente no Space via API."""
    import re
    import urllib.request

    short_name = space.split("/")[-1]
    new_title = f"🦁 LION - {short_name}"

    # Busca o README.md atual do Space
    url_get = f"https://huggingface.co/spaces/{space}/raw/main/README.md"
    req_get = urllib.request.Request(url_get, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req_get, timeout=10) as resp:
            content = resp.read().decode("utf-8")
    except Exception as e:
        print(f"⚠ Não foi possível ler o README.md do Space: {e}")
        return

    updated = re.sub(r"(?m)^title:.*$", f"title: {new_title}", content)
    # Garante colorFrom e colorTo
    if re.search(r"(?m)^colorFrom:", updated):
        updated = re.sub(r"(?m)^colorFrom:.*$", "colorFrom: yellow", updated)
    else:
        updated = re.sub(r"(?m)^(title:.*\n)", r"\1colorFrom: yellow\n", updated)
    if re.search(r"(?m)^colorTo:", updated):
        updated = re.sub(r"(?m)^colorTo:.*$", "colorTo: yellow", updated)
    else:
        updated = re.sub(r"(?m)^(colorFrom:.*\n)", r"\1colorTo: yellow\n", updated)
    if updated == content:
        return  # nada a fazer

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)
        api.upload_file(
            path_or_fileobj=updated.encode("utf-8"),
            path_in_repo="README.md",
            repo_id=space,
            repo_type="space",
            commit_message=f"chore: update Space title to '{new_title}'",
        )
        print(f"✔ Título do Space atualizado: {new_title}")
    except Exception as e:
        print(f"⚠ Não foi possível atualizar o título do Space: {e}")


def _git_push_space(remote_url: str) -> None:
    """Adiciona remote 'space' se não existir e faz push."""
    remotes = subprocess.run(["git", "remote"], capture_output=True, text=True).stdout.split()
    if "space" not in remotes:
        subprocess.run(["git", "remote", "add", "space", remote_url], check=True)
    else:
        subprocess.run(["git", "remote", "set-url", "space", remote_url], check=True)
    subprocess.run(["git", "push", "space", "main", "--force"], check=True)


def deploy_flow(notebook_id: str) -> None:
    """Fluxo interativo de publicação no HuggingFace Spaces."""
    token = _hf_token()
    if not token:
        print("\n⚠ Token do HuggingFace não encontrado. Pulando deploy.")
        print("  Execute: huggingface-cli login")
        return

    username = _hf_username(token)
    if not username:
        print("\n⚠ Não foi possível obter o usuário HuggingFace. Pulando deploy.")
        return

    print(f"\n{'─' * 50}")
    resp = input("Deseja publicar no HuggingFace Spaces? [s/N] ").strip().lower()
    if resp not in ("s", "sim", "y", "yes"):
        print("Deploy ignorado.")
        return

    # ── Lista spaces existentes ───────────────────────────────────────
    spaces = _list_hf_spaces(token, username)
    space_repo_id: str

    print(f"\nSeus Spaces ({username}):")
    print(f"  {'0.':<4} Criar novo Space")
    for i, s in enumerate(spaces, start=1):
        name = s.get("id", s.get("name", "?"))
        sdk  = s.get("cardData", {}).get("sdk", "-")
        print(f"  {i}. {name}  [{sdk}]")

    while True:
        escolha = input("\nEscolha o número do Space (ou 0 para criar novo): ").strip()
        if not escolha.isdigit() or int(escolha) > len(spaces):
            print("Opção inválida, tente novamente.")
            continue
        break

    idx = int(escolha)
    if idx == 0:
        space_name = input("Nome do novo Space: ").strip()
        if not space_name:
            print("Nome inválido. Deploy cancelado.")
            return
        # Sanitiza: substitui caracteres inválidos por hífen
        import re as _re
        space_name = _re.sub(r"[^A-Za-z0-9._-]+", "-", space_name).strip("-")

        print("\nVisibilidade do Space:")
        print("  1. 🌐 Público")
        print("  2. 🔒 Privado")
        while True:
            vis = input("Escolha [1/2]: ").strip()
            if vis in ("1", "2"):
                break
            print("Opção inválida, tente novamente.")
        private = vis == "2"

        print(f"\nCriando Space '{space_name}' ({'privado' if private else 'público'})...")
        _create_hf_space(token, username, space_name, private=private)
        space_repo_id = f"{username}/{space_name}"
        vis_label = "🔒 privado" if private else "🌐 público"
        print(f"✔ Space criado ({vis_label}): https://huggingface.co/spaces/{space_repo_id}")
    else:
        space_repo_id = spaces[idx - 1].get("id", spaces[idx - 1].get("name"))
        print(f"✔ Space selecionado: {space_repo_id}")

    # ── Push do código ──────────────────────────────────────────────
    hf_token_in_url = token
    remote_url = f"https://{username}:{hf_token_in_url}@huggingface.co/spaces/{space_repo_id}"
    print("\n⬆ Enviando código para o Space...")
    try:
        _git_push_space(remote_url)
        print("✔ Código enviado")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no push: {e}")
        return

    # ── Atualiza título no README.md do Space ────────────────────────
    _update_space_readme_via_api(token, space_repo_id)

    # ── Secrets ─────────────────────────────────────────────────
    print("🔑 Configurando secrets...")
    auth_file = Path.home() / ".notebooklm" / "storage_state.json"
    try:
        _push_secret(token, space_repo_id, "CHATBOT_NOTEBOOK_ID", notebook_id)
        print("✔ CHATBOT_NOTEBOOK_ID configurado")
        if auth_file.exists():
            _push_secret(token, space_repo_id, "NOTEBOOKLM_AUTH_JSON", auth_file.read_text())
            print("✔ NOTEBOOKLM_AUTH_JSON configurado")
        else:
            print("⚠ storage_state.json não encontrado — configure NOTEBOOKLM_AUTH_JSON manualmente")
    except Exception as e:
        print(f"❌ Erro ao configurar secrets: {e}")
        return

    # ── Restart ───────────────────────────────────────────────────
    _restart_space(token, space_repo_id)
    print(f"\n✅ Deploy concluído!")
    print(f"   https://huggingface.co/spaces/{space_repo_id}")


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


async def _prompt_notebook_selection(preferred_name: str | None = None) -> tuple[str | None, str | None, bool]:
    """Pergunta ao usuário se quer usar uma base existente ou criar uma nova.

    Returns:
        (notebook_id, notebook_title, process_docs):
            notebook_id=None indica criação de nova base.
            process_docs indica se deve importar os documentos do docs/.
    """
    from notebooklm import NotebookLMClient

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()

    print(f"\n{'─' * 60}")
    print("Bases de conhecimento disponíveis:\n")
    print(f"  {'0.':<4} Criar nova base")
    for i, nb in enumerate(notebooks, start=1):
        print(f"  {i}. {nb.title}  [{nb.id[:8]}…]  ({nb.sources_count} fonte(s))")
    print()

    while True:
        escolha = input("Escolha o número da base (ou 0 para criar nova): ").strip()
        if escolha.isdigit() and int(escolha) <= len(notebooks):
            break
        print("Opção inválida, tente novamente.")

    idx = int(escolha)
    if idx == 0:
        if preferred_name:
            notebook_title = preferred_name.strip()
        else:
            resposta = input(f"Nome da nova base [{NOTEBOOK_TITLE}]: ").strip()
            notebook_title = resposta if resposta else NOTEBOOK_TITLE
        return None, notebook_title, True
    else:
        selected = notebooks[idx - 1]
        print(f"✔ Base selecionada: {selected.title} ({selected.id})")
        resp = input("Deseja importar os documentos da pasta docs/? [S/n] ").strip().lower()
        process_docs = resp not in ("n", "nao", "não", "no")
        return selected.id, None, process_docs


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

    # Determina o notebook_id e o nome da base
    notebook_id_resolved = args.notebook_id
    notebook_title: str | None = None
    process_docs = True

    if not notebook_id_resolved:
        notebook_id_resolved, notebook_title, process_docs = asyncio.run(
            _prompt_notebook_selection(preferred_name=args.name)
        )

    notebook_id = asyncio.run(setup_notebook(notebook_id=notebook_id_resolved, notebook_title=notebook_title, process_docs=process_docs))
    deploy_flow(notebook_id)


if __name__ == "__main__":
    main()
