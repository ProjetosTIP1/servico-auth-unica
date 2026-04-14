# Estratégia de Testes - Single Auth Microservice

Este documento descreve a arquitetura e a estratégia de testes adotada no projeto, servindo como guia para desenvolvedores que desejam manter ou expandir a suíte de testes.

## 1. Filosofia de Testes: TDD
Utilizamos **Test-Driven Development (TDD)** como nosso "Norte". Não escrevemos testes apenas para verificar se o código funciona; escrevemos testes para definir o que o código deve fazer (seu contrato).

### O Ciclo Red-Green-Refactor
1.  **Red**: Escreva um teste que falha para uma nova funcionalidade ou correção.
2.  **Green**: Escreva o código mínimo necessário para fazer o teste passar.
3.  **Refactor**: Melhore o código mantendo os testes passando.

## 2. Camadas de Teste

### A. Testes Unitários de Serviço (`core/tests/test_*_service.py`)
Focam na lógica de negócio exclusiva da camada de `Services`.
- **Isolamento**: Usamos `unittest.mock` (`AsyncMock`, `MagicMock`) para simular Repositórios e Banco de Dados.
- **Velocidade**: Não dependem de infraestrutura externa (Docker, Banco Real).
- **Fixtures**: Localizadas em `core/tests/conftest.py`, provêem instâncias mockadas automáticas.

### B. Testes de Helpers (`core/tests/test_helpers.py`)
Testam funções utilitárias puras (hashing, JWT, manipulação de datas).
- Devem ser determinísticos e rápidos.

### C. Testes de Integração de API (`api/tests/test_api.py`)
Verificam se os Handlers da FastAPI estão corretamente integrados com os Services.
- **TestClient**: Utilizamos o `TestClient` da FastAPI.
- **Dependency Overrides**: Utilizamos `app.dependency_overrides` para injetar mocks nos Handlers, garantindo que o teste de API valide a rota e o gerenciamento de erros sem tocar no banco de dados real.

## 3. Como Executar os Testes

Certifique-se de que o ambiente virtual está ativo (`.venv`).

```bash
# Executar todos os testes
uv run pytest

# Executar um arquivo específico
uv run pytest core/tests/test_user_service.py

# Executar com cobertura
uv run pytest --cov=core --cov=api
```

## 4. Guia para Novos Desenvolvedores

### Adicionando um Novo Teste de Serviço
1.  Defina o caso de uso (Ex: "Ao criar um usuário com CPF duplicado, deve lançar uma exceção").
2.  Utilize as fixtures `user_service` e `mock_user_repo`.
3.  Configure o retorno do mock: `mock_user_repo.get_by_id.return_value = MyModel(...)`.
4.  Execute a ação e faça o `assert`.

### Boas Práticas
- **Clean Architecture**: Teste contra as interfaces (`core/ports`). Nunca importe implementações concretas de infraestrutura nos testes de serviço.
- **DIP (Dependency Inversion)**: Sempre injete as dependências mockadas via fixtures.
- **Socratic Method**: Antes de escrever o código, pergunte-se: "Como eu posso provar que este código está correto através de um teste isolado?".

## 5. Ferramentas Utilizadas
- **Pytest**: Runner principal.
- **Pytest-Asyncio**: Para suporte a `async/await`.
- **Unittest.mock**: Para mocks e stubs.
- **FastAPI TestClient**: Para simulação de requisições HTTP.
