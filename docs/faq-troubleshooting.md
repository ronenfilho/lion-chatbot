# FAQ & Troubleshooting — AcmeCorp Platform

## Perguntas Frequentes

---

### Autenticação

**P: Meu token está expirando antes do tempo indicado. Por quê?**

R: O campo `expires_in` indica o tempo máximo em segundos. Por questões de segurança,
tokens podem ser invalidados antes disso nos seguintes casos:
- Rotação de chaves de segurança (aviso enviado por e-mail com 48h de antecedência)
- Detecção de uso suspeito ou acesso de IP não autorizado
- Revogação manual em *Settings → API Keys*

Recomendamos renovar o token quando restar menos de 5 minutos para expirar.

---

**P: Recebi erro `403 Forbidden` mesmo com token válido. O que fazer?**

R: Verifique:
1. A role do usuário ou service account tem permissão para o recurso
2. O recurso pertence ao tenant correto do seu token
3. O plano contratado inclui o endpoint acessado
4. Não há restrição de IP configurada em *Settings → Security*

---

**P: Como testar a autenticação sem afetar dados de produção?**

R: Use o ambiente Sandbox (`https://sandbox.acmecorp.com/v2`). Ele aceita as mesmas
credenciais mas opera com dados isolados e fictícios.

---

### Integrações

**P: O SDK Python suporta chamadas assíncronas?**

R: Sim. O SDK oferece cliente assíncrono:

```python
from acmecorp import AsyncAcmeClient
import asyncio

async def main():
    async with AsyncAcmeClient(...) as client:
        projects = await client.projects.list()

asyncio.run(main())
```

---

**P: Como recebo notificações em tempo real de eventos?**

R: Configure Webhooks em *Settings → Webhooks*. Insira a URL do seu endpoint
e selecione os eventos de interesse. Validamos o payload via HMAC-SHA256:

```python
import hmac, hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

**P: Posso importar dados em lote?**

R: Sim, via endpoint `POST /batch`. Limite de 100 itens por requisição:

```json
{
  "operations": [
    { "method": "POST", "path": "/users", "body": { ... } },
    { "method": "POST", "path": "/users", "body": { ... } }
  ]
}
```

---

### Erros Comuns

**Erro: `422 Unprocessable Entity`**

Causa mais comum: campos obrigatórios ausentes ou com formato inválido.
O corpo do erro detalha o campo específico:

```json
{
  "error": "validation_failed",
  "details": [
    { "field": "email", "message": "Formato de e-mail inválido" }
  ]
}
```

---

**Erro: `409 Conflict`**

Ocorre ao tentar criar um recurso que já existe (ex: e-mail de usuário duplicado).
Use `GET` para verificar existência antes de criar, ou trate o 409 na aplicação.

---

**Erro: `503 Service Unavailable`**

A API está temporariamente indisponível. Verifique https://status.acmecorp.com
e implemente retry com backoff exponencial (ver Guia de Integração, seção 4).

---

### Limites e Cotas

**P: Como saber quantas requisições ainda tenho disponíveis?**

R: Todo response inclui os headers:
```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 245
X-RateLimit-Reset: 1709654400  (Unix timestamp de reset)
```

---

**P: O que acontece quando estouro o rate limit?**

R: Você recebe `429 Too Many Requests` com o header `Retry-After` indicando
quantos segundos aguardar antes de tentar novamente. Requisições acima do limite
são descartadas (não enfileiradas).

---

**P: Existe limite de tamanho para uploads de arquivo?**

R: Sim:
- Plano Free: 10 MB por arquivo, 100 MB total/mês
- Plano Pro: 100 MB por arquivo, 10 GB total/mês
- Plano Enterprise: 1 GB por arquivo, ilimitado total

---

### Faturamento

**P: Serei cobrado por chamadas ao Sandbox?**

R: Não. O ambiente Sandbox é completamente gratuito e não gera cobranças.

---

**P: Como monitorar o consumo da API?**

R: Acesse *Dashboard → Usage* para visualizar:
- Requisições por endpoint
- Volume de dados transferidos
- Erros por tipo
- Comparativo com períodos anteriores

Alertas de consumo podem ser configurados em *Settings → Alerts*.
