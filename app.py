"""app.py — Interface gráfica do Chatbot Institucional (Gradio).

Lê o CHATBOT_NOTEBOOK_ID do arquivo .env (gerado pelo setup.py) e sobe
uma interface web com histórico de conversa, listagem de fontes e
painel de status.

Uso:
    python app.py
    python app.py --notebook-id <id>
    python app.py --port 7861 --share   # Gera link público temporário
"""

import argparse
import asyncio
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

import gradio as gr

# ── Configuração ───────────────────────────────────────────────────────────────
ENV_FILE = Path(__file__).parent / ".env"
NOTEBOOK_TITLE = "Lion Chatbot"
APP_TITLE = "🦁 Lion Chatbot"
APP_DESCRIPTION = "Assistente técnico inteligente alimentado por documentações reais via Google NotebookLM."

# Estado global da sessão (thread-safe via asyncio + Gradio state)
_client = None
_notebook_id: str | None = None
_sources: list = []
_loop: asyncio.AbstractEventLoop | None = None


# ── Utilitários ────────────────────────────────────────────────────────────────

def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _run_async(coro):
    """Executa uma coroutine no event loop dedicado."""
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=60)


# ── Inicialização do cliente ───────────────────────────────────────────────────

async def _init_client(notebook_id: str):
    """Inicializa o cliente NotebookLM e carrega metadados do notebook."""
    global _client, _notebook_id, _sources
    from notebooklm import NotebookLMClient

    _client = await NotebookLMClient.from_storage()
    await _client.__aenter__()
    _notebook_id = notebook_id

    nb = await _client.notebooks.get(_notebook_id)
    _sources = await _client.sources.list(_notebook_id)

    return nb, _sources


# ── Lógica do chat ─────────────────────────────────────────────────────────────

async def _ask(question: str, conversation_id: str | None):
    """Envia pergunta ao NotebookLM e retorna (resposta, novo conversation_id)."""
    result = await _client.chat.ask(
        _notebook_id,
        question,
        conversation_id=conversation_id,
    )
    return result.answer, result.conversation_id


def chat_fn(message: str, history: list, conversation_id: str):
    """Função principal chamada pelo Gradio a cada mensagem."""
    if not message.strip():
        return history, conversation_id

    if _client is None or _notebook_id is None:
        history.append({"role": "assistant", "content": "⚠️ Cliente não inicializado. Reinicie o app."})
        return history, conversation_id

    try:
        answer, new_conv_id = _run_async(_ask(message.strip(), conversation_id or None))
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": answer})
        return history, new_conv_id or conversation_id
    except Exception as e:
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": f"❌ Erro ao consultar o NotebookLM: {e}"})
        return history, conversation_id


def reset_conversation():
    """Limpa o histórico e inicia nova conversa."""
    return [], ""


# ── Construção da interface ────────────────────────────────────────────────────

def build_sources_markdown(sources: list) -> str:
    if not sources:
        return "_Nenhuma fonte carregada._"
    lines = []
    for src in sources:
        kind = getattr(src, "kind", "doc")
        lines.append(f"- 📄 **{src.title}** `{kind}`")
    return "\n".join(lines)


def build_app(notebook_title: str, sources: list) -> gr.Blocks:
    sources_md = build_sources_markdown(sources)
    source_count = len(sources)

    with gr.Blocks(title=APP_TITLE) as app:

        # ── Estado interno ────────────────────────────────────────────────────
        conversation_id = gr.State("")

        # ── Cabeçalho ─────────────────────────────────────────────────────────
        with gr.Row():
            with gr.Column(scale=8):
                gr.Markdown(f"# {APP_TITLE}")
                gr.Markdown(APP_DESCRIPTION)
            with gr.Column(scale=2):
                gr.Markdown(
                    f"**Base de conhecimento:** {notebook_title}  \n"
                    f"**Fontes:** {source_count} documento(s)  \n"
                    f"**Motor:** Google NotebookLM"
                )

        gr.HTML("<hr style='margin: 8px 0; border-color: #e2e8f0;'>")

        # ── Layout principal ──────────────────────────────────────────────────
        with gr.Row(equal_height=True):

            # Painel esquerdo — chat
            with gr.Column(scale=7):
                chatbot = gr.Chatbot(
                    elem_id="chatbot",
                    label="Conversa",
                    height=520,
                    layout="bubble",
                    avatar_images=(
                        None,
                        "https://www.gstatic.com/notebooklm/notebooklm_favicon_v2.ico",
                    ),
                    buttons=["copy"],
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Digite sua pergunta sobre a documentação...",
                        label="",
                        scale=8,
                        lines=1,
                        max_lines=4,
                        show_label=False,
                        autofocus=True,
                    )
                    send_btn = gr.Button(
                        "Enviar ➤",
                        variant="primary",
                        elem_id="send-btn",
                        scale=1,
                    )

                with gr.Row():
                    reset_btn = gr.Button(
                        "🔄 Nova conversa",
                        variant="secondary",
                        elem_id="reset-btn",
                        scale=1,
                    )
                    with gr.Column(scale=5):
                        gr.Markdown(
                            "_Pressione **Enter** para enviar ou **Shift+Enter** para nova linha._"
                        )

            # Painel direito — informações
            with gr.Column(scale=3):
                with gr.Accordion("📚 Fontes carregadas", open=True):
                    gr.Markdown(sources_md)

                with gr.Accordion("💡 Sugestões de perguntas", open=True):
                    gr.Markdown(
                        "- Como faço para autenticar na API?\n"
                        "- Quais são os planos de rate limiting?\n"
                        "- O que fazer quando recebo erro 403?\n"
                        "- Como configurar webhooks?\n"
                        "- O SDK suporta chamadas assíncronas?\n"
                        "- Como importar dados em lote?\n"
                        "- Qual a diferença entre os ambientes?"
                    )

                with gr.Accordion("ℹ️ Sobre", open=False):
                    gr.Markdown(
                        "**Lion Chatbot** é um assistente técnico que utiliza o "
                        "**Google NotebookLM** como motor de IA para responder "
                        "perguntas com base nas documentações carregadas.\n\n"
                        "As respostas são geradas exclusivamente a partir do "
                        "conteúdo dos documentos indexados, garantindo precisão "
                        "e rastreabilidade das informações."
                    )

        # ── Eventos ───────────────────────────────────────────────────────────

        # Envio pelo botão
        send_btn.click(
            fn=chat_fn,
            inputs=[msg_input, chatbot, conversation_id],
            outputs=[chatbot, conversation_id],
        ).then(
            fn=lambda: "",
            outputs=msg_input,
        )

        # Envio pelo Enter
        msg_input.submit(
            fn=chat_fn,
            inputs=[msg_input, chatbot, conversation_id],
            outputs=[chatbot, conversation_id],
        ).then(
            fn=lambda: "",
            outputs=msg_input,
        )

        # Reset da conversa
        reset_btn.click(
            fn=reset_conversation,
            outputs=[chatbot, conversation_id],
        )

    return app


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    global _loop

    parser = argparse.ArgumentParser(
        description="Interface gráfica do chatbot institucional — motor NotebookLM."
    )
    parser.add_argument("--notebook-id", metavar="ID", help="ID do notebook (sobrescreve .env).")
    parser.add_argument("--port", type=int, default=7860, help="Porta HTTP (padrão: 7860).")
    parser.add_argument("--share", action="store_true", help="Gera link público temporário via Gradio.")
    args = parser.parse_args()

    # Determina notebook_id
    notebook_id = args.notebook_id
    if not notebook_id:
        env = _load_env()
        notebook_id = env.get("CHATBOT_NOTEBOOK_ID") or os.environ.get("CHATBOT_NOTEBOOK_ID")

    if not notebook_id:
        print("❌ notebook_id não configurado.")
        print("Execute primeiro: python setup.py")
        sys.exit(1)

    # Sobe event loop dedicado em thread separada
    _loop = asyncio.new_event_loop()
    t = threading.Thread(target=_loop.run_forever, daemon=True)
    t.start()

    # Inicializa cliente
    print("Conectando ao NotebookLM...")
    try:
        nb, sources = _run_async(_init_client(notebook_id))
    except Exception as e:
        print(f"❌ Falha ao conectar: {e}")
        print("Verifique a autenticação com: notebooklm auth check")
        sys.exit(1)

    print(f"✔ Notebook: {nb.title}")
    print(f"✔ Fontes: {len(sources)} documento(s)")
    print(f"✔ Iniciando interface em http://localhost:{args.port}\n")

    app = build_app(nb.title, sources)
    app.launch(
        server_name="0.0.0.0",
        server_port=args.port,
        share=args.share,
        favicon_path=None,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
        ),
        css="""
        #send-btn { min-width: 100px; }
        #reset-btn { min-width: 100px; }
        footer { display: none !important; }
        """,
    )


if __name__ == "__main__":
    main()
