---
title: Lion Chatbot
emoji: 🦁
colorFrom: yellow
colorTo: orange
sdk: gradio
sdk_version: 6.8.0
app_file: app.py
pinned: false
---

# 🤖 Demo — Chatbot Institucional com NotebookLM

Chatbot de suporte técnico alimentado por documentações reais, usando o
[NotebookLM](https://notebooklm.google.com) como motor de IA via
[notebooklm-py](https://github.com/teng-lin/notebooklm-py).

## Estrutura

```
demo/
├── app.py                  # Interface gráfica web (Gradio) ← recomendado
├── chatbot.py              # Chatbot interativo via terminal
├── setup.py                # Configura o notebook e importa as fontes
├── .env                    # Gerado pelo setup.py (notebook_id)
└── docs/                   # Documentações técnicas (fontes do chatbot)
    ├── api-reference.md
    ├── integration-guide.md
    └── faq-troubleshooting.md
```

## Pré-requisitos

Autenticação já configurada (a partir da raiz do projeto):

```bash
source .venv/bin/activate
notebooklm auth check
```

## Passo a Passo

### 1. Configurar o notebook

```bash
cd demo/
python setup.py
```

Este script:
- Cria um notebook chamado **"Chatbot Institucional — AcmeCorp"** no NotebookLM
- Faz upload de todos os arquivos `.md` da pasta `docs/` como fontes
- Salva o `CHATBOT_NOTEBOOK_ID` no arquivo `.env`

Para reaproveitar um notebook existente:

```bash
python setup.py --notebook-id <id_do_notebook>
```

Para listar seus notebooks:

```bash
python setup.py --list
```

### 2. Iniciar a interface gráfica (recomendado)

```bash
python app.py
```

Acesse no navegador: **http://localhost:7860**

Opções disponíveis:
```bash
python app.py --port 8080          # Porta customizada
python app.py --share              # Gera link público temporário
python app.py --notebook-id <id>   # Sobrescreve o .env
```

### 2b. Iniciar o chatbot via terminal (alternativo)

```bash
python chatbot.py
```

---

## Exemplo de Sessão

```
════════════════════════════════════════════════════════════
  🤖  Chatbot Institucional — AcmeCorp Platform
════════════════════════════════════════════════════════════
  Motor: Google NotebookLM  |  Digite /ajuda para comandos
────────────────────────────────────────────────────────────

✔ Conectado ao notebook: Chatbot Institucional — AcmeCorp
✔ Fontes carregadas: 3 documento(s)

Você: Como faço para autenticar na API?

🤖 Chatbot:
  Para autenticar na API da AcmeCorp, você deve fazer um POST para
  /auth/token com seu client_id e client_secret. A API retornará um
  token JWT válido por 1 hora...

Você: E se o token expirar antes do tempo?

🤖 Chatbot:
  Tokens podem ser invalidados antes do prazo por rotação de chaves,
  uso suspeito ou revogação manual. Recomenda-se renovar quando restar
  menos de 5 minutos para expirar...

Você: /sair
Até logo! 👋
```

---

## Comandos do Chat

| Comando         | Ação                                        |
|-----------------|---------------------------------------------|
| `/ajuda`        | Exibe os comandos disponíveis               |
| `/novo`         | Inicia nova conversa (limpa o contexto)     |
| `/historico`    | Exibe o histórico da sessão atual           |
| `/fontes`       | Lista os documentos carregados no notebook  |
| `/sair`         | Encerra o chatbot                           |

---

## Personalizando

### Adicionar suas próprias documentações

Coloque arquivos `.md` ou `.pdf` na pasta `docs/` e rode o setup novamente:

```bash
cp /caminho/para/sua-doc.pdf docs/
python setup.py --notebook-id <id_existente>
```

### Trocar o nome do produto

Edite a constante `NOTEBOOK_TITLE` no topo de `setup.py`:

```python
NOTEBOOK_TITLE = "Chatbot Institucional — SuaEmpresa"
```
