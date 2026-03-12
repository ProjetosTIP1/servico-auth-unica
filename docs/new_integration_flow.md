# Single Auth Microservice (SAM): New Integration Flow

This document describes the modernized, high-performance integration flow between **SGA (SQL Server)** and **SAM (Single Auth Microservice)**.

## 1. Architectural Overview

The integration has been refactored following **Clean Architecture** principles and leverages **Polars** for multi-threaded data processing, replacing the legacy Pandas/Django implementation.

### Key Components:
- **Domain Entities**: Pure data structures representing our internal state.
- **DTOs**: Specialized models for data extraction from external sources (SGA).
- **Ports (Interfaces)**: Decoupled contracts for repositories and services.
- **Adapters**: Concrete implementations using Polars and SQLAlchemy for database-specific logic.
- **Orchestration Service**: The core logic that handles data transformation, comparison, and synchronization.

---

## 2. Domain Models & DTOs

Located in `core/models/integration_models.py`.

### Entities (Internal)
- `IntegrationUser`: Represents a user being synchronized, containing mapped fields for SAM.
- `IntegrationUnit/Department/Position`: Metadata entities for categorization.

### DTOs (Source Data)
- `SgaUserDTO`: Maps the raw output of the SQL Server complex queries.
- `SgaDepartmentDTO/SgaPositionDTO`: Maps metadata from SGA.

---

## 3. The Synchronization Flow (ETL)

The process follows a classic **Extract, Transform, Load (ETL)** pattern, optimized with Polars.

### Step 1: Extraction (E)
The `SgaPolarsAdapter` executes optimized SQL queries against SQL Server. Instead of loading rows one by one, it uses `polars.read_database` to stream the entire result set into a multi-threaded DataFrame.

### Step 2: Transformation (T)
The `IntegrationService` performs the following in-memory operations:
1.  **Cleaning**: Usernames are normalized using Polars expressions (removing dots, dashes, slashes, and whitespace).
2.  **Deduplication**: Ensures only the most recent record per username is processed.
3.  **Change Detection**:
    - **New Users**: Identified via an `anti-join` (SGA users not present in SAM).
    - **Updates**: Identified via an `inner-join` between SGA and SAM, followed by a filter that compares fields (Name, Unit, Job, Department).
    - **Disabled Users**: Identified by checking SGA contract status against SAM's active users.
4.  **Security**: New users have a default password generated and immediately hashed using **Bcrypt**.

### Step 3: Loading (L)
The `SamIntegrationAdapter` performs batch operations:
- **Batch Upsert**: Uses the `INSERT ... ON DUPLICATE KEY UPDATE` pattern in MariaDB. This allows inserting new users and updating existing ones in a single, transactional database trip.
- **Batch Disable**: Updates the `is_active` status for multiple users simultaneously using an `IN` clause.

---

## 4. Key Functions

### `IntegrationService.sync_users(dry_run=True)`
The main entry point for user synchronization.
- **Dry Run Mode**: When enabled, the service logs the number of intended changes (New/Updated/Disabled) without modifying the database.

### `SamIntegrationAdapter.upsert_users(df)`
Converts a Polars DataFrame into a list of dictionaries and executes a prepared SQL statement within an SQLAlchemy transaction.

---

## 5. Performance & Safety Improvements

| Feature | Improvement |
| :--- | :--- |
| **Data Engine** | **Polars** (Rust-backed) is significantly faster and uses less memory than Pandas. |
| **Hashing** | Switched from legacy Django PBKDF2 to modern **Bcrypt**. |
| **Transactions** | Uses `engine.begin()` to ensure "All or Nothing" updates. |
| **Batching** | Eliminated row-by-row loops for database updates. |
| **Validation** | Uses **Pydantic** to ensure data integrity during the transformation phase. |

---

## 6. How to Trigger

The flow is exposed via the following endpoints in `api/handlers/integration_handler.py`:

- `POST /integration/sync-all`: Full metadata and user sync.
- `POST /integration/sync-users`: Synchronize users only.
- `POST /integration/sync-metadata`: Synchronize departments and positions.

All endpoints support a `dry_run=true` query parameter for safe testing.
