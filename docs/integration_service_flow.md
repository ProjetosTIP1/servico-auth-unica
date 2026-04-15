# Integration Service: Step-by-Step Data Flow

This document explains the technical flow of the `IntegrationService`, which orchestrates the synchronization of user data between the legacy **SGA (SQL Server)** system and the **SAM (MariaDB)** authentication platform.

---

## 1. Overview
The integration follows an **ETL (Extract, Transform, Load)** pattern, leveraging **Polars** for high-performance data processing. It ensures that user identities, roles, and status are consistent across both systems.

---

## 2. Phase 1: Extraction (Source: SQL Server / SGA)

The process begins by fetching raw data from the SQL Server database using the `SgaPolarsAdapter`.

### User Extraction (`get_users_df`)
A complex SQL query with **Common Table Expressions (CTEs)** is used to identify the "source of truth" for each employee:

1.  **`UltimoContrato`**: Finds the ID of the most recent contract for every person.
2.  **`ContratoDetalhe`**: Fetches details (dates, company, branch) for those latest contracts.
3.  **`UltimoCadastro`**: Deduplicates records in the `FORNECEDOR` table using `ROW_NUMBER()` to ensure only the most recent entry for each CPF/CNPJ is processed.

**Data Joined**:
- `FORNECEDOR (UC)`: Base identity data (CPF/CNPJ, Name).
- `CONTRATOPESSOAL (C)`: Contract dates and company IDs.
- `RH_LOTACAO (L)`: Current department and job role assignment.
- `RH_DEPARTAMENTO (D)`: Human-readable department codes.
- `RH_CARGO (CA)`: Role names.
- `EMPRESA/FILIAL`: Company and branch names used to build the "Unidade" and "Cargo" strings.

**Filters Applied**:
- Excludes empty CPFs/Names.
- Excludes blocked users (`FORBLOQCOMPRA <> 'S'`).
- Handles specific legacy filters for company codes (e.g., excluding `EMPCOD 21`).
- **Recent Update**: The fields `departamento` and `unidade` were normalized to lowercase in the SQL query to match the Python logic.

---

## 3. Phase 2: Extraction (Target: MariaDB / SAM)

Simultaneously, the `SamIntegrationAdapter` fetches the current state of users in MariaDB:

- **Query**: Selects `username`, `full_name`, `is_active`, `unit`, `job`, and `branche` from the `users` table.
- **Purpose**: This creates a baseline to compare against SGA data, allowing the service to detect only what has *changed*, rather than rewriting everything.

---

## 4. Phase 3: Transformation (The "Brain")

The `IntegrationService` uses Polars to process these two datasets in memory.

### Step A: Cleaning and Deduplication
- **Sanitization**: Separators like `.`, `-`, and `/` are removed from usernames (CPFs) to ensure consistency.
- **Unique Check**: Ensures no duplicate usernames exist in the source dataframe.

### Step B: Change Detection (Joins)
1.  **New Users**: An `anti_join` identifies users present in SGA but totally missing from SAM.
2.  **Updated Users**: An `inner_join` finds users present in both. It then filters for differences in fields like:
    - Full Name
    - Job Title (`cargo`)
    - Department (`unidade`)
    - Unit (`departamento`)

### Step C: Password Generation
For **New Users**, a default password hash is created:
1.  Take the first 6 characters of the username.
2.  Append `@@`.
3.  Hash using `bcrypt` (calculated via `get_password_hash`).

### Step D: Disabling Users
The service fetches a list of users marked for disabling in SGA and compares them with currently active users in SAM. Any match is flagged for deactivation.

---

## 5. Phase 4: Loading (Target: MariaDB / SAM)

The final phase writes the processed data back to MariaDB.

### Upsert Logic (`upsert_users`)
Instead of simple inserts, the adapter uses an **Upsert (ON DUPLICATE KEY UPDATE)** strategy:
- If the `username` exists, it updates the fields (name, email, unit, job, etc.).
- If the `username` is new, it creates a fresh record with timestamps.
- This prevents errors on duplicate records and ensures updates are atomic.

### Disabling Logic (`disable_users`)
A single batch `UPDATE` command sets `is_active = 0` for all usernames identified in the transformation phase.

---

## Technical Summary

| Step | Tool | Key Component |
| :--- | :--- | :--- |
| **Extraction** | SQLAlchemy / pyodbc | `SgaPolarsAdapter` (SQL Server) |
| **In-Memory Processing** | Polars | `IntegrationService.sync_users` |
| **Logic** | Python / Bcrypt | `get_password_hash` |
| **Loading** | SQL (MariaDB) | `SamIntegrationAdapter` (MariaDB) |

> [!TIP]
> This "Batch Upsert" approach is significantly faster than row-by-row ORM operations, making it suitable for synchronizing thousands of records in seconds.
