"""app.py — Interface web do LION (Legal Interpretation and Official Norms).

Lê configurações de variáveis de ambiente ou do arquivo .env local:
  - CHATBOT_NOTEBOOK_ID  : ID da base de conhecimento
  - NOTEBOOKLM_AUTH_JSON : JSON do storage_state (para Hugging Face Spaces)

Uso local:
    python app.py
    python app.py --notebook-id <id>
    python app.py --port 7861 --share   # Gera link público temporário

Hugging Face Spaces:
    Configure CHATBOT_NOTEBOOK_ID e NOTEBOOKLM_AUTH_JSON como Secrets.
"""

import argparse
import asyncio
import os
import sys
import threading
from pathlib import Path

import gradio as gr

# ── Configuração ───────────────────────────────────────────────────────────────
ENV_FILE = Path(__file__).parent / ".env"
NOTEBOOK_TITLE = "LION"
APP_TITLE = "🦁 LION"
APP_DESCRIPTION = "Legal Interpretation and Official Norms"

# Estado global da sessão (thread-safe via asyncio + Gradio state)
_client = None
_notebook_id: str | None = None
_sources: list = []
_suggestions: list[str] = []
_loop: asyncio.AbstractEventLoop | None = None


# ── Utilitários ────────────────────────────────────────────────────────────────

def _load_env() -> dict[str, str]:
    """Carrega variáveis do arquivo .env local (fallback para uso local)."""
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _get_notebook_id() -> str | None:
    """Obtém o notebook_id de variáveis de ambiente ou .env local."""
    # 1. Variável de ambiente direta (HF Spaces secrets ou export local)
    notebook_id = os.environ.get("CHATBOT_NOTEBOOK_ID")
    if notebook_id:
        return notebook_id.strip()
    # 2. Arquivo .env local (gerado pelo setup.py)
    env = _load_env()
    return env.get("CHATBOT_NOTEBOOK_ID")


def _run_async(coro):
    """Executa uma coroutine no event loop dedicado."""
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=60)


# ── Inicialização do cliente ───────────────────────────────────────────────────

async def _init_client(notebook_id: str):
    """Inicializa o cliente e carrega metadados do notebook."""
    global _client, _notebook_id, _sources
    from notebooklm import NotebookLMClient

    _client = await NotebookLMClient.from_storage()
    await _client.__aenter__()
    _notebook_id = notebook_id

    nb = await _client.notebooks.get(_notebook_id)
    _sources = await _client.sources.list(_notebook_id)

    return nb, _sources


async def _generate_suggestions() -> list[str]:
    """Consulta a base para gerar sugestões de perguntas contextuais."""
    prompt = (
        "Com base nos documentos disponíveis nesta base de conhecimento, "
        "gere exatamente 6 sugestões de perguntas que um usuário poderia fazer. "
        "As perguntas devem ser objetivas, relevantes e variadas. "
        "Retorne apenas as perguntas, uma por linha, sem numeração, "
        "sem marcadores e sem nenhum texto adicional."
    )
    try:
        result = await _client.chat.ask(_notebook_id, prompt)
        lines = [l.strip() for l in result.answer.strip().splitlines() if l.strip()]
        # filtra linhas que parecem perguntas (terminam em ? ou têm conteúdo)
        questions = [l.lstrip("-•*0123456789. ") for l in lines if len(l) > 10][:6]
        return questions if questions else []
    except Exception:
        return []


# Instrução de contexto injetada em cada pergunta
_PROMPT_INSTRUCTIONS = (
    "Responda de forma direta e objetiva. "
    "Não inclua referências numéricas como [1], [2] ou similares na resposta."
)


# ── Lógica do chat ─────────────────────────────────────────────────────────────

async def _ask(question: str, conversation_id: str | None):
    """Envia pergunta à base de conhecimento e retorna (resposta, novo conversation_id)."""
    full_question = f"{_PROMPT_INSTRUCTIONS}\n\n{question}"
    result = await _client.chat.ask(
        _notebook_id,
        full_question,
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
        history.append({"role": "assistant", "content": f"❌ Erro ao processar sua consulta: {e}"})
        return history, conversation_id


def reset_conversation():
    """Limpa o histórico e inicia nova conversa."""
    return [], ""


# ── Construção da interface ────────────────────────────────────────────────────

def build_sources_markdown(sources: list) -> str:
    if not sources:
        return "_Nenhuma fonte carregada._"
    icon_map = {"pdf": "📕", "md": "📝", "txt": "📄", "html": "🌐"}
    lines = []
    for src in sources:
        title = src.title or "Sem título"
        ext = title.rsplit(".", 1)[-1].lower() if "." in title else ""
        icon = icon_map.get(ext, "📄")
        lines.append(f"- {icon} {title}")
    return "\n".join(lines)


def build_app(notebook_title: str, sources: list, suggestions: list[str]) -> gr.Blocks:
    sources_md = build_sources_markdown(sources)
    source_count = len(sources)
    suggestions_md = "\n".join(f"- {q}" for q in suggestions) if suggestions else (
        "- Quais são as principais obrigações previstas?\n"
        "- Qual o prazo para cumprimento desta norma?\n"
        "- Quem são os sujeitos passivos desta legislação?\n"
        "- Quais as penalidades previstas em caso de descumprimento?\n"
        "- Existem exceções ou isenções previstas?\n"
        "- Qual o órgão responsável pela fiscalização?"
    )

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
                    f"**Documentos indexados:** {source_count}  \n"
                    f"**Versão:** 0.0.1"
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
                    avatar_images=(None, None),
                    buttons=["copy"],
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Digite sua pergunta sobre normas, legislação ou documentos institucionais...",
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
                    gr.Markdown(suggestions_md)

                with gr.Accordion("ℹ️ Sobre o LION", open=False):
                    gr.Markdown(
                        "**LION** _(Legal Interpretation and Official Norms)_ é uma "
                        "plataforma de Q&A institucional baseada em documentos. \n\n"
                        "Permite consultar normas, legislações e documentos internos "
                        "de forma conversacional, com respostas fundamentadas "
                        "exclusivamente no conteúdo indexado — garantindo precisão "
                        "e rastreabilidade das informações.\n\n"
                        "Pode ser aplicado em contextos jurídicos, regulatórios, "
                        "de compliance ou como base de conhecimento institucional."
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

    # Suporte a argumentos CLI para uso local (ignorados no HF Spaces)
    parser = argparse.ArgumentParser(
        description="LION — Legal Interpretation and Official Norms. Interface web de consulta a documentos."
    )
    parser.add_argument("--notebook-id", metavar="ID", help="ID do notebook (sobrescreve .env e variável de ambiente).")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 7860)), help="Porta HTTP (padrão: 7860).")
    parser.add_argument("--share", action="store_true", help="Gera link público temporário via Gradio.")
    args = parser.parse_args()

    # Determina notebook_id: argumento CLI > variável de ambiente > .env
    notebook_id = args.notebook_id or _get_notebook_id()

    if not notebook_id:
        print("❌ notebook_id não configurado.")
        print("Defina a variável de ambiente CHATBOT_NOTEBOOK_ID ou execute: python setup.py")
        sys.exit(1)

    # Sobe event loop dedicado em thread separada
    _loop = asyncio.new_event_loop()
    t = threading.Thread(target=_loop.run_forever, daemon=True)
    t.start()

    # Inicializa cliente
    print("Conectando à base de conhecimento...")
    try:
        nb, sources = _run_async(_init_client(notebook_id))
    except Exception as e:
        print(f"❌ Falha ao conectar: {e}")
        print("Verifique a autenticação e tente novamente.")
        sys.exit(1)

    print(f"✔ Notebook: {nb.title}")
    print(f"✔ Fontes: {len(sources)} documento(s)")
    print("⏳ Gerando sugestões de perguntas...")
    suggestions = _run_async(_generate_suggestions())
    print(f"✔ {len(suggestions)} sugestões geradas")
    print(f"✔ Iniciando interface em http://localhost:{args.port}\n")

    app = build_app(nb.title, sources, suggestions)
    app.launch(
        server_name="0.0.0.0",
        server_port=args.port,
        share=args.share,
        favicon_path=None,
        theme=gr.themes.Soft(
            primary_hue="amber",
            secondary_hue="orange",
            neutral_hue="slate",
        ),
        css="""
        #send-btn { min-width: 110px; }
        #reset-btn { min-width: 110px; }
        footer { display: none !important; }
        .gradio-container { max-width: 1200px !important; margin: auto; }
        h1 { letter-spacing: 0.05em; }
        """,
    )


if __name__ == "__main__":
    main()
