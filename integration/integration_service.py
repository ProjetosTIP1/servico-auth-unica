import polars as pl
import polars.selectors as cs
from core.ports.service import IIntegrationService
from core.ports.repository import ISgaRepository, ISamIntegrationRepository
from core.helpers.logger_helper import logger
from core.helpers.authentication_helper import get_password_hash


class IntegrationService(IIntegrationService):
    """
    Orchestrates the synchronization between SGA and SAM using Polars for high performance.
    """

    def __init__(self, sga_repo: ISgaRepository, sam_repo: ISamIntegrationRepository):
        self.sga_repo: ISgaRepository = sga_repo
        self.sam_repo: ISamIntegrationRepository = sam_repo

    async def sync_all(self, dry_run: bool = False) -> dict[str, int]:
        logger.info("Starting full synchronization...")
        # await self.sync_metadata(dry_run) # Optional metadata sync
        result = await self.sync_users(dry_run)
        logger.info("Full synchronization completed.")
        return result

    async def sync_users(self, dry_run: bool = False) -> dict[str, int]:
        logger.info("Starting user synchronization...")

        # 1. Extraction (E)
        sga_users_df = self.sga_repo.get_users_df()
        logger.debug(f"Found {sga_users_df.height} users in SGA.")
        sam_users_df = self.sam_repo.get_current_users_df()
        logger.debug(f"Found {sam_users_df.height} users in SAM.")

        # Defensive casting: ensure comparison columns and join key are strings
        # This prevents type mismatch errors when one of the DataFrames is empty (producing Null types)
        sync_cols = ["username", "nome_completo", "cargo", "departamento", "unidade"]

        def normalize_df(df: pl.DataFrame) -> pl.DataFrame:
            # Only cast if columns exist to avoid errors with completely empty DFs
            existing = [c for c in sync_cols if c in df.columns]
            if not existing:
                return df
            return df.with_columns(
                [pl.col(c).cast(pl.String).fill_null("") for c in existing]
            )

        sga_users_df = normalize_df(sga_users_df)
        sam_users_df = normalize_df(sam_users_df)

        # 2. Transformation (T)
        if not sga_users_df.is_empty():
            # Clean usernames: remove . / - and spaces, then deduplicate
            sga_users_df = sga_users_df.with_columns(
                pl.col("username")
                .str.replace_all(r"[\./-]", "")
                .str.strip_chars()
                .alias("username")
            ).unique(subset=["username"], keep="last")

            # Join to find new users vs updates
            # New users: in SGA but NOT in SAM
            new_users_df = sga_users_df.join(sam_users_df, on="username", how="anti")

            # Updates: in both SGA and SAM, but with differences
            common_users_df = sga_users_df.join(
                sam_users_df, on="username", how="inner", suffix="_sam"
            )

            # Filter changed users: compare relevant fields
            changed_users_df = common_users_df.filter(
                (pl.col("nome_completo") != pl.col("nome_completo_sam"))
                | (pl.col("cargo") != pl.col("cargo_sam"))
                | (pl.col("departamento") != pl.col("departamento_sam"))
                | (pl.col("unidade") != pl.col("unidade_sam"))
            )

            # Process new users: generate password, cpf_cnpj and split name
            if not new_users_df.is_empty():
                logger.info(f"Detected {new_users_df.height} new users.")
                # Map default password: first 6 chars of username + @@ (legacy pattern)
                # Set first_name and last_name from nome_completo
                new_users_df = new_users_df.with_columns(
                    pl.col("username")
                    .str.slice(0, 6)
                    .map_elements(
                        lambda x: get_password_hash(f"{x}@@"), return_dtype=pl.String
                    )
                    .alias("password"),
                    pl.col("nome_completo")
                    .str.split(" ")
                    .map_elements(lambda x: x[0], return_dtype=pl.String)
                    .alias("first_name"),
                    pl.col("nome_completo")
                    .str.split(" ")
                    .map_elements(lambda x: " ".join(x[1:]), return_dtype=pl.String)
                    .alias("last_name"),
                    pl.col("username")
                    .str.replace_all(r"[\./-]", "")
                    .str.strip_chars()
                    .alias("cpf_cnpj"),
                )
        else:
            logger.warning(
                "No users found in SGA. Proceeding to check for disabled users."
            )
            new_users_df = pl.DataFrame()
            changed_users_df = pl.DataFrame()

        # Process disabled users (D)
        disabled_sga_df = self.sga_repo.get_disabled_users_df()
        if not disabled_sga_df.is_empty():
            disabled_sga_df = disabled_sga_df.with_columns(
                pl.col("username")
                .str.replace_all(r"[\./-]", "")
                .str.strip_chars()
                .alias("username")
            )
            # Only disable those who are currently active in SAM
            active_sam_usernames = sam_users_df.filter(pl.col("is_active") == 1).select(
                "username"
            )
            to_disable_df = disabled_sga_df.join(
                active_sam_usernames, on="username", how="inner"
            )
            logger.info(f"Detected {to_disable_df.height} users to disable.")
        else:
            to_disable_df = pl.DataFrame()

        # 3. Loading (L)
        if dry_run:
            logger.info("[Dry Run] User sync would process:")
            logger.info(f"- New: {new_users_df.height}")
            logger.info(f"- Changed: {changed_users_df.height}")
            logger.info(f"- Disabled: {to_disable_df.height}")
            return {
                "new": new_users_df.height,
                "changed": changed_users_df.height,
                "disabled": to_disable_df.height,
            }

        # Perform Upserts
        upsert_count = 0
        if not new_users_df.is_empty():
            upsert_count += self.sam_repo.upsert_users(new_users_df)

        if not changed_users_df.is_empty():
            # For updates, we can reuse the same upsert_users method as it uses ON DUPLICATE KEY UPDATE
            upsert_count += self.sam_repo.upsert_users(
                changed_users_df.drop(cs.ends_with("_sam"))
            )

        disabled_count = 0
        if not to_disable_df.is_empty():
            disabled_count = self.sam_repo.disable_users(
                to_disable_df["username"].to_list()
            )

        logger.info(
            f"User sync finished. Upserted: {upsert_count}, Disabled: {disabled_count}"
        )
        return {
            "upserted": upsert_count,
            "disabled": disabled_count,
        }

    async def sync_metadata(self, dry_run: bool = False):
        logger.info("Starting metadata synchronization (Departments & Positions)...")

        # This assumes SAM wants to keep separate tables for these.
        # If the schema doesn't have them, these will fail or return empty DFs.

        # Sync Departments
        sga_depts = self.sga_repo.get_departments_df()
        if not sga_depts.is_empty():
            if not dry_run:
                count = self.sam_repo.upsert_departments(sga_depts)
                logger.info(f"Upserted {count} departments.")

        # Sync Positions
        sga_positions = self.sga_repo.get_positions_df()
        if not sga_positions.is_empty():
            if not dry_run:
                count = self.sam_repo.upsert_positions(sga_positions)
                logger.info(f"Upserted {count} positions.")

        logger.info("Metadata synchronization completed.")
