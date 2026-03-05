# API Reference — AcmeCorp Platform

## Visão Geral

A AcmeCorp Platform expõe uma REST API versionada disponível em `https://api.acmecorp.com/v2`.
Todas as requisições devem conter o header `Authorization: Bearer <token>`.

---

## Autenticação

### POST /auth/token

Gera um token JWT de acesso.

**Request Body:**
```json
{
  "client_id": "seu_client_id",
  "client_secret": "seu_client_secret",
  "grant_type": "client_credentials"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Erros comuns:**
- `401 Unauthorized` — credenciais inválidas
- `429 Too Many Requests` — limite de requisições atingido (máx. 10 tentativas/min)

---

## Recursos

### Usuários

#### GET /users/{id}

Retorna os dados de um usuário.

**Parâmetros:**
| Parâmetro | Tipo   | Obrigatório | Descrição      |
|-----------|--------|-------------|----------------|
| `id`      | string | Sim         | ID do usuário  |

**Response 200:**
```json
{
  "id": "usr_abc123",
  "name": "Maria Silva",
  "email": "maria@empresa.com",
  "role": "admin",
  "created_at": "2025-01-15T10:30:00Z",
  "active": true
}
```

#### POST /users

Cria um novo usuário.

**Request Body:**
```json
{
  "name": "João Santos",
  "email": "joao@empresa.com",
  "role": "viewer",
  "department": "engenharia"
}
```

**Roles disponíveis:** `admin`, `editor`, `viewer`

---

### Projetos

#### GET /projects

Lista todos os projetos do tenant.

**Query Parameters:**
| Parâmetro  | Tipo    | Padrão | Descrição                       |
|------------|---------|--------|---------------------------------|
| `page`     | integer | 1      | Página de resultados            |
| `per_page` | integer | 20     | Itens por página (máx. 100)    |
| `status`   | string  | all    | Filtro: `active`, `archived`   |

#### POST /projects

Cria um novo projeto.

**Request Body:**
```json
{
  "name": "Projeto Alpha",
  "description": "Descrição do projeto",
  "owner_id": "usr_abc123",
  "tags": ["backend", "api"]
}
```

---

## Rate Limiting

A API implementa rate limiting por tenant:

| Plano       | Requisições/min | Requisições/dia |
|-------------|-----------------|-----------------|
| Free        | 60              | 1.000           |
| Pro         | 300             | 50.000          |
| Enterprise  | Ilimitado       | Ilimitado       |

Headers de resposta com informações de limite:
```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 297
X-RateLimit-Reset: 1709654400
```

---

## Códigos de Erro

| Código | Significado                        |
|--------|------------------------------------|
| 400    | Requisição inválida                |
| 401    | Não autenticado                    |
| 403    | Sem permissão                      |
| 404    | Recurso não encontrado             |
| 409    | Conflito (recurso já existe)       |
| 422    | Entidade não processável           |
| 429    | Muitas requisições                 |
| 500    | Erro interno do servidor           |
| 503    | Serviço indisponível               |

---

## Webhooks

Configure webhooks em `/settings/webhooks` para receber eventos em tempo real.

**Eventos disponíveis:**
- `project.created`
- `project.updated`
- `project.deleted`
- `user.invited`
- `deployment.completed`
- `deployment.failed`

**Payload padrão:**
```json
{
  "event": "deployment.completed",
  "timestamp": "2026-03-05T12:00:00Z",
  "data": { ... }
}
```

Todos os payloads incluem o header `X-AcmeCorp-Signature` para validação HMAC-SHA256.
