"""chatbot.py — Lion Chatbot interativo via terminal, alimentado pelo NotebookLM.

Lê o CHATBOT_NOTEBOOK_ID do arquivo .env (gerado pelo setup.py) e inicia
um loop de conversa no terminal. O histórico de contexto é mantido via
conversation_id entre as perguntas da mesma sessão.

Uso:
    python chatbot.py
    python chatbot.py --notebook-id <id>   # Sobrescreve o .env
    python chatbot.py --reset              # Nova conversa (limpa histórico)

Comandos especiais durante o chat:
    /sair ou /exit   — Encerra o chatbot
    /novo            — Inicia nova conversa (limpa contexto)
    /historico       — Exibe o histórico da sessão atual
    /fontes          — Lista as fontes do notebook
    /ajuda           — Exibe a ajuda
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"

# ── Cores ANSI ────────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
DIM = "\033[2m"
BLUE = "\033[94m"


def _load_env() -> dict[str, str]:
    """Carrega variáveis do arquivo .env da demo."""
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def _print_header() -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  🦁  Lion Chatbot{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{DIM}  Motor: Google NotebookLM  |  Digite /ajuda para comandos{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 60}{RESET}\n")


def _print_help() -> None:
    print(f"\n{BOLD}Comandos disponíveis:{RESET}")
    cmds = [
        ("/sair, /exit", "Encerra o chatbot"),
        ("/novo",        "Inicia nova conversa (limpa o contexto)"),
        ("/historico",   "Exibe o histórico da sessão"),
        ("/fontes",      "Lista as fontes do notebook"),
        ("/ajuda",       "Exibe esta ajuda"),
    ]
    for cmd, desc in cmds:
        print(f"  {CYAN}{cmd:<20}{RESET} {desc}")
    print()


def _format_answer(answer: str) -> str:
    """Formata a resposta com indentação leve."""
    lines = answer.strip().splitlines()
    return "\n".join(f"  {line}" for line in lines)


async def run_chatbot(notebook_id: str, reset: bool = False) -> None:
    """Loop principal do chatbot."""
    from notebooklm import NotebookLMClient, RPCError

    history: list[dict] = []   # {"role": "user"|"bot", "text": str, "time": str}
    conversation_id: str | None = None

    _print_header()

    async with await NotebookLMClient.from_storage() as client:

        # ── Valida notebook ───────────────────────────────────────────────────
        try:
            nb = await client.notebooks.get(notebook_id)
        except Exception as e:
            print(f"{RED}[ERRO] Notebook não encontrado: {e}{RESET}")
            print(f"Execute primeiro: {YELLOW}python setup.py{RESET}\n")
            return

        print(f"{GREEN}✔ Conectado ao notebook:{RESET} {BOLD}{nb.title}{RESET}")

        sources = await client.sources.list(nb.id)
        print(f"{GREEN}✔ Fontes carregadas:{RESET} {len(sources)} documento(s)\n")

        if not sources:
            print(f"{YELLOW}⚠ Nenhuma fonte encontrada. Execute python setup.py primeiro.{RESET}\n")
            return

        print(f"{DIM}Faça sua pergunta sobre a documentação. Digite /ajuda para ver os comandos.{RESET}\n")

        # ── Loop de conversa ──────────────────────────────────────────────────
        while True:
            try:
                user_input = input(f"{BOLD}{BLUE}Você:{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{DIM}Encerrando...{RESET}\n")
                break

            if not user_input:
                continue

            # ── Comandos especiais ────────────────────────────────────────────
            cmd = user_input.lower()

            if cmd in ("/sair", "/exit", "sair", "exit"):
                print(f"\n{DIM}Até logo! 👋{RESET}\n")
                break

            if cmd == "/ajuda":
                _print_help()
                continue

            if cmd == "/novo":
                conversation_id = None
                history.clear()
                print(f"\n{YELLOW}🔄 Nova conversa iniciada.{RESET}\n")
                continue

            if cmd == "/historico":
                if not history:
                    print(f"\n{DIM}Nenhuma mensagem nesta sessão.{RESET}\n")
                else:
                    print(f"\n{BOLD}── Histórico da sessão ──{RESET}")
                    for msg in history:
                        role_label = (
                            f"{BLUE}Você{RESET}"
                            if msg["role"] == "user"
                            else f"{GREEN}Bot{RESET}"
                        )
                        print(f"{DIM}[{msg['time']}]{RESET} {role_label}: {msg['text'][:120]}{'…' if len(msg['text']) > 120 else ''}")
                    print()
                continue

            if cmd == "/fontes":
                print(f"\n{BOLD}── Fontes do notebook ──{RESET}")
                for src in sources:
                    print(f"  • {src.title} {DIM}({src.kind}){RESET}")
                print()
                continue

            # ── Pergunta ao NotebookLM ────────────────────────────────────────
            now = datetime.now().strftime("%H:%M:%S")
            history.append({"role": "user", "text": user_input, "time": now})

            print(f"{DIM}Consultando documentação...{RESET}", end="\r", flush=True)

            try:
                result = await client.chat.ask(
                    nb.id,
                    user_input,
                    conversation_id=conversation_id,
                )
                conversation_id = result.conversation_id

                # Limpa a linha "Consultando..."
                print(" " * 40, end="\r")

                answer = result.answer
                history.append({"role": "bot", "text": answer, "time": datetime.now().strftime("%H:%M:%S")})

                print(f"\n{BOLD}{GREEN}🦁 Lion:{RESET}")
                print(_format_answer(answer))

                # Exibe fontes referenciadas (se disponíveis)
                if hasattr(result, "references") and result.references:
                    refs = [r.title for r in result.references if hasattr(r, "title")]
                    if refs:
                        print(f"\n  {DIM}📎 Fontes: {', '.join(refs)}{RESET}")

                print()

            except RPCError as e:
                print(" " * 40, end="\r")
                print(f"\n{RED}[ERRO API] {e}{RESET}\n")
            except Exception as e:
                print(" " * 40, end="\r")
                print(f"\n{RED}[ERRO] {e}{RESET}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chatbot institucional interativo — motor NotebookLM."
    )
    parser.add_argument(
        "--notebook-id",
        metavar="ID",
        help="ID do notebook (sobrescreve o .env).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Inicia sem histórico de conversa anterior.",
    )
    args = parser.parse_args()

    # Determina o notebook_id
    notebook_id = args.notebook_id
    if not notebook_id:
        env = _load_env()
        notebook_id = env.get("CHATBOT_NOTEBOOK_ID") or os.environ.get("CHATBOT_NOTEBOOK_ID")

    if not notebook_id:
        print(f"{RED}[ERRO] notebook_id não configurado.{RESET}")
        print(f"Execute primeiro: {YELLOW}python setup.py{RESET}")
        sys.exit(1)

    asyncio.run(run_chatbot(notebook_id=notebook_id, reset=args.reset))


if __name__ == "__main__":
    main()
