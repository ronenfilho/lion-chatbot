---
title: LION
colorFrom: yellow
colorTo: yellow
sdk: gradio
sdk_version: 6.8.0
app_file: app.py
pinned: false
---

# 🦁 LION — Legal Interpretation and Official Norms

Q&A conversacional sobre documentos institucionais. Respostas fundamentadas exclusivamente no conteúdo indexado — leis, normas, manuais ou qualquer base documental.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

### 1. Configurar a base de conhecimento

```bash
python setup.py
```

Selecione uma base existente ou crie uma nova. O script converte arquivos `.html` de `docs/` para `.txt`, faz upload das fontes e salva o `CHATBOT_NOTEBOOK_ID` no `.env`.

```bash
python setup.py --list               # Lista bases disponíveis
python setup.py --notebook-id <id>   # Usa base existente diretamente
```

### 2. Iniciar

**Interface web** (recomendado):
```bash
python app.py                        # http://localhost:7860
python app.py --port 8080 --share    # Porta customizada + link público
```

**Terminal**:
```bash
python chatbot.py
```

Comandos do chat: `/ajuda`, `/novo`, `/fontes`, `/historico`, `/sair`

## Estrutura

```
lion-chatbot/
├── app.py       # Interface web (Gradio)
├── chatbot.py   # Interface via terminal
├── setup.py     # Configura base e faz deploy no HuggingFace
├── docs/        # Documentos indexados (.md, .pdf, .html)
└── .env         # Gerado pelo setup.py (CHATBOT_NOTEBOOK_ID)
```

## Deploy no HuggingFace Spaces

O `setup.py` gerencia o deploy completo: cria o Space, configura os secrets `CHATBOT_NOTEBOOK_ID` e `NOTEBOOKLM_AUTH_JSON`, e faz o push do código automaticamente.
