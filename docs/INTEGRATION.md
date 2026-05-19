# Plano de Integração SAM (Single Auth Microservice)

Este documento descreve como desenvolvedores podem integrar suas aplicações ao ecossistema SAM para centralizar autenticação, perfil de usuário e gestão de permissões.

---

## 1. Visão Geral da Integração

O SAM atua como o **Provedor de Identidade (IdP)** central. Sua aplicação (Client App) delega a autenticação para o SAM e recebe em troca um conjunto de tokens JWT que comprovam a identidade do usuário e suas permissões.

### Fluxo Recomendado
1. **Redirecionamento:** O usuário clica em "Entrar" na sua aplicação e é redirecionado para o SAM.
2. **Autenticação:** O usuário faz login no SAM (via Microsoft SSO ou E-mail/Senha).
3. **Retorno:** O SAM redireciona de volta para sua aplicação com um `access_token` e `refresh_token`.
4. **Consumo:** Sua aplicação usa o `access_token` para identificar o usuário e validar permissões.

---

## 2. Passo a Passo para Desenvolvedores

### A. Registro da Aplicação
Antes de começar, sua aplicação deve estar cadastrada no SAM:
1. Acesse o painel administrativo do SAM.
2. Em **Aplicações**, clique em "Nova Aplicação".
3. Defina o **Nome**, **URI de Redirecionamento** (sua URL de callback) e as **Permissões Disponíveis** (ex: `admin`, `editor`, `viewer`).

### B. Implementando o Login (Frontend)

Se sua aplicação é um SPA (React, Vue, Angular), você tem duas opções:

#### Opção 1: Uso Direto do Microsoft SSO (Recomendado para SSO Corporativo)
1. Use a biblioteca `msal-browser` no seu frontend para autenticar o usuário.
2. Envie o `id_token` recebido da Microsoft para o endpoint do SAM:
   `POST /o/microsoft/validate`
   ```json
   { "token": "JWT_DA_MICROSOFT" }
   ```
3. O SAM retornará os tokens internos do SAM, que você deve armazenar (Cookies HttpOnly ou LocalStorage).

#### Opção 2: Redirecionamento para o SAM
1. Redirecione o usuário para a URL de login do SAM:
   `GET /o/microsoft/login-url?redirect_uri=SUA_URL_DE_CALLBACK`
2. O SAM fará o login e redirecionará de volta para `SUA_URL_DE_CALLBACK?token=...`

---

## 3. Gestão de Tokens

### Access Token
- **Uso:** Deve ser enviado no header `Authorization: Bearer <TOKEN>` em todas as requisições para o seu backend.
- **Validação:** Seu backend deve validar a assinatura do JWT usando a `SECRET_KEY` do SAM ou chamando o endpoint `/o/validate`.

### Refresh Token
- Quando o `access_token` expirar (erro 401), use o `refresh_token` para obter um novo par:
  `POST /o/refresh`
  ```json
  { "refresh_token": "SEU_REFRESH_TOKEN", "access_token": "SEU_ACCESS_TOKEN_EXPIRADO" }
  ```

---

## 4. Obtendo Perfil e Permissões

Para saber quem é o usuário e o que ele pode fazer na sua aplicação:

### Rota `/o/me`
Retorna os dados básicos do usuário logado.
```bash
curl -H "Authorization: Bearer <TOKEN>" http://sam-url/o/me
```

### Validação de Permissões
Atualmente, as permissões são geridas por aplicação. No seu backend, você pode verificar se o usuário tem acesso à sua aplicação chamando:
`GET /users/{id}/applications` (Requer perfil de gerente no SAM)

**Dica de Implementação:** 
Para aplicações satélites, recomendamos que o backend da sua aplicação valide o `sub` (CPF/CNPJ) presente no JWT e consulte as permissões do usuário para o seu `application_id` específico no banco do SAM.

---

## 5. Melhores Práticas de Segurança

1. **Sempre use HTTPS** em produção.
2. **Não armazene segredos** no frontend.
3. **Validação de Audience:** Sempre verifique se o token emitido pelo SAM foi destinado à sua aplicação.
4. **Logout Centralizado:** Ao deslogar da sua aplicação, chame `POST /o/logout` no SAM para invalidar a sessão global.

---

## 6. Endpoints de Referência

| Finalidade | Endpoint |
|---|---|
| Login Local | `POST /o/token` |
| Validar Microsoft | `POST /o/microsoft/validate` |
| Renovação | `POST /o/refresh` |
| Perfil | `GET /o/me` |
| Logout | `POST /o/logout` |
