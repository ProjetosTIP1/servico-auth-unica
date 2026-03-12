import pandas
import sqlalchemy
from urllib.parse import quote_plus  # para o @ da senha
import os
from dotenv import load_dotenv
import time
import sys
import django
from pathlib import Path
from django.contrib.auth.hashers import make_password
import logging

logger = logging.getLogger("app")


# BASE_DIR vai ser 'valeflow'
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Adiciona 'backend' ao sys.path
sys.path.append(str(BASE_DIR))

# Nome do settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

# Inicializa o Django
try:
    django.setup()
except Exception as e:
    logger.error(f"Erro ao inicializar o Django: {e}")


load_dotenv(BASE_DIR / ".env")

from app.services.appropriation_service import (
    appropriations_customer,
    deactivate_future_appropriations_user,
)

SQL_USER_MAP = """
    SELECT id, username FROM custom_user
"""
SQL_USER_MAP_CARGO = """
    SELECT id, Codigo FROM valeflow_cargos
"""
SQL_UNIT_VALEFLOW = """
    SELECT
        ID,
        SIGLA UNIDADE
    FROM valeflow_unidades
    WHERE ativo = 1
"""
SQL_USERS_VALEFLOW = """
    SELECT 
        username, 
        first_name, 
        email, 
        u.SIGLA UNIDADE
    FROM custom_user au
    LEFT JOIN tb_custom_user tu ON tu.user_id = au.id
    LEFT JOIN tb_unidade u ON u.ID = tu.UNIDADE
"""
SQL_USERS_VALEFLOW = """
    SELECT 
        username, 
        nome_completo, 
        u.SIGLA UNIDADE,
        cargo,
        departamento Departamento
    FROM custom_user au
    LEFT JOIN valeflow_unidades u ON u.ID = au.unidade
"""
SQL_USERS_SGA = """
   WITH UltimoContrato AS (
        SELECT 
            COPFOR,
            MAX(COPCOD) AS COPCOD
        FROM CONTRATOPESSOAL
        GROUP BY COPFOR
    ),

	UltimoCadastro AS(
		SELECT
			FORCNPJCPF,
			FORNOME,
			FOREMAIL,
			FORCOD,
			ROW_NUMBER() OVER (PARTITION BY FORCNPJCPF ORDER BY FORCOD DESC) AS RN
		FROM FORNECEDOR
	)
	
    SELECT  
        --FO.FORCOD,
        --CP.COPCOD,
        FO.FORCNPJCPF username, 
        FO.FORNOME first_name,
        FO.FOREMAIL email,
        IIF(FILSIGLA IS NULL, EMPSIGLA, FILSIGLA) AS UNIDADE
    FROM UltimoCadastro UC
	LEFT JOIN FORNECEDOR FO ON FO.FORCOD = UC.FORCOD
    LEFT JOIN UltimoContrato CP ON FO.FORCOD = CP.COPFOR
    LEFT JOIN CONTRATOPESSOAL C ON C.COPCOD = CP.COPCOD
    LEFT JOIN EMPRESA E ON C.COPEMP = E.EMPCOD
    LEFT JOIN FILIAL F ON F.FILCOD = C.COPFIL
    WHERE LEFT(FO.FORCNPJCPF,1) != '' 
    AND LEFT(FO.FORNOME,1) != ''
	AND FORBLOQCOMPRA <> 'S'
	AND ( FORCFOR <> 21 OR (FORCFOR = 21 AND COPDTFINAL < CONVERT(DATE,'02/01/1900',103)))
	AND UC.RN = 1
	ORDER BY FO.FORNOME
"""
SQL_USERS_SGA = """
WITH UltimoContrato AS (
    SELECT 
        COPFOR,
        MAX(COPCOD) AS COPCOD
    FROM CONTRATOPESSOAL
    GROUP BY COPFOR
),

ContratoDetalhe AS (
    SELECT 
        C.COPFOR,
        C.COPCOD,
        C.COPDTFINAL,
        C.COPEMP,
        C.COPFIL
    FROM CONTRATOPESSOAL C
    INNER JOIN UltimoContrato UC ON C.COPFOR = UC.COPFOR AND C.COPCOD = UC.COPCOD
),

UltimoCadastro AS (
    SELECT
        FORCNPJCPF,
        FORNOME,
        FORBLOQCOMPRA,
        FORCFOR,
        FORCOD,
        ROW_NUMBER() OVER (PARTITION BY FORCNPJCPF ORDER BY FORCOD DESC) AS RN
    FROM FORNECEDOR
)

SELECT 
    UC.FORCNPJCPF AS username, 
    UC.FORNOME AS nome_completo,
	concat(
            CASE
                WHEN COPFIL = 0 THEN EMPSIGLA
                ELSE FILSIGLA
            END,                                   '-',
			CA.CODIGO
    )cargo,
    d.codigo Departamento,
    IIF(FILSIGLA IS NULL, EMPSIGLA, FILSIGLA) AS UNIDADE
FROM UltimoCadastro UC
INNER JOIN ContratoDetalhe C ON UC.FORCOD = C.COPFOR
JOIN RH_LOTACAO L ON L.PPREF = COPCOD  AND INICIO = (SELECT MAX(INICIO) FROM RH_LOTACAO
                            WHERE PPREF = C.COPCOD) -- Imprimi somente a ultima alocacao
LEFT OUTER JOIN RH_DEPARTAMENTO D ON D.PPAPLIC = 'G' AND D.CODIGO = L.DEPARTAMENTO
INNER JOIN RH_CARGO CA ON CA.PPAPLIC = 'E' AND CA.PPREF = (C.COPFIL * 1000000 + C.COPEMP) AND CA.CODIGO = L.CARGO
LEFT JOIN EMPRESA E ON C.COPEMP = E.EMPCOD
LEFT JOIN FILIAL F ON F.FILCOD = C.COPFIL
WHERE LEFT(UC.FORCNPJCPF,1) != '' 
AND LEFT(UC.FORNOME,1) != ''
AND UC.FORBLOQCOMPRA <> 'S'
AND ( UC.FORCFOR <> 21 OR (UC.FORCFOR = 21 AND C.COPDTFINAL < CONVERT(DATE,'02/01/1900',103)))
AND UC.RN = 1
AND E.EMPCOD NOT IN (21)
"""
SQL_CARGOS_SGA = """
                SELECT DISTINCT
                    concat(
                            CASE
                                WHEN COPFIL = 0 THEN EMPSIGLA
                                ELSE FILSIGLA
                            END,
                            '-',
                            C.CODIGO
                            )Codigo,
                    C.NOME Nome,
                    d.codigo Departamento,
                    CASE
                        WHEN COPFIL = 0 THEN EMPSIGLA
                        ELSE FILSIGLA
                    END Filial
                FROM CONTRATOPESSOAL COP
                INNER JOIN FORNECEDOR F ON FORCOD = COPFOR
                INNER JOIN RH_LOTACAO L ON L.PPREF = COPCOD AND INICIO = (SELECT MAX(INICIO) FROM RH_LOTACAO
                                                                    WHERE PPREF = COP.COPCOD) -- Imprimi somente a ultima alocacao
                INNER JOIN RH_DEPARTAMENTO D ON D.PPAPLIC = 'G' AND D.CODIGO = L.DEPARTAMENTO
                INNER JOIN RH_CARGO C ON C.PPAPLIC = 'E' AND C.PPREF = (COP.COPFIL * 1000000 + COP.COPEMP) AND C.CODIGO = L.CARGO
                INNER JOIN EMPRESA ON EMPCOD = COPEMP
                LEFT JOIN FILIAL ON FILCOD = COPFIL
                WHERE COPCOD > 0
                AND EMPCOD IN (1,2,3,4,7,8,10) AND (FILCOD IN (1,3,5,6,8,10,11,30) OR FILCOD IS NULL)
                AND (COPDTFINAL < CONVERT(DATETIME, '01/01/1900', 103) )
                ORDER BY Codigo, Nome
"""
SQL_DEPARTAMENTOS_SGA = """
    select 
        CODIGO Codigo,
        NOME Nome
    from RH_DEPARTAMENTO 
    where PPAPLIC = 'G' 
"""
SQL_USERS_SGA_DISABLED = """
WITH UltimoContrato AS (
    SELECT 
        COPFOR,
        MAX(COPCOD) AS COPCOD
    FROM CONTRATOPESSOAL
    GROUP BY COPFOR
),

ContratoDetalhe AS (
    SELECT 
        C.COPFOR,
        C.COPCOD,
        C.COPDTFINAL,
        C.COPEMP,
        C.COPFIL
    FROM CONTRATOPESSOAL C
    INNER JOIN UltimoContrato UC ON C.COPFOR = UC.COPFOR AND C.COPCOD = UC.COPCOD
),

UltimoCadastro AS (
    SELECT
        FORCNPJCPF,
        FORNOME,
        FORBLOQCOMPRA,
        FORCFOR,
        FORCOD,
        ROW_NUMBER() OVER (PARTITION BY FORCNPJCPF ORDER BY FORCOD DESC) AS RN
    FROM FORNECEDOR
)

SELECT 
    UC.FORCNPJCPF AS username, 
    UC.FORNOME AS nome_completo,
	'0' is_active,
	concat(
            CASE
                WHEN COPFIL = 0 THEN EMPSIGLA
                ELSE FILSIGLA
            END,                                   '-',
			CA.CODIGO
    )cargo,
    d.codigo Departamento,
    IIF(FILSIGLA IS NULL, EMPSIGLA, FILSIGLA) AS UNIDADE
FROM UltimoCadastro UC
INNER JOIN ContratoDetalhe C ON UC.FORCOD = C.COPFOR
JOIN RH_LOTACAO L ON L.PPREF = COPCOD  AND INICIO = (SELECT MAX(INICIO) FROM RH_LOTACAO
                            WHERE PPREF = C.COPCOD) -- Imprimi somente a ultima alocacao
LEFT OUTER JOIN RH_DEPARTAMENTO D ON D.PPAPLIC = 'G' AND D.CODIGO = L.DEPARTAMENTO
INNER JOIN RH_CARGO CA ON CA.PPAPLIC = 'E' AND CA.PPREF = (C.COPFIL * 1000000 + C.COPEMP) AND CA.CODIGO = L.CARGO
LEFT JOIN EMPRESA E ON C.COPEMP = E.EMPCOD
LEFT JOIN FILIAL F ON F.FILCOD = C.COPFIL
WHERE LEFT(UC.FORCNPJCPF,1) != '' 
AND LEFT(UC.FORNOME,1) != ''
AND UC.FORBLOQCOMPRA <> 'S'
AND (UC.FORCFOR = 21 AND C.COPDTFINAL > CONVERT(DATE,'01/12/2025',103))
AND UC.RN = 1
AND E.EMPCOD NOT IN (21)
"""
SQL_USERS_VALEFLOW_DISABLED = """
    SELECT 
        username, 
        nome_completo, 
        is_active,
        u.SIGLA UNIDADE,
        cargo,
        departamento Departamento
    FROM custom_user au
    LEFT JOIN valeflow_unidades u ON u.ID = au.unidade
    where is_active = 1
"""


class Sga:
    def __init__(self):
        pass

    def get_connection_string(self):
        driver = os.getenv("DRIVER_ODBC")
        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")
        user = os.getenv("SQL_USER")
        password = quote_plus(os.getenv("SQL_PASSWORD") or "")
        if not all([server, database, user]):
            raise ValueError(
                "Missing required environment variables for SQL Server connection: SQL_SERVER, SQL_DATABASE, SQL_USER"
            )
        return f"mssql+pyodbc://{user}:{password}@{server}/{database}?driver={quote_plus(driver)}&TrustServerCertificate=yes"

    def get_sql(self, sql: str):
        try:
            logger.info("Attempting to get connection string...")
            connection_string = self.get_connection_string()
            logger.info("Connection string obtained. Attempting to create engine...")
            engine = sqlalchemy.create_engine(connection_string)
            logger.info("Engine created. Attempting to connect...")
            # with engine.connect() as connection:
            logger.info("Connection established. Attempting to read SQL query...")
            df = pandas.read_sql_query(sql, engine.connect())
            logger.info("SQL query executed successfully.")
        except Exception as e:
            error_msg = "get_sql, erro ao criar o df: " + str(e)
            logger.error(error_msg)
            df = pandas.DataFrame()  # retorna um df vazio para nao parar o processo
        logger.info("Returning DataFrame from get_sql.")
        return df


class Valeflow:
    def __init__(self):
        pass

    def get_engine(self):
        server = os.getenv("MYSQL_HOST")
        database = os.getenv("MYSQL_DATABASE")
        user = os.getenv("MYSQL_USER")
        password = quote_plus(os.getenv("MYSQL_PASSWORD") or "")
        port = 3306
        max_tentativas = 40
        tentativas = 0
        while tentativas < max_tentativas:
            try:
                engine = sqlalchemy.create_engine(
                    f"mysql+pymysql://{user}:{password}@{server}:{port}/{database}"
                )
                return engine
            except Exception as e:
                msg_erro = "get_engine, erro ao criar a conexão: " + str(e)
                logger.error(msg_erro)
                tentativas += 1
                logger.error(
                    f"Tentativa {tentativas} de {max_tentativas} para conectar ao banco de dados MySQL"
                )
                if tentativas > max_tentativas:
                    logger.error(
                        "Excedido o número máximo de tentativas para conectar ao banco de dados MySQL"
                    )
                    logger.error("Finalizando o processo")
                    sys.exit()
                logger.error("Aguardando para tentar conectar de novo no banco")
                time.sleep(1800)

        logger.error(
            "--- Falha ao estabelecer conexão com o banco de dados após {} tentativas".format(
                max_tentativas
            )
        )
        return None

    def get_sql(self, sql: str, type={}):
        try:
            engine = self.get_engine()
            if engine is None:
                return (
                    pandas.DataFrame()
                )  # Retorna um DataFrame vazio se a conexão falhar
            with engine.connect() as connection:
                df = pandas.read_sql_query(sql, connection, dtype=type)
        except Exception as e:
            error_msg = "get_sql, erro ao criar o df: " + str(e)
            logger.error(error_msg)
            df = pandas.DataFrame()  # Retorna um DataFrame vazio se ocorrer um erro

        return df

    def insertDf(self, df, tabela: str):
        engine = self.get_engine()
        try:
            df.to_sql(tabela, con=engine, if_exists="append", index=False)
        except Exception as e:
            error_msg = f"insertDf Erro ao inserir df: {e}"
            logger.error(error_msg)

    def update_valeflow(
        self, table_name: str, where_conditions: dict, values_to_update: dict
    ):
        """
        Função genérica para atualizar dados em uma tabela.

        :param table_name: Nome da tabela como string
        :param where_conditions: Dicionário com as condições de filtro para o WHERE
        :param values_to_update: Dicionário com os valores a serem atualizados
        """
        # Criar uma conexão com o banco de dados
        engine = self.get_engine()
        if engine is None:
            logger.error(
                "--- Erro ao conectar ao banco de dados. Verifique as credenciais e a conexão."
            )
            return
        with engine.connect() as connection:
            try:
                # Criar a parte SET da query, ex: "coluna1 = :coluna1, coluna2 = :coluna2"
                set_clause = ", ".join(
                    [f"{col} = :{col}" for col in values_to_update.keys()]
                )

                # Criar a parte WHERE da query, ex: "coluna_id = :coluna_id AND outra_coluna = :outra_coluna"
                where_clause = " AND ".join(
                    [f"{col} = :{col}" for col in where_conditions.keys()]
                )

                # Construir a query SQL completa
                sql_query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"

                # Combinar valores de update e de where em um único dicionário
                combined_params = {**values_to_update, **where_conditions}

                # Executar a query
                result = connection.execute(sqlalchemy.text(sql_query), combined_params)
                connection.commit()
                affected_rows = result.rowcount

                logger.info("Dados atualizados com sucesso!")
                logger.info(f"Linhas afetadas: {affected_rows}")

            except Exception as e:
                error_msg = f" update_valeflow. Erro ao atualizar dados: {e}"
                logger.error(error_msg)

    def update_from_df(self, df, table_name: str, where_column: list):
        """
        Atualiza os dados de uma tabela com base em um DataFrame.

        :param df: DataFrame contendo os dados a serem atualizados
        :param table_name: Nome da tabela como string
        :param where_column: Coluna usada para identificar as linhas a serem atualizadas
        """
        # engine = self.get_engine()
        # with engine.connect() as connection:
        for index, row in df.iterrows():
            # else row[0]
            where = {}
            for linha, col in enumerate(where_column):
                where[col] = row[col]

            # if len(where_column) == 1:
            # where_value = row[where_column[0]]
            # values_to_update = {col: row[col] for col in df.columns if col != where_column[0]}
            # where = {where_column[0]: where_value}
            # else:
            # where_value = tuple(row[col] for col in where_column)
            values_to_update = {
                col: None if pandas.isna(row[col]) else row[col]
                for col in df.columns
                if col not in where_column
            }

            self.update_valeflow(table_name, where, values_to_update)


class Integration:
    def __init__(self):
        try:
            self.df_users_sga = sga.get_sql(SQL_USERS_SGA)
            self.df_users_sga["username"] = (
                self.df_users_sga["username"]
                .str.replace(".", "")
                .str.replace("/", "")
                .str.replace("-", "")
            )  # Limpar username removendo caracteres especiais
            self.df_users_sga["username"] = self.df_users_sga["username"].str.replace(
                " ", "", regex=False
            )  # retirar espaços em branco
            self.df_users_sga = self.df_users_sga.drop_duplicates(
                subset="username", keep="last"
            )
        except Exception as e:
            error_msg = (
                "Integration __init__, erro ao criar o df de usuários do SGA: " + str(e)
            )
            logger.error(error_msg)
            self.df_users_sga = (
                pandas.DataFrame()
            )  # retorna um df vazio para nao parar o processo

    def maping(
        self,
        df: pandas.DataFrame,
        sql: str,
        colum_df: str,
        colum_df_map: str,
        colum_maping: str,
    ):
        df_map = valeflow.get_sql(sql)  # Obter o mapeamento
        mapeamento = dict(
            zip(df_map[colum_df_map], df_map[colum_maping])
        )  # Criar um mapeamento
        df[colum_df] = df[colum_df].map(mapeamento)  # Mapear no df
        return df

    def new_department(self):
        df_department_Sga = sga.get_sql(SQL_DEPARTAMENTOS_SGA)
        df_department_valeflow = valeflow.get_sql(
            "SELECT id Codigo, Nome FROM valeflow_departamentos"
        )

        if df_department_valeflow.empty:
            df_department_valeflow = pandas.DataFrame(columns=["Codigo", "Nome"])
        df_merged = pandas.merge(
            df_department_Sga,
            df_department_valeflow,
            on="Codigo",
            how="left",
            suffixes=("_sga", "_valeflow"),
        )  # Unir os DataFrames do SGA e valeflow com base no username

        df_new = df_merged.copy()
        df_new = df_new[
            df_new["Nome_valeflow"].isnull()
        ]  # Filtrar apenas os usuários que estão no SGA e não estão no valeflow

        df_new = df_new.drop(columns=["Nome_valeflow"])  # Retirar colunas do valeflow
        df_new.rename(
            columns=lambda x: x.replace("_sga", ""), inplace=True
        )  # Renomear colunas do SGA para o padrão do valeflow

        df_new.rename(
            columns={"Codigo": "id"}, inplace=True
        )  # Renomear coluna Codigo para id

        logger.info(f"Inserindo {len(df_new)} cargos novos no valeflow") if len(
            df_new
        ) > 0 else None

        valeflow.insertDf(
            df_new, "valeflow_departamentos"
        )  # Inserir novos usuários no valeflow

    def new_position(self):
        df_cargos_Sga = sga.get_sql(SQL_CARGOS_SGA)
        df_cargos_valeflow = valeflow.get_sql(
            "SELECT Codigo, Nome, Filial FROM valeflow_cargos"
        )

        if df_cargos_valeflow.empty:
            df_cargos_valeflow = pandas.DataFrame(columns=["Codigo", "Nome"])
        df_merged = pandas.merge(
            df_cargos_Sga,
            df_cargos_valeflow,
            on="Codigo",
            how="left",
            suffixes=("_sga", "_valeflow"),
        )  # Unir os DataFrames do SGA e valeflow com base no username

        df_novos = df_merged.copy()
        df_novos = df_novos[
            df_novos["Nome_valeflow"].isnull()
        ]  # Filtrar apenas os usuários que estão no SGA e não estão no valeflow

        df_novos = df_novos.drop(
            columns=["Nome_valeflow"]
        )  # Retirar colunas do valeflow
        df_novos.rename(
            columns=lambda x: x.replace("_sga", ""), inplace=True
        )  # Renomear colunas do SGA para o padrão do valeflow

        logger.info(f"Inserindo {len(df_novos)} cargos novos no valeflow") if len(
            df_novos
        ) > 0 else None

        valeflow.insertDf(
            df_novos, "valeflow_cargos"
        )  # Inserir novos usuários no valeflow

    def new_users(self):

        df_users_valeflow = valeflow.get_sql(SQL_USERS_VALEFLOW)

        df_merged = pandas.merge(
            self.df_users_sga,
            df_users_valeflow,
            on="username",
            how="left",
            suffixes=("_sga", "_valeflow"),
        )  # Unir os DataFrames do SGA e valeflow com base no username

        df_novos = df_merged.copy()
        df_novos = df_novos[
            df_novos["nome_completo_valeflow"].isnull()
        ]  # Filtrar apenas os usuários que estão no SGA e não estão no valeflow

        df_novos["password"] = (
            "pbkdf2_sha256$600000$ICVcnhzBIZb6bpdBX4QkKr$Ato2EsTZU8LTOTtW6Rf6WYKdYOF9L/zOWJ04s804j2k="
        )

        # df_novos = df_novos.head(20) # Limitando para o django Q não entrar em loop

        for index, row in df_novos.iterrows():
            df_novos.at[index, "password"] = make_password(
                row["username"][:6] + "@@"
            )  # Definir a senha como os primeiros 6 caracteres do username com @@ no final
            print(f"Definindo a senha {index + 1} de {len(df_novos.index)} usuários")

        # df_novos['password'] = df_novos['username'].apply(
        #     lambda x: make_password(x.replace('.', '').replace('/', '').replace('-', '')[:6]+'@@')
        # ) # Definir a senha como os primeiros 6 caracteres do username com @@ no final com hashing do django

        df_novos = df_novos.drop(
            columns=[
                "nome_completo_valeflow",
                "UNIDADE_valeflow",
                "Departamento_valeflow",
                "cargo_valeflow",
            ]
        )  # Retirar colunas do valeflow
        df_novos.rename(
            columns=lambda x: x.replace("_sga", ""), inplace=True
        )  # Renomear colunas do SGA para o padrão do valeflow

        df_novos["is_active"] = 1  # Definir o usuário como ativo
        df_novos["INTEGRADO"] = 1  # Definir o usuário como ativo

        # df_novos['username'] = df_novos['username'].str.replace(' ', '', regex=False) # retirar espaços em branco

        # df_novos = df_novos.drop_duplicates(subset='username', keep='first')

        df_novos = self.maping(
            df_novos, SQL_UNIT_VALEFLOW, "UNIDADE", "UNIDADE", "ID"
        )  # Mapear a unidade para o id da unidade

        df_novos = self.maping(
            df_novos, SQL_USER_MAP_CARGO, "cargo", "Codigo", "id"
        )  # Mapear o cargo para o id do cargo

        df_novos["UNIDADE"] = df_novos["UNIDADE"].astype(
            "Int64"
        )  # Evitnado valores float por cusas de possiveis NaNs

        logger.info(f"Inserindo {len(df_novos)} usuários novos no valeflow") if len(
            df_novos
        ) > 0 else None
        # valeflow.insertDf(df_novos.drop(columns=['UNIDADE']), 'custom_user') # Inserir novos usuários no valeflow
        valeflow.insertDf(df_novos, "custom_user")  # Inserir novos usuários no valeflow
        df_novos_funcionarios = (
            df_novos.copy()
        )  # copiando o df para ser usado na diarização das tarefas

        # df_user_map = valeflow.get_sql(SQL_USER_MAP) # Obter o mapeamento de id do usuário para o id do custom user
        # mapeamento_usuarios = dict(zip(df_user_map['username'], df_user_map['id'])) # Criar um mapeamento de username para ID do usuario
        # df_novos['username'] = df_novos['username'].map(mapeamento_usuarios) # Mapear o username para o id do usuario

        df_novos = self.maping(
            df_novos, SQL_USER_MAP, "username", "username", "id"
        )  # Mapear o username para o id do usuario
        df_novos.rename(
            columns={"username": "customuser_id"}, inplace=True
        )  # Renomear coluna

        df_novos["customuser_id"] = df_novos["customuser_id"].astype(
            "Int64"
        )  # Evitando valores float por cusas de possiveis NaNs

        df_novos["group_id"] = 1

        logger.info(
            f"Inserindo {len(df_novos)} grupos para usuários novos no valeflow"
        ) if len(df_novos) > 0 else None
        df_novos.drop(
            columns=[
                "password",
                "nome_completo",
                "is_active",
                "UNIDADE",
                "cargo",
                "Departamento",
                "INTEGRADO",
            ],
            inplace=True,
        )  # Retirar colunas desnecessárias
        valeflow.insertDf(
            df_novos, "custom_user_groups"
        )  # Inserir grupo de usuário dos novos usuários no valeflow

        # Diarizando as tarefas dos novos funcionarios
        for index, row in df_novos_funcionarios.iterrows():
            logger.info(
                f"Criando apropriações para o usuário {row['nome_completo']} com username {row['username']} "
            )
            appropriations_customer(row["username"])

    def update_users(self):
        df_users_valeflow = valeflow.get_sql(
            SQL_USERS_VALEFLOW
        )  # Atualizar os ususarios do valeflow após inserção para procurar as diferenças

        self.df_users_sga = self.maping(
            self.df_users_sga, SQL_USER_MAP_CARGO, "cargo", "Codigo", "id"
        )  # Mapear o cargo para o id do cargo

        self.df_users_sga["cargo"] = self.df_users_sga["cargo"].astype(
            "Int64"
        )  # Evitando valores float por cusas de possiveis NaNs
        self.df_users_sga["Departamento"] = self.df_users_sga["Departamento"].astype(
            "Int64"
        )  # Evitando valores float por cusas de possiveis NaNs

        df_users_valeflow["cargo"] = df_users_valeflow["cargo"].astype(
            "Int64"
        )  # Evitando valores float por cusas de possiveis NaNs
        df_users_valeflow["Departamento"] = df_users_valeflow["Departamento"].astype(
            "Int64"
        )  # Evitando valores float por cusas de possiveis NaNs

        df_merged = pandas.merge(
            self.df_users_sga,
            df_users_valeflow,
            on="username",
            how="inner",
            suffixes=("_sga", "_valeflow"),
        )  # Unir os DataFrames do SGA e valeflow com base no username

        df_alterados = df_merged.copy()

        df_alterados = df_alterados.fillna(
            0
        )  # definir NaNs como 0 para facilitar a comparação

        df_alterados = df_alterados[
            ~(
                (
                    df_alterados["nome_completo_sga"]
                    == df_alterados["nome_completo_valeflow"]
                )
                | (
                    df_alterados["nome_completo_sga"].isna()
                    & df_alterados["nome_completo_valeflow"].isna()
                )
            )
            | ~(
                (
                    df_alterados["Departamento_sga"]
                    == df_alterados["Departamento_valeflow"]
                )
                | (
                    df_alterados["Departamento_sga"].isna()
                    & df_alterados["Departamento_valeflow"].isna()
                )
            )
            | ~(
                (df_alterados["cargo_sga"] == df_alterados["cargo_valeflow"])
                | (
                    df_alterados["cargo_sga"].isna()
                    & df_alterados["cargo_valeflow"].isna()
                )
            )
            | ~(
                (df_alterados["UNIDADE_sga"] == df_alterados["UNIDADE_valeflow"])
                | (
                    df_alterados["UNIDADE_sga"].isna()
                    & df_alterados["UNIDADE_valeflow"].isna()
                )
            )
        ]  # Comparando com auth_user para verificar se o nome, departamento, cargo ou unidade foram alterados

        df_alterados = df_alterados.drop(
            columns=[
                "nome_completo_valeflow",
                "UNIDADE_valeflow",
                "cargo_valeflow",
                "Departamento_valeflow",
            ]
        )  # Retirar colunas do valeflow
        df_alterados.rename(
            columns=lambda x: x.replace("_sga", ""), inplace=True
        )  # Renomear colunas do SGA para o padrão do valeflow

        self.maping(
            df_alterados, SQL_UNIT_VALEFLOW, "UNIDADE", "UNIDADE", "ID"
        )  # Mapear a unidade para o id da unidade

        df_alterados["UNIDADE"] = df_alterados["UNIDADE"].astype(
            "Int64"
        )  # Evitnado valores float por cusas de possiveis NaNs

        # valeflow.update_from_df(df_alterados.drop(columns=['UNIDADE']), 'custom_user', ['username']) # Atualizar os usuários no valeflow
        valeflow.update_from_df(
            df_alterados, "custom_user", ["username"]
        )  # Atualizar os usuários no valeflow

        # Diarizando as tarefas dos novos funcionarios
        for index, row in df_alterados.iterrows():
            logger.info(
                f"Funcionário {row['nome_completo']} com username {row['username']} teve alteração no cadastro, refazendo apropriações"
            )
            deactivate_future_appropriations_user(row["username"])
            appropriations_customer(row["username"])

    def disabled_users(self):
        df_users_valeflow_disabled = valeflow.get_sql(
            SQL_USERS_VALEFLOW_DISABLED
        )  # Atualizar os ususarios do valeflow após inserção para procurar os desabilitados

        df_users_sga_disabled = sga.get_sql(
            SQL_USERS_SGA_DISABLED
        )  # Buscar funcionarios demitidos
        df_users_sga_disabled["username"] = (
            df_users_sga_disabled["username"]
            .str.replace(".", "")
            .str.replace("/", "")
            .str.replace("-", "")
        )  # Limpar username removendo caracteres especiais
        df_users_sga_disabled["username"] = df_users_sga_disabled[
            "username"
        ].str.replace(" ", "", regex=False)  # retirar espaços em branco
        df_users_sga_disabled = df_users_sga_disabled.drop_duplicates(
            subset="username", keep="last"
        )

        df_merged = pandas.merge(
            df_users_sga_disabled,
            df_users_valeflow_disabled,
            on="username",
            how="inner",
            suffixes=("_sga", "_valeflow"),
        )  # Unir os DataFrames do SGA e valeflow com base no username

        df_alterados = df_merged.copy()

        df_alterados = df_alterados.fillna(
            0
        )  # definir NaNs como 0 para facilitar a comparação

        df_alterados = df_alterados[
            ~(df_alterados["is_active_sga"] == df_alterados["is_active_valeflow"])
        ]  # Comparando a coluna is_active para atualizar os demitidos

        df_alterados = df_alterados.drop(
            columns=[
                "nome_completo_valeflow",
                "UNIDADE_valeflow",
                "cargo_valeflow",
                "Departamento_valeflow",
                "is_active_valeflow",
                "cargo_sga",
                "Departamento_sga",
                "UNIDADE_sga",
                "nome_completo_sga",
            ]
        )  # Retirar colunas do valeflow
        df_alterados.rename(
            columns=lambda x: x.replace("_sga", ""), inplace=True
        )  # Renomear colunas do SGA para o padrão do valeflow

        valeflow.update_from_df(
            df_alterados, "custom_user", ["username"]
        )  # Desativar usuários

        # Diarizando as tarefas dos novos funcionarios
        for index, row in df_alterados.iterrows():
            logger.info(
                f"Funcionário com username {row['username']} foi desativado, desfazendo apropriações"
            )
            deactivate_future_appropriations_user(row["username"])


sga = Sga()
valeflow = Valeflow()
integration = Integration()

# integration.new_department() # Executar a integração para criar novos departamentos
# integration.new_position() # Executar a integração para criar novos cargos

# integration.new_users() # Executar a integração para criar novos usuários
# integration.update_users()
# integration.disabled_users()
