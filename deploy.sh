#!/usr/bin/env bash
# deploy.sh — Publica o LION no GitHub e HuggingFace Spaces
#
# Uso:
#   ./deploy.sh                        # commit automático com mensagem padrão
#   ./deploy.sh "mensagem do commit"   # mensagem personalizada
#   ./deploy.sh --secrets-only         # só atualiza secrets e reinicia, sem commit/push

set -euo pipefail

# ── Configuração ──────────────────────────────────────────────────────────────
HF_TOKEN=$(cat ~/.cache/huggingface/token 2>/dev/null || echo "")
SPACE="ronenfilho/lion-chatbot"
AUTH_FILE="$HOME/.notebooklm/storage_state.json"
ENV_FILE="$(dirname "$0")/.env"

# ── Funções ───────────────────────────────────────────────────────────────────
check_requirements() {
    if [[ -z "$HF_TOKEN" ]]; then
        echo "❌ Token do HuggingFace não encontrado em ~/.cache/huggingface/token"
        echo "   Execute: huggingface-cli login"
        exit 1
    fi
    if [[ ! -f "$AUTH_FILE" ]]; then
        echo "❌ Arquivo de autenticação não encontrado: $AUTH_FILE"
        exit 1
    fi
}

get_notebook_id() {
    if [[ -f "$ENV_FILE" ]]; then
        grep "CHATBOT_NOTEBOOK_ID" "$ENV_FILE" | cut -d'=' -f2 | tr -d '[:space:]'
    else
        echo ""
    fi
}

push_secrets() {
    local notebook_id
    notebook_id=$(get_notebook_id)

    if [[ -z "$notebook_id" ]]; then
        echo "⚠ CHATBOT_NOTEBOOK_ID não encontrado no .env — pulando secret."
    else
        echo "🔑 Atualizando CHATBOT_NOTEBOOK_ID..."
        curl -s -X POST \
            "https://huggingface.co/api/spaces/${SPACE}/secrets" \
            -H "Authorization: Bearer ${HF_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"key\": \"CHATBOT_NOTEBOOK_ID\", \"value\": \"${notebook_id}\"}" > /dev/null
        echo "   ✔ CHATBOT_NOTEBOOK_ID = ${notebook_id}"
    fi

    echo "🔑 Atualizando NOTEBOOKLM_AUTH_JSON..."
    python3 - <<EOF
import json, subprocess

hf_token = open("$HOME/.cache/huggingface/token").read().strip()
auth_json = open("$AUTH_FILE").read().strip()
payload   = json.dumps({"key": "NOTEBOOKLM_AUTH_JSON", "value": auth_json})

r = subprocess.run([
    "curl", "-s", "-X", "POST",
    "https://huggingface.co/api/spaces/${SPACE}/secrets",
    "-H", f"Authorization: Bearer {hf_token}",
    "-H", "Content-Type: application/json",
    "--data-binary", payload
], capture_output=True, text=True)

if r.returncode != 0:
    print(f"   ✗ Erro: {r.stderr}")
    exit(1)
EOF
    echo "   ✔ NOTEBOOKLM_AUTH_JSON atualizado"
}

restart_space() {
    echo "🚀 Reiniciando Space..."
    curl -s -X POST \
        "https://huggingface.co/api/spaces/${SPACE}/restart" \
        -H "Authorization: Bearer ${HF_TOKEN}" > /dev/null
    echo "   ✔ Space reiniciado — https://huggingface.co/spaces/${SPACE}"
}

commit_and_push() {
    local msg="${1:-"chore: deploy $(date +'%Y-%m-%d %H:%M')"}"
    cd "$(dirname "$0")"

    if git diff --quiet && git diff --staged --quiet; then
        echo "ℹ Nenhuma alteração para commitar."
    else
        echo "📦 Commitando alterações..."
        git add -A
        git commit -m "$msg"
        echo "   ✔ Commit: $msg"
    fi

    echo "⬆ Push para GitHub..."
    git push origin main
    echo "   ✔ GitHub atualizado"

    echo "⬆ Push para HuggingFace Spaces..."
    git push space main
    echo "   ✔ HuggingFace atualizado"
}

# ── Main ──────────────────────────────────────────────────────────────────────
echo ""
echo "🦁 LION — Deploy"
echo "$(printf '─%.0s' {1..40})"

check_requirements

if [[ "${1:-}" == "--secrets-only" ]]; then
    push_secrets
    restart_space
else
    commit_and_push "${1:-}"
    push_secrets
    restart_space
fi

echo ""
echo "✅ Deploy concluído!"
echo "   https://huggingface.co/spaces/${SPACE}"
echo ""
