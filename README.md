---
title: LION
emoji: 🦁
colorFrom: yellow
colorTo: yellow
sdk: gradio
sdk_version: 6.8.0
app_file: app.py
pinned: false
---

# 🦁 LION — Legal Interpretation and Official Norms

Plataforma de Q&A institucional baseada em documentos. Consulte normas, legislações e documentos internos de forma conversacional, com respostas fundamentadas exclusivamente no conteúdo indexado.

> Pode ser aplicado em contextos jurídicos, regulatórios, de compliance ou como base de conhecimento de qualquer instituição.

## Estrutura

```
lion-chatbot/
├── app.py          # Interface web (Gradio) ← recomendado
├── chatbot.py      # Interface interativa via terminal
├── setup.py        # Configura a base e indexa os documentos
├── .env            # Gerado pelo setup.py (notebook_id)
└── docs/           # Documentos indexados (fontes do LION)
    ├── *.md
    ├── *.pdf
    └── *.html      # Convertidos automaticamente para .txt
```

## Pré-requisitos

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Passo a Passo

### 1. Indexar os documentos

```bash
python setup.py
```

Este script:
- Converte arquivos `.html` de `docs/` para `.txt` (UTF-8)
- Cria uma base de conhecimento chamada **"LION"**
- Faz upload de todos os arquivos `.md`, `.pdf` e `.txt` como fontes
- Salva o `CHATBOT_NOTEBOOK_ID` no arquivo `.env`

Para reaproveitar uma base existente:

```bash
python setup.py --notebook-id <id_existente>
```

Para listar bases disponíveis:

```bash
python setup.py --list
```

### 2. Iniciar a interface web (recomendado)

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

### 2b. Interface via terminal (alternativo)

```bash
python chatbot.py
```

---

## Exemplo de Sessão (Terminal)

```
════════════════════════════════════════════════════════════
  🦁  LION — Legal Interpretation and Official Norms
════════════════════════════════════════════════════════════
  Consulta inteligente a normas e documentos institucionais
  Digite /ajuda para ver os comandos disponíveis
────────────────────────────────────────────────────────────

✔ Base de conhecimento: LION
✔ Documentos indexados: 6 documento(s)

Você: Quais são as penalidades previstas na L15270?

🦁 LION:
  De acordo com o artigo X da Lei nº 15.270, as penalidades
  incluem multa de 50% a 150% sobre o valor da infração,
  podendo ser cumulada com suspensão de atividades...

Você: /fontes

── Documentos indexados ──
  • D9580 (doc)
  • L15270 (doc)
  • L7713compilada (doc)
  ...

Você: /sair
Até logo! 👋
```

---

## Comandos do Chat

| Comando      | Ação                                       |
|--------------|--------------------------------------------|
| `/ajuda`     | Exibe os comandos disponíveis              |
| `/novo`      | Inicia nova conversa (limpa o contexto)    |
| `/historico` | Exibe o histórico da sessão atual          |
| `/fontes`    | Lista os documentos indexados              |
| `/sair`      | Encerra o LION                             |

---

## Adicionando Documentos

Coloque arquivos `.md`, `.pdf` ou `.html` na pasta `docs/` e reindexe:

```bash
cp /caminho/para/documento.pdf docs/
python setup.py --notebook-id <id_existente>
```

## Casos de Uso

- 📜 **Legislação e normas tributárias** — consulta a leis e instruções normativas
- 🏢 **Base de conhecimento interna** — manuais, políticas e procedimentos
- 📋 **Compliance e regulatório** — interpretação de normas e regulamentos
- 🎓 **Q&A educacional** — dúvidas sobre conteúdos e documentos acadêmicos
