# Single Auth Microservice

Microsserviço centralizado de autenticação construído com **FastAPI**, responsável por gerenciar usuários, emitir tokens JWT e integrar login via **Microsoft Entra ID (Azure AD)** usando o padrão MSAL.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Stack Tecnológica](#stack-tecnológica)
- [Arquitetura](#arquitetura)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Banco de Dados](#banco-de-dados)
- [Executando o Projeto](#executando-o-projeto)
- [Endpoints da API](#endpoints-da-api)
- [Integração SGA ↔ SAM](#integração-sga--sam)
- [Fluxos de Autenticação](#fluxos-de-autenticação)
  - [Fluxo 1 — Login com e-mail e senha](#fluxo-1--login-com-e-mail-e-senha)
  - [Fluxo 2 — Login via Microsoft (MSAL)](#fluxo-2--login-via-microsoft-msal)
- [Convenções de Desenvolvimento](#convenções-de-desenvolvimento)

---

## Visão Geral

O serviço expõe uma API REST que centraliza:

- **Autenticação local** — login com e-mail/senha gerando tokens JWT (access + refresh).
- **SSO via Microsoft** — validação de `id_token` emitido pelo Azure AD, provisionamento automático do usuário local na primeira entrada (_just-in-time provisioning_) e emissão de tokens JWT próprios.
- **Gerenciamento de usuários** — CRUD protegido por perfil de gerente.
- **Gestão de tokens** — refresh, revogação e logout.

---

## Stack Tecnológica

| Componente | Tecnologia |
|---|---|
| Framework web | FastAPI 0.129+ / Uvicorn |
| Linguagem | Python 3.12+ |
| Validação / schemas | Pydantic v2 + Pydantic Settings |
| Banco principal | MariaDB (via driver nativo `mariadb`) |
| Banco secundário | SQL Server (via `pyodbc`) |
| Autenticação Microsoft | MSAL (`msal`) + `python-jose[cryptography]` |
| Hash de senhas | `bcrypt` |
| Linting / formatação | `ruff` |
| Gerenciador de deps | `uv` |

---

## Arquitetura

O projeto segue **Clean Architecture** com a regra de dependência apontando sempre de fora para dentro:

```
┌─────────────────────────────────────────────┐
│  API Layer  (api/)                          │
│  Handlers, Middlewares                      │
├─────────────────────────────────────────────┤
│  Application Layer  (core/services/)        │
│  Casos de uso: MicrosoftLoginService,       │
│  TokenService, UserService                  │
├─────────────────────────────────────────────┤
│  Domain Layer  (core/models/, core/ports/)  │
│  Entidades, Interfaces (Ports)              │
├─────────────────────────────────────────────┤
│  Infrastructure Layer  (core/infrastructure)│
│  MicrosoftAuthAdapter, MariaDBAdapter,      │
│  DatabaseManager                            │
└─────────────────────────────────────────────┘
```

**Princípios aplicados:**

- **DIP (Dependency Inversion):** Serviços dependem de interfaces (`core/ports/`), nunca de implementações concretas.
- **SRP:** Cada classe tem uma única responsabilidade (ex.: `MicrosoftAuthAdapter` é a única classe que conhece JWKS e MSAL).
- **Composition Root:** `core/util/deps.py` é o único lugar que conecta interfaces às implementações, via injeção de dependência do FastAPI.

---

## Estrutura de Diretórios

```
single-auth-microservice/
├── main.py                        # Ponto de entrada FastAPI (lifespan, routers, middlewares)
├── pyproject.toml                 # Dependências e configuração do projeto
├── api/
│   ├── handlers/
│   │   ├── ms_handler.py          # Endpoints de autenticação Microsoft
│   │   ├── oauth_handler.py       # Endpoints OAuth2 (login, refresh, logout, /me)
│   │   └── user_handler.py        # CRUD de usuários
│   └── middlewares/
│       ├── auth_mw.py             # Middleware de autenticação JWT
│       └── correlation_id_mw.py   # Middleware de Correlation ID
├── core/
│   ├── config/
│   │   └── settings.py            # Todas as variáveis de ambiente (Pydantic Settings)
│   ├── infrastructure/
│   │   ├── database_manager.py    # Singleton que gerencia o ciclo de vida das conexões
│   │   ├── mariadb_adapter.py     # Implementação concreta de IDatabase para MariaDB
│   │   ├── microsoft_auth_adapter.py  # Validação de JWT do Azure AD (JWKS + python-jose)
│   │   └── sqls_adapter.py        # Implementação concreta de IDatabase para SQL Server
│   ├── models/
│   │   ├── user_models.py         # UserType, UserCreateType, MicrosoftUserIdentity, ...
│   │   ├── oauth_models.py        # TokenResponseModel, TokenModel, ...
│   │   └── application_models.py  # ApplicationModel
│   ├── ports/
│   │   ├── service.py             # IMicrosoftAuthService, ITokenService
│   │   ├── repository.py          # IUserRepository, ITokenRepository
│   │   └── infrastructure.py      # IDatabase
│   ├── repositories/
│   │   ├── user_repository.py     # Queries SQL para usuários
│   │   └── token_repository.py    # Queries SQL para tokens
│   ├── services/
│   │   ├── microsoft_login_service.py  # Caso de uso: validar token MS + provisionar usuário
│   │   ├── token_service.py            # Login local, refresh, revogação
│   │   └── user_service.py             # CRUD de usuários
│   └── util/
│       ├── deps.py                # Composition Root — injeção de dependências
│       └── context.py             # ContextVar para Correlation ID
└── docs/
    └── database_schema.sql        # Schema completo do MariaDB
```

---

## Configuração do Ambiente

Crie o arquivo `core/config/.env` com base no template abaixo:

```dotenv
# ── Geral ──────────────────────────────────────────────────────────────────
DEVELOPMENT_ENV=true
DEBUG=true
API_URL=http://localhost:8000

# ── JWT ────────────────────────────────────────────────────────────────────
SECRET_KEY=troque-por-uma-chave-secreta-forte
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRES_DAYS=7

# ── CORS ───────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# ── MariaDB ────────────────────────────────────────────────────────────────
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=sua_senha
MARIADB_DB=auth_db

# ── SQL Server (opcional) ──────────────────────────────────────────────────
SQLSERVER_HOST=localhost
SQLSERVER_PORT=1433
SQLSERVER_USER=sa
SQLSERVER_PASSWORD=sua_senha
SQLSERVER_DB=seu_banco
SQLSERVER_DRIVER=ODBC Driver 17 for SQL Server
SQLSERVER_ENCRYPT=yes
SQLSERVER_TRUST_SERVER_CERTIFICATE=yes

# ── Microsoft Entra ID (Azure AD) ──────────────────────────────────────────
# AZURE_TENANT_ID: GUID do seu tenant ou "common" para multi-tenant
AZURE_TENANT_ID=seu-tenant-guid
# AZURE_CLIENT_ID: ID do app registrado no Azure Portal
AZURE_CLIENT_ID=seu-client-id
# AZURE_CLIENT_SECRET: necessário apenas para fluxos server-to-server
AZURE_CLIENT_SECRET=seu-client-secret
```

> **Atenção:** `AZURE_CLIENT_ID` é usado como **audience** (`aud`) na validação do JWT. O token enviado pelo frontend **precisa** ter esse valor no campo `aud`.

---

## Banco de Dados

Execute o schema em `docs/database_schema.sql` no seu MariaDB:

```bash
mysql -u root -p < docs/database_schema.sql
```

Tabelas criadas:

| Tabela | Descrição |
|---|---|
| `users` | Usuários do sistema. Campo `ms_oid` armazena o OID do Azure AD para vincular contas Microsoft. |
| `tokens` | Access e refresh tokens emitidos. Suporte a revogação e expiração. |
| `applications` | Aplicações cadastradas (para controle de acesso multiapp). |
| `database_logs` | Log de auditoria de operações. |

---

## Executando o Projeto

### Pré-requisitos

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv)
- MariaDB em execução
- (Opcional) SQL Server

### Instalação

```bash
# Instalar dependências
uv sync

# Ativar o ambiente virtual
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS
```

### Iniciar o servidor

```bash
uvicorn main:app --reload
```

A documentação interativa estará disponível em:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Linting e formatação

```bash
ruff check .
ruff format .
```

---

## Endpoints da API

### OAuth / Autenticação local (`/o`)

| Método | Rota | Autenticação | Descrição |
|---|---|---|---|
| `POST` | `/o/token` | Pública | Login com `username` + `password` (OAuth2 Password Flow). Retorna `access_token` e `refresh_token`. |
| `POST` | `/o/refresh` | Pública | Renova o access token a partir de um refresh token válido. |
| `POST` | `/o/logout` | JWT | Revoga os tokens da sessão atual. |
| `GET` | `/o/me` | JWT | Retorna os dados do usuário autenticado. |
| `POST` | `/o/validate` | Pública | Valida um token JWT interno. |

### Microsoft SSO (`/o/microsoft`)

| Método | Rota | Autenticação | Descrição |
|---|---|---|---|
| `POST` | `/o/microsoft/validate` | Pública | Recebe o `id_token` do Azure AD, valida criptograficamente e retorna tokens JWT internos + dados do usuário. |
| `GET` | `/o/microsoft/login-url` | Pública | Gera a URL de login Microsoft (para frontends sem MSAL.js). |
| `POST` | `/o/microsoft/callback` | Pública | Troca um authorization code por token (fluxo server-side). |
| `GET` | `/o/microsoft/me` | Bearer (id_token) | Retorna a identidade Microsoft do usuário autenticado via Bearer token. |

### Usuários (`/users`)

| Método | Rota | Autenticação | Perfil mínimo |
|---|---|---|---|
| `GET` | `/users/{user_id}` | JWT | Gerente |
| `POST` | `/users/` | JWT | Gerente |
| `PATCH` | `/users/{user_id}` | JWT | Gerente |
| `PATCH` | `/users/{user_id}/password` | JWT | Gerente |
| `DELETE` | `/users/{user_id}` | JWT | Gerente |

### Integração SGA (`/integration`)

| Método | Rota | Autenticação | Parâmetros | Descrição |
|---|---|---|---|---|
| `POST` | `/integration/sync-all` | Pública* | `dry_run` (bool) | Executa a sincronização completa (usuários e metadados). |
| `POST` | `/integration/sync-users` | Pública* | `dry_run` (bool) | Sincroniza apenas usuários. |
| `POST` | `/integration/sync-metadata` | Pública* | `dry_run` (bool) | Sincroniza apenas metadados (Departamentos e Cargos). |

> \* **Nota:** Atualmente os endpoints de integração são públicos para facilitar chamadas de tarefas agendadas internas. Recomenda-se restringir o acesso via firewall ou rede interna.

---

## Integração SGA ↔ SAM

O sistema possui um motor de integração de alta performance baseado em **Polars** que sincroniza os dados do sistema legado (SGA - SQL Server) com o SAM (MariaDB).

### Funcionamento do Processo
O processo de sincronização segue o padrão ETL:
1.  **Extração:** Busca usuários em massa do SQL Server.
2.  **Transformação:** Normaliza usernames, detecta novos usuários, mudanças em cargos/unidades e identifica usuários que devem ser desativados.
3.  **Carga (Load):** Realiza upserts em lote no MariaDB para máxima eficiência.

### Execução via Host Task (Agendamento)

Para manter os dados sincronizados automaticamente, você pode configurar uma tarefa no host (servidor) que chama o endpoint de sincronização em intervalos regulares.

#### Linux (Cronjob)
Adicione uma entrada ao `crontab` para executar a sincronização toda madrugada às 02:00:
```bash
0 2 * * * curl -X POST "http://localhost:8000/integration/sync-all?dry_run=false"
```

#### Windows (Task Scheduler)
Crie uma tarefa agendada que execute um comando PowerShell:
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/integration/sync-all?dry_run=false"
```

#### Execução Manual (Dry Run)
Antes de aplicar mudanças reais, você pode testar o que será alterado usando o parâmetro `dry_run=true`:
```bash
curl -X POST "http://localhost:8000/integration/sync-all?dry_run=true"
```
O resultado será exibido nos logs da aplicação detalhando a quantidade de registros que seriam afetados.

---

## Fluxos de Autenticação

### Fluxo 1 — Login com e-mail e senha

```
Frontend                     Backend (/o/token)           Banco (MariaDB)
   │                               │                            │
   │── POST /o/token ─────────────>│                            │
   │   {username, password}        │                            │
   │                               │── buscar usuário ─────────>│
   │                               │<── UserInDB ───────────────│
   │                               │                            │
   │                               │── bcrypt.verify(password)  │
   │                               │                            │
   │                               │── criar refresh_token ────>│ (tabela tokens)
   │                               │── criar access_token ─────>│ (tabela tokens)
   │                               │                            │
   │<── 200 {access_token, ────────│
   │         refresh_token,        │
   │         expires_in}           │
```

**Renovação de token:**
```
Frontend                     Backend (/o/refresh)
   │── POST /o/refresh ───────────>│
   │   {refresh_token}             │── validar refresh token no BD
   │                               │── verificar se não está revogado
   │                               │── emitir novo access_token
   │<── 200 {access_token, ────────│
   │         refresh_token}        │
```

---

### Fluxo 2 — Login via Microsoft (MSAL)

Este é o fluxo principal de SSO. O frontend usa **MSAL.js** para autenticar o usuário diretamente com o Azure AD e recebe um `id_token`. Esse token é então enviado ao backend para validação e criação de sessão local.

#### Por que `id_token` e não `access_token`?

> O `access_token` emitido com escopos do Microsoft Graph (ex.: `User.Read`) tem como audience `00000003-0000-0000-c000-000000000000` (o ID fixo do Graph). As chaves públicas usadas para assinar esse token **nunca são publicadas** no JWKS do seu tenant — portanto, nenhum app externo consegue validá-lo.
>
> O `id_token` sempre tem como audience o `clientId` do seu app registrado, é assinado com as chaves publicadas no JWKS e carrega todas as informações de identidade necessárias (`oid`, `email`, `name`, etc.).

#### Diagrama completo do fluxo

```
Usuário          Frontend (MSAL.js)           Azure AD            Backend
   │                    │                         │                   │
   │── clica "Entrar ──>│                         │                   │
   │   com Microsoft"   │                         │                   │
   │                    │── loginPopup / ─────────>│                   │
   │                    │   loginRedirect          │                   │
   │                    │   (scopes: openid,       │                   │
   │                    │    profile, email)        │                   │
   │                    │                         │                   │
   │<── tela de login ──│<────────────────────────│                   │
   │   Microsoft        │                         │                   │
   │                    │                         │                   │
   │── credenciais ─────│────────────────────────>│                   │
   │                    │                         │                   │
   │                    │<── AuthenticationResult ─│                   │
   │                    │    {idToken, accessToken}│                   │
   │                    │                         │                   │
   │                    │── POST /o/microsoft/validate ───────────────>│
   │                    │   Body: { token: idToken }                   │
   │                    │                         │                   │
   │                    │                         │  1. _get_jwks()   │
   │                    │                         │<── GET JWKS ───────│
   │                    │                         │──> {keys:[...]} ──>│
   │                    │                         │                   │
   │                    │                         │  2. extrair kid    │
   │                    │                         │     do header JWT  │
   │                    │                         │                   │
   │                    │                         │  3. encontrar a    │
   │                    │                         │     chave certa    │
   │                    │                         │     no JWKS        │
   │                    │                         │                   │
   │                    │                         │  4. jwt.decode()   │
   │                    │                         │     verifica:      │
   │                    │                         │     - assinatura   │
   │                    │                         │     - aud == clientId
   │                    │                         │     - exp          │
   │                    │                         │                   │
   │                    │                         │  5. _map_claims_   │
   │                    │                         │     to_identity()  │
   │                    │                         │     → MicrosoftUserIdentity
   │                    │                         │                   │
   │                    │                         │  6. buscar usuário │
   │                    │                         │     por ms_oid     │──> MariaDB
   │                    │                         │                   │<── user | None
   │                    │                         │                   │
   │                    │                         │  7a. usuário existe│
   │                    │                         │      → retornar    │
   │                    │                         │                   │
   │                    │                         │  7b. email existe  │
   │                    │                         │      → vincular    │
   │                    │                         │        ms_oid      │──> UPDATE users
   │                    │                         │                   │
   │                    │                         │  7c. novo usuário  │
   │                    │                         │      → criar conta │──> INSERT users
   │                    │                         │      (senha aleatória,
   │                    │                         │       pois login é via MS)
   │                    │                         │                   │
   │                    │                         │  8. emitir tokens  │
   │                    │                         │     JWT internos   │──> INSERT tokens
   │                    │                         │                   │
   │<── 200 ────────────│<────────────────────────────────────────────│
   │                    │  {access_token,          │                   │
   │                    │   refresh_token,         │                   │
   │                    │   oid, email, name,      │                   │
   │                    │   is_new_user}           │                   │
```

#### Código de exemplo no frontend (MSAL.js)

```typescript
import { useMsal } from "@azure/msal-react";

const { instance, accounts } = useMsal();

// Configuração de escopos — NÃO inclua escopos do Graph aqui
// se o objetivo é autenticar no seu backend.
const loginRequest = {
  scopes: ["openid", "profile", "email"],
};

async function handleLogin() {
  // Autenticar com Microsoft
  const result = await instance.loginPopup(loginRequest);

  // IMPORTANTE: enviar o idToken, NÃO o accessToken
  //   accessToken → audience = Graph (00000003-...) → inválido para o seu backend
  //   idToken     → audience = seu clientId          → válido ✓
  await fetch("/o/microsoft/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: result.idToken }),
  });
}

// Renovação silenciosa (token em cache)
async function loginSilently() {
  const tokenResponse = await instance.acquireTokenSilent({
    ...loginRequest,
    account: accounts[0],
  });

  // Mesma regra: usar idToken
  await fetch("/o/microsoft/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: tokenResponse.idToken }),
  });
}
```

#### Validação de token no backend (`MicrosoftAuthAdapter`)

O processo de validação segue estas etapas, conforme implementado em `core/infrastructure/microsoft_auth_adapter.py`:

1. **Buscar JWKS** — Obtém as chaves públicas do Azure AD em `https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys`. As chaves são cacheadas por 1 hora para evitar latência de rede em cada requisição.

2. **Extrair `kid`** — Lê o campo `kid` (Key ID) do header do JWT sem verificar a assinatura (`jwt.get_unverified_header`). Isso identifica qual chave RSA foi usada para assinar o token.

3. **Localizar a chave** — Filtra o array `keys` do JWKS para encontrar a chave cujo `kid` corresponde ao do token.

4. **Decodificar e verificar** — Chama `jwt.decode()` passando apenas a chave correta. O `python-jose` verifica:
   - Assinatura RSA-256
   - `aud` (audience) == `AZURE_CLIENT_ID`
   - `exp` (expiração)

5. **Mapear claims** — Converte os claims brutos do JWT em um objeto `MicrosoftUserIdentity` com os campos: `oid`, `email`, `name`, `given_name`, `family_name`, `tenant_id`, `preferred_username`, `roles`.

#### Registro de aplicativo no Azure Portal

Para que o fluxo funcione corretamente:

1. **Azure Portal → App registrations → New registration**
   - Supported account types: escolha conforme seu cenário (single tenant ou multi-tenant).
   - Redirect URI: `http://localhost:5173/redirect` (SPA).

2. **Authentication → Add platform → Single-page application**
   - Adicione os redirect URIs do seu frontend.
   - Marque `ID tokens` em **Implicit grant and hybrid flows**.

3. **Token configuration**
   - Adicione optional claims: `email`, `given_name`, `family_name`, `preferred_username` no `id_token`.

4. **Variáveis de ambiente**
   - `AZURE_TENANT_ID`: Directory (tenant) ID
   - `AZURE_CLIENT_ID`: Application (client) ID

---

## Convenções de Desenvolvimento

- **Interfaces primeiro:** Toda nova funcionalidade começa com a definição da interface em `core/ports/`. A implementação concreta vem depois.
- **Injeção de dependência:** Nunca instancie serviços ou repositórios diretamente em handlers. Use sempre `Depends()` via `core/util/deps.py`.
- **Repositório — sem ORM:** Queries SQL são escritas manualmente no `core/repositories/`. Use sempre `execute_with_params()` para prevenir SQL injection.
- **Validação na borda:** Inputs externos são validados com modelos Pydantic. Nunca confie em dicionários crus vindos de APIs externas ou do banco.
- **Logging centralizado:** Use o `logger` de `core.helpers.logger_helper` — nunca `print()` em produção.
- **Correlation ID:** Toda requisição recebe um `X-Correlation-ID` via middleware, propagado nos logs para rastreabilidade.
- **Erros explícitos:** Exceções de domínio (ex.: `MicrosoftAuthError`) são lançadas na camada de infraestrutura e convertidas em respostas HTTP na camada de API.
