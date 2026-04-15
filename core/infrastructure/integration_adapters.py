import polars as pl
from sqlalchemy import create_engine, text
from core.ports.repository import ISgaRepository, ISamIntegrationRepository
from core.helpers.logger_helper import logger
from core.config.settings import settings
from urllib.parse import quote_plus


class SgaPolarsAdapter(ISgaRepository):
    """
    SQL Server adapter using Polars for high-performance data extraction.
    """

    def __init__(self):
        # Polars with SQLAlchemy needs a URL, not just an ODBC string
        user = quote_plus(settings.SQLSERVER_USER)
        password = quote_plus(settings.SQLSERVER_PASSWORD)
        driver = quote_plus(settings.SQLSERVER_DRIVER)
        self.connection_url = (
            f"mssql+pyodbc://{user}:{password}@{settings.SQLSERVER_HOST}:{settings.SQLSERVER_PORT}/"
            f"{settings.SQLSERVER_DB}?driver={driver}&TrustServerCertificate={settings.SQLSERVER_TRUST_SERVER_CERTIFICATE}"
        )
        self._engine = create_engine(self.connection_url)

    def _read_sql(self, sql: str) -> pl.DataFrame:
        try:
            with self._engine.connect() as conn:
                return pl.read_database(query=sql, connection=conn)
        except Exception as e:
            logger.error(f"Error reading from SGA: {e}")
            return pl.DataFrame()

    def get_users_df(self) -> pl.DataFrame:
        sql = """
        WITH UltimoContrato AS (
            SELECT COPFOR, MAX(COPCOD) AS COPCOD
            FROM CONTRATOPESSOAL
            GROUP BY COPFOR
        ),
        ContratoDetalhe AS (
            SELECT C.COPFOR, C.COPCOD, C.COPDTFINAL, C.COPEMP, C.COPFIL
            FROM CONTRATOPESSOAL C
            INNER JOIN UltimoContrato UC ON C.COPFOR = UC.COPFOR AND C.COPCOD = UC.COPCOD
        ),
        UltimoCadastro AS (
            SELECT FORCNPJCPF, FORNOME, FORBLOQCOMPRA, FORCFOR, FORCOD,
                   ROW_NUMBER() OVER (PARTITION BY FORCNPJCPF ORDER BY FORCOD DESC) AS RN
            FROM FORNECEDOR
        )
        SELECT 
            UC.FORCNPJCPF AS username, 
            UC.FORNOME AS nome_completo,
            concat(
                CASE WHEN COPFIL = 0 THEN EMPSIGLA ELSE FILSIGLA END, '-', CA.CODIGO
            ) as cargo,
            d.codigo as departamento,
            IIF(FILSIGLA IS NULL, EMPSIGLA, FILSIGLA) AS unidade
        FROM UltimoCadastro UC
        INNER JOIN ContratoDetalhe C ON UC.FORCOD = C.COPFOR
        JOIN RH_LOTACAO L ON L.PPREF = COPCOD AND INICIO = (SELECT MAX(INICIO) FROM RH_LOTACAO WHERE PPREF = C.COPCOD)
        LEFT OUTER JOIN RH_DEPARTAMENTO D ON D.PPAPLIC = 'G' AND D.CODIGO = L.DEPARTAMENTO
        INNER JOIN RH_CARGO CA ON CA.PPAPLIC = 'E' AND CA.PPREF = (C.COPFIL * 1000000 + C.COPEMP) AND CA.CODIGO = L.CARGO
        LEFT JOIN EMPRESA E ON C.COPEMP = E.EMPCOD
        LEFT JOIN FILIAL F ON F.FILCOD = C.COPFIL
        WHERE LEFT(UC.FORCNPJCPF, 1) != '' 
        AND LEFT(UC.FORNOME, 1) != ''
        AND UC.FORBLOQCOMPRA <> 'S'
        AND (UC.FORCFOR <> 21 OR (UC.FORCFOR = 21 AND C.COPDTFINAL < CONVERT(DATE, '02/01/1900', 103)))
        AND UC.RN = 1
        AND E.EMPCOD NOT IN (21)
        """
        return self._read_sql(sql)

    def get_disabled_users_df(self) -> pl.DataFrame:
        sql = """
        WITH UltimoContrato AS (
            SELECT COPFOR, MAX(COPCOD) AS COPCOD FROM CONTRATOPESSOAL GROUP BY COPFOR
        ),
        ContratoDetalhe AS (
            SELECT C.COPFOR, C.COPCOD, C.COPDTFINAL, C.COPEMP, C.COPFIL
            FROM CONTRATOPESSOAL C
            INNER JOIN UltimoContrato UC ON C.COPFOR = UC.COPFOR AND C.COPCOD = UC.COPCOD
        ),
        UltimoCadastro AS (
            SELECT FORCNPJCPF, FORNOME, FORBLOQCOMPRA, FORCFOR, FORCOD,
                   ROW_NUMBER() OVER (PARTITION BY FORCNPJCPF ORDER BY FORCOD DESC) AS RN
            FROM FORNECEDOR
        )
        SELECT 
            UC.FORCNPJCPF AS username, 
            '0' as is_active
        FROM UltimoCadastro UC
        INNER JOIN ContratoDetalhe C ON UC.FORCOD = C.COPFOR
        LEFT JOIN EMPRESA E ON C.COPEMP = E.EMPCOD
        WHERE UC.FORBLOQCOMPRA <> 'S'
        AND (UC.FORCFOR = 21 AND C.COPDTFINAL > CONVERT(DATE, '01/12/2025', 103))
        AND UC.RN = 1
        AND E.EMPCOD NOT IN (21)
        """
        return self._read_sql(sql)

    def get_departments_df(self) -> pl.DataFrame:
        sql = "SELECT CODIGO as Codigo, NOME as Nome FROM RH_DEPARTAMENTO WHERE PPAPLIC = 'G'"
        return self._read_sql(sql)

    def get_positions_df(self) -> pl.DataFrame:
        sql = """
        SELECT DISTINCT
            concat(CASE WHEN COPFIL = 0 THEN EMPSIGLA ELSE FILSIGLA END, '-', C.CODIGO) as Codigo,
            C.NOME as Nome,
            d.codigo as Departamento,
            CASE WHEN COPFIL = 0 THEN EMPSIGLA ELSE FILSIGLA END as Filial
        FROM CONTRATOPESSOAL COP
        INNER JOIN FORNECEDOR F ON FORCOD = COPFOR
        INNER JOIN RH_LOTACAO L ON L.PPREF = COPCOD AND INICIO = (SELECT MAX(INICIO) FROM RH_LOTACAO WHERE PPREF = COP.COPCOD)
        INNER JOIN RH_DEPARTAMENTO D ON D.PPAPLIC = 'G' AND D.CODIGO = L.DEPARTAMENTO
        INNER JOIN RH_CARGO C ON C.PPAPLIC = 'E' AND C.PPREF = (COP.COPFIL * 1000000 + COP.COPEMP) AND C.CODIGO = L.CARGO
        INNER JOIN EMPRESA ON EMPCOD = COPEMP
        LEFT JOIN FILIAL ON FILCOD = COPFIL
        WHERE COPCOD > 0
        AND EMPCOD IN (1,2,3,4,7,8,10) AND (FILCOD IN (1,3,5,6,8,10,11,30) OR FILCOD IS NULL)
        AND (COPDTFINAL < CONVERT(DATETIME, '01/01/1900', 103))
        """
        return self._read_sql(sql)


class SamIntegrationAdapter(ISamIntegrationRepository):
    """
    SAM adapter using Polars and SQLAlchemy for batch operations.
    """

    def __init__(self):
        self.connection_url = settings.database_url
        self._engine = create_engine(self.connection_url)

    def get_current_users_df(self) -> pl.DataFrame:
        sql = """
        SELECT username, full_name as nome_completo, is_active, unit as UNIDADE, job as cargo, branche as Departamento
        FROM users
        """
        try:
            with self._engine.connect() as conn:
                return pl.read_database(query=sql, connection=conn)
        except Exception as e:
            logger.error(f"Error reading current users from SAM: {e}")
            return pl.DataFrame()

    def get_units_mapping_df(self) -> pl.DataFrame:
        # Assuming there's a units table or similar. For now based on legacy logic:
        # In legacy it was 'valeflow_unidades'
        sql = "SELECT ID, SIGLA FROM units WHERE active = 1"
        try:
            with self._engine.connect() as conn:
                return pl.read_database(query=sql, connection=conn)
        except Exception as e:
            logger.error(f"Error reading units from SAM: {e}")
            return pl.DataFrame()

    def get_positions_mapping_df(self) -> pl.DataFrame:
        # Assuming a positions table
        sql = "SELECT id, code FROM positions"
        try:
            with self._engine.connect() as conn:
                return pl.read_database(query=sql, connection=conn)
        except Exception as e:
            logger.error(f"Error reading positions from SAM: {e}")
            return pl.DataFrame()

    def upsert_departments(self, df: pl.DataFrame) -> int:
        if df.is_empty():
            return 0

        # Batch upsert using SQL construction for "ON DUPLICATE KEY UPDATE"
        # Or just insert ignore if that's the requirement.
        # For simplicity and performance, we'll use a transaction.
        count = 0
        with self._engine.begin() as conn:
            for row in df.to_dicts():
                stmt = text("""
                    INSERT INTO departments (id, name) 
                    VALUES (:id, :name)
                    ON DUPLICATE KEY UPDATE name = VALUES(name)
                """)
                conn.execute(stmt, {"id": row["Codigo"], "name": row["Nome"]})
                count += 1
        return count

    def upsert_positions(self, df: pl.DataFrame) -> int:
        if df.is_empty():
            return 0
        count = 0
        with self._engine.begin() as conn:
            for row in df.to_dicts():
                stmt = text("""
                    INSERT INTO positions (code, name, branche) 
                    VALUES (:code, :name, :branche)
                    ON DUPLICATE KEY UPDATE name = VALUES(name), branche = VALUES(branche)
                """)
                conn.execute(
                    stmt,
                    {
                        "code": row["Codigo"],
                        "name": row["Nome"],
                        "branche": row["Filial"],
                    },
                )
                count += 1
        return count

    def upsert_users(self, df: pl.DataFrame) -> int:
        if df.is_empty():
            return 0
        count = 0
        with self._engine.begin() as conn:
            for row in df.to_dicts():
                # SAM Schema columns: username, email, full_name, unit, job, branche, is_active, hashed_password
                stmt = text("""
                    INSERT INTO users (username, full_name, email, unit, job, branche, is_active, hashed_password, created_at, updated_at)
                    VALUES (:username, :full_name, :email, :unit, :job, :branche, :is_active, :hashed_password, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE 
                        full_name = VALUES(full_name),
                        email = VALUES(email),
                        unit = VALUES(unit),
                        job = VALUES(job),
                        branche = VALUES(branche),
                        is_active = VALUES(is_active),
                        updated_at = NOW()
                """)
                conn.execute(
                    stmt,
                    {
                        "username": row["username"],
                        "full_name": row["nome_completo"],
                        "email": row.get("email"),
                        "unit": row.get("UNIDADE"),
                        "job": row.get("cargo"),
                        "branche": row.get("Departamento"),
                        "is_active": row.get("is_active", 1),
                        "hashed_password": row.get("password", "NOT_SET"),
                    },
                )
                count += 1
        return count

    def disable_users(self, usernames: list[str]) -> int:
        if not usernames:
            return 0
        with self._engine.begin() as conn:
            stmt = text(
                "UPDATE users SET is_active = 0, updated_at = NOW() WHERE username IN :usernames"
            )
            result = conn.execute(stmt, {"usernames": tuple(usernames)})
            return result.rowcount
