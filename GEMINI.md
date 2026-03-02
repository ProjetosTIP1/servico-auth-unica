# Single Auth Microservice

A centralized authentication microservice built with FastAPI, designed to handle user management, JWT-based authentication, and integration with Microsoft Entra ID (Azure AD).

## Project Overview

*   **Main Technologies:** Python 3.12+, FastAPI, MariaDB, SQL Server, Redis, MSAL, SQLAlchemy, Pydantic Settings, Ruff.
*   **Architecture:** Follows Clean Architecture principles with a clear separation between the API layer, core business logic, and infrastructure adapters.
    *   `api/`: Contains FastAPI route handlers and middlewares (e.g., correlation ID, auth).
    *   `core/ports/`: Defines interfaces (Service, Repository, Infrastructure) to decouple logic from implementation.
    *   `core/infrastructure/`: Concrete implementations of database adapters and authentication services.
    *   `core/services/`: Application use cases and business logic.
    *   `core/repositories/`: Data access layer for MariaDB and potentially other sources.
    *   `core/util/deps.py`: The Composition Root for Dependency Injection, wiring everything together.

## Building and Running

### Prerequisites
*   Python 3.12 or higher.
*   [uv](https://github.com/astral-sh/uv) (recommended for dependency management).
*   MariaDB and Redis instances.

### Setup
1.  Install dependencies:
    ```bash
    uv sync
    ```
2.  Configure environment variables:
    *   Copy `core/config/.env.sample` to `core/config/.env` and fill in the required values (DB credentials, Azure AD settings, etc.).

### Running the Application
*   Start the FastAPI server:
    ```bash
    uvicorn main:app --reload
    ```
*   The API documentation will be available at `http://localhost:8000/docs`.

### Testing
*   TODO: No specific test runner configuration found in `pyproject.toml`, but an `api/tests` and `core/tests` directory exists. Use `pytest` if available.
    ```bash
    pytest
    ```

## Development Conventions

*   **Clean Architecture:** Always code against interfaces (`core/ports`) and inject concrete implementations via `core/util/deps.py`.
*   **Type Hinting:** Use explicit type hints for all function signatures and variables. `Annotated` is preferred for FastAPI dependencies.
*   **Linting & Formatting:** The project uses `ruff`. Run it before committing:
    ```bash
    ruff check .
    ruff format .
    ```
*   **Error Handling:** Use custom exceptions where appropriate and handle them in the API layer or via middlewares.
*   **Logging:** Use the centralized `logger` from `core.helpers.logger_helper`.
