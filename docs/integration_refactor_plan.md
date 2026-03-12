# Integration Refactor Plan: Legacy to Modern

This document outlines the current flow of the `old_integration.py` script and proposes a modern, high-performance refactoring strategy aligned with Clean Architecture and the project's tech stack.

## 1. Current Flow Analysis

The legacy integration script synchronizes data between **SGA (SQL Server)** and **SAM (Single Auth Microservice)**.

### Execution Steps:
1.  **Bootstrap**: Loads environment variables and initializes a Django environment (legacy requirement).
2.  **Extraction**: Executes complex SQL queries against SQL Server to fetch the "Source of Truth" for:
    *   Departments (`RH_DEPARTAMENTO`)
    *   Positions (`RH_CARGO`, `RH_LOTACAO`)
    *   Users (Contract details from `CONTRATOPESSOAL` and `FORNECEDOR`)
3.  **Transformation (Pandas)**:
    *   Cleans `username` (removing dots, slashes, dashes).
    *   Joins (merges) SGA data with existing SAM data.
    *   Filters to find "New", "Changed", or "Disabled" records.
    *   Maps legacy strings to SAM IDs (e.g., mapping a string "Unit A" to its integer ID in the target DB).
4.  **Loading**:
    *   **Inserts**: Uses `df.to_sql(..., if_exists="append")`.
    *   **Updates**: Iterates through DataFrames row-by-row, building and executing `UPDATE` statements manually.
5.  **Side Effects**: Calls Django services (`appropriations_customer`, etc.) to trigger business logic for new or updated users.

---

## 2. Refactoring Proposal

### Architectural Goals
*   **Decouple from Django**: Use standalone libraries for password hashing (e.g., `passlib`) and move service logic into the new FastAPI microservice structure.
*   **Performance**: Replace **Pandas** with **Polars** to leverage multi-threading and lazy execution.
*   **Safety**: Use SQLAlchemy ORM or Core for all operations to prevent SQL injection and handle transactions properly.
*   **Testability**: Implement the **Repository Pattern**. Mock database adapters to test synchronization logic in isolation.

### Technical Stack
*   **Processing**: `polars`
*   **Database**: `SQLAlchemy 2.0` (Unified interface for MariaDB and SQL Server)
*   **Validation**: `Pydantic` models for data transfer
*   **Concurrency**: `asyncio` for non-blocking I/O where applicable

---

## 3. Implementation Strategy (The "Clean" Way)

### Phase 1: Ports (Interfaces)
Define interfaces in `core/ports/repository.py`:
- `SgaRepositoryPort`: Methods like `get_active_users()`, `get_positions()`.
- `SamRepositoryPort`: Methods like `upsert_users()`, `sync_departments()`.

### Phase 2: Infrastructure (Adapters)
Implement adapters in `core/infrastructure/`:
- `PolarsSgaAdapter`: Uses `polars.read_database()` with SQLAlchemy engines.
- `PolarsSamAdapter`: Handles batch updates using Polars expressions to prepare data for `INSERT ... ON DUPLICATE KEY UPDATE`.

### Phase 3: Service (Use Case)
Create an `IntegrationService` in `core/services/`:
- **Step 1: Extract**: Fetch Polars DataFrames from both sources.
- **Step 2: Transform**: 
    ```python
    # Example Polars Optimization
    new_users = sga_df.join(sam_df, on="username", how="anti")
    changed_users = sga_df.join(sam_df, on="username", how="inner").filter(
        (pl.col("name_sga") != pl.col("name_sam")) | 
        (pl.col("dept_sga") != pl.col("dept_sam"))
    )
    ```
- **Step 3: Load**: Execute batch operations instead of row-by-row loops.

### Phase 4: Verification & Safety
- **Dry Run Mode**: Add a flag to log intended changes without committing.
- **Circuit Breakers**: Stop the integration if more than X% of users are about to be disabled (safety net for source data corruption).
- **Unit Tests**: Use `pytest` with static Polars DataFrames to verify that the "Mapping" and "Filtering" logic works correctly for all edge cases.

---

## 4. Key Improvements Summary

| Feature | Legacy (Pandas) | Modern (Polars + Clean Arch) |
| :--- | :--- | :--- |
| **Speed** | Sequential, single-threaded | Multi-threaded, SIMD optimized |
| **Memory** | High (eager loading) | Efficient (lazy evaluation) |
| **Updates** | Row-by-row (Slow) | Batch Upserts (Fast) |
| **Testing** | Manual/Database dependent | Unit testable with Mocks |
| **Code Quality** | Procedural / Monolithic | Domain-Driven / Decoupled |
