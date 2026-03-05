# Guia de Integração — AcmeCorp Platform

## Primeiros Passos

Este guia explica como integrar sua aplicação com a AcmeCorp Platform do zero.

---

## 1. Configuração do Ambiente

### Pré-requisitos

- Python 3.10+ ou Node.js 18+
- Conta ativa na AcmeCorp Platform
- Client ID e Client Secret (disponíveis em *Settings → API Keys*)

### Variáveis de Ambiente Recomendadas

```bash
ACMECORP_CLIENT_ID=seu_client_id
ACMECORP_CLIENT_SECRET=seu_client_secret
ACMECORP_BASE_URL=https://api.acmecorp.com/v2
ACMECORP_ENVIRONMENT=production  # ou staging
```

---

## 2. SDK Oficial

### Instalação Python

```bash
pip install acmecorp-sdk
```

### Instalação Node.js

```bash
npm install @acmecorp/sdk
```

### Exemplo de Uso (Python)

```python
from acmecorp import AcmeClient

client = AcmeClient(
    client_id="seu_client_id",
    client_secret="seu_client_secret"
)

# Listar projetos
projects = client.projects.list(status="active")
for project in projects:
    print(f"{project.id}: {project.name}")

# Criar usuário
user = client.users.create(
    name="Ana Costa",
    email="ana@empresa.com",
    role="editor"
)
```

---

## 3. Fluxo de Autenticação

```
Cliente → POST /auth/token (client_id + client_secret)
       ← { access_token, expires_in: 3600 }

Cliente → GET /projects (Authorization: Bearer <token>)
       ← [ { id, name, ... }, ... ]
```

O token expira em **1 hora**. Implemente refresh automático:

```python
import time

class TokenManager:
    def __init__(self, client_id, client_secret):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token = None
        self._expires_at = 0

    def get_token(self):
        if time.time() >= self._expires_at - 60:  # Renova 60s antes
            self._refresh()
        return self._token

    def _refresh(self):
        # POST /auth/token
        response = requests.post(...)
        self._token = response["access_token"]
        self._expires_at = time.time() + response["expires_in"]
```

---

## 4. Tratamento de Erros

### Retry com Backoff Exponencial

Para erros `429` e `503`, implemente retry com backoff:

```python
import time
import random

def request_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
```

---

## 5. Ambientes

| Ambiente   | Base URL                          | Uso                        |
|------------|-----------------------------------|----------------------------|
| Production | `https://api.acmecorp.com/v2`    | Dados reais                |
| Staging    | `https://staging-api.acmecorp.com/v2` | Testes de integração  |
| Sandbox    | `https://sandbox.acmecorp.com/v2`| Desenvolvimento local      |

**Atenção:** O Sandbox usa dados fictícios e não processa cobranças reais.

---

## 6. Boas Práticas

1. **Nunca comite credenciais** — use variáveis de ambiente ou cofre de segredos
2. **Cache de tokens** — não gere novo token a cada requisição
3. **Idempotency Keys** — use o header `Idempotency-Key` em POSTs críticos
4. **Timeouts** — configure timeout de 30s para todas as chamadas
5. **Logs estruturados** — registre `request_id` retornado em cada response

---

## 7. Suporte

- **Documentação:** https://docs.acmecorp.com
- **Status da API:** https://status.acmecorp.com
- **Suporte técnico:** suporte@acmecorp.com
- **Fórum da comunidade:** https://community.acmecorp.com
