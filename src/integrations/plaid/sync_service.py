# src/integrations/plaid/sync_service.py
"""
Plaid Sync Service

Fetches investment data from Plaid and stores in canonical tables.
Handles securities master deduplication, position snapshots, and transactions.

Privacy: Dollar amounts encrypted before storage.
Audit: All sync operations logged.
"""

import os
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class PlaidSyncService:
    """
    Syncs Plaid investment data to ACMS canonical tables.

    Handles:
    - Securities master deduplication (by CUSIP/ISIN/ticker)
    - Position snapshots (daily)
    - Transaction normalization
    - Tag seeding from security_seed_data
    """

    def __init__(self, db_pool=None):
        """Initialize sync service."""
        self.db_pool = db_pool

        # Initialize encryption for dollar amounts
        encryption_key = os.getenv("PLAID_ENCRYPTION_KEY")
        if encryption_key:
            self.cipher = Fernet(
                encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
            )
        else:
            logger.warning("PLAID_ENCRYPTION_KEY not set - using temporary key")
            self.cipher = Fernet(Fernet.generate_key())

        # Initialize OAuth handler
        from .oauth import PlaidOAuth
        self.oauth = PlaidOAuth(db_pool)

        # Initialize Plaid client
        from .client import PlaidClient
        self.plaid = PlaidClient()

        logger.info("PlaidSyncService initialized")

    def _encrypt(self, value: float) -> str:
        """Encrypt a dollar amount."""
        return self.cipher.encrypt(str(value).encode()).decode()

    def _decrypt(self, encrypted: str) -> float:
        """Decrypt a dollar amount."""
        return float(self.cipher.decrypt(encrypted.encode()).decode())

    def _parse_date(self, date_value) -> Optional[date]:
        """Convert date string or datetime to date object for asyncpg."""
        if date_value is None:
            return None
        if isinstance(date_value, date):
            return date_value
        if isinstance(date_value, datetime):
            return date_value.date()
        if isinstance(date_value, str):
            try:
                return date.fromisoformat(date_value)
            except ValueError:
                logger.warning(f"Could not parse date: {date_value}")
                return None
        return None

    async def sync_item(self, item_id: str) -> Dict[str, Any]:
        """
        Sync all data for a Plaid Item.

        Args:
            item_id: Plaid Item ID

        Returns:
            Sync summary with counts
        """
        logger.info(f"Starting sync for item {item_id}")

        # Get access token
        access_token = await self.oauth.get_access_token(item_id)
        if not access_token:
            raise ValueError(f"No access token for item {item_id}")

        # Sync holdings (includes securities and accounts)
        holdings_result = await self.sync_holdings(access_token, item_id)

        # Sync transactions (last 90 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        transactions_result = await self.sync_transactions(
            access_token, item_id,
            start_date.isoformat(), end_date.isoformat()
        )

        # Update last sync time
        await self._update_sync_status(item_id, success=True)

        return {
            "item_id": item_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "securities": holdings_result["securities_synced"],
            "accounts": holdings_result["accounts_synced"],
            "positions": holdings_result["positions_synced"],
            "transactions": transactions_result["transactions_synced"],
        }

    async def sync_holdings(
        self,
        access_token: str,
        item_id: str,
    ) -> Dict[str, Any]:
        """
        Sync investment holdings from Plaid.

        Args:
            access_token: Decrypted Plaid access token
            item_id: Plaid Item ID

        Returns:
            Sync counts
        """
        # Fetch from Plaid
        data = self.plaid.get_investment_holdings(access_token)

        securities_synced = 0
        accounts_synced = 0
        positions_synced = 0

        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            # 1. Sync securities to securities_master
            security_id_map = {}  # plaid_security_id -> internal UUID

            for security in data["securities"]:
                internal_id = await self._upsert_security(conn, security)
                security_id_map[security["security_id"]] = internal_id
                securities_synced += 1

            # 2. Sync accounts to financial_accounts
            account_id_map = {}  # plaid_account_id -> internal UUID

            for account in data["accounts"]:
                internal_id = await self._upsert_account(conn, account, item_id)
                account_id_map[account["account_id"]] = internal_id
                accounts_synced += 1

            # 3. Sync positions to positions_daily
            # Aggregate holdings by (account, security) to handle multiple lots
            snapshot_date = date.today()
            aggregated_holdings = {}

            for holding in data["holdings"]:
                account_id = account_id_map.get(holding["account_id"])
                security_id = security_id_map.get(holding["security_id"])

                if not account_id or not security_id:
                    continue

                key = (account_id, security_id)

                if key not in aggregated_holdings:
                    aggregated_holdings[key] = {
                        "quantity": 0,
                        "institution_value": 0,
                        "cost_basis": 0,
                        "institution_price": holding.get("institution_price"),
                    }

                aggregated_holdings[key]["quantity"] += holding.get("quantity", 0)
                aggregated_holdings[key]["institution_value"] += holding.get("institution_value", 0)
                if holding.get("cost_basis"):
                    aggregated_holdings[key]["cost_basis"] += holding["cost_basis"]

            # Now insert aggregated positions
            for (account_id, security_id), agg in aggregated_holdings.items():
                await self._upsert_position(
                    conn, agg,
                    account_id,
                    security_id,
                    snapshot_date,
                )
                positions_synced += 1

        logger.info(
            f"Synced {securities_synced} securities, "
            f"{accounts_synced} accounts, "
            f"{positions_synced} positions"
        )

        return {
            "securities_synced": securities_synced,
            "accounts_synced": accounts_synced,
            "positions_synced": positions_synced,
        }

    async def sync_transactions(
        self,
        access_token: str,
        item_id: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Sync investment transactions from Plaid.

        Args:
            access_token: Decrypted Plaid access token
            item_id: Plaid Item ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Sync counts
        """
        # Fetch from Plaid
        data = self.plaid.get_investment_transactions(
            access_token, start_date, end_date
        )

        transactions_synced = 0

        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            # Get security and account ID maps
            security_id_map = await self._get_security_id_map(conn)
            account_id_map = await self._get_account_id_map(conn, item_id)

            # Also sync any new securities from transactions
            for security in data.get("securities", []):
                if security["security_id"] not in security_id_map:
                    internal_id = await self._upsert_security(conn, security)
                    security_id_map[security["security_id"]] = internal_id

            # Sync transactions
            for txn in data["transactions"]:
                await self._upsert_transaction(
                    conn, txn,
                    account_id_map.get(txn["account_id"]),
                    security_id_map.get(txn["security_id"]),
                )
                transactions_synced += 1

        logger.info(f"Synced {transactions_synced} transactions")

        return {
            "transactions_synced": transactions_synced,
            "total_available": data.get("total_transactions", transactions_synced),
        }

    async def _upsert_security(
        self,
        conn,
        security: Dict[str, Any],
    ) -> UUID:
        """
        Insert or update a security in securities_master.

        Deduplicates by CUSIP > ISIN > Plaid ID.
        Also applies seed tags if available.
        """
        # Try to find existing by CUSIP, ISIN, or Plaid ID
        existing = None

        if security.get("cusip"):
            existing = await conn.fetchrow(
                "SELECT id FROM securities_master WHERE cusip = $1",
                security["cusip"]
            )
        if not existing and security.get("isin"):
            existing = await conn.fetchrow(
                "SELECT id FROM securities_master WHERE isin = $1",
                security["isin"]
            )
        if not existing and security.get("security_id"):
            existing = await conn.fetchrow(
                "SELECT id FROM securities_master WHERE plaid_security_id = $1",
                security["security_id"]
            )

        # Map Plaid security type to our enum
        security_type = self._map_security_type(security.get("type"))

        if existing:
            # Update existing record
            await conn.execute("""
                UPDATE securities_master SET
                    plaid_security_id = COALESCE($2, plaid_security_id),
                    name = COALESCE($3, name),
                    last_close_price = COALESCE($4, last_close_price),
                    last_close_date = COALESCE($5, last_close_date),
                    updated_at = NOW()
                WHERE id = $1
            """,
                existing["id"],
                security.get("security_id"),
                security.get("name"),
                security.get("close_price"),
                self._parse_date(security.get("close_price_as_of")),
            )
            security_id = existing["id"]
        else:
            # Insert new record
            row = await conn.fetchrow("""
                INSERT INTO securities_master (
                    ticker, cusip, isin, sedol, plaid_security_id,
                    name, security_type, is_cash_equivalent,
                    last_close_price, last_close_date, currency
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """,
                security.get("ticker_symbol"),
                security.get("cusip"),
                security.get("isin"),
                security.get("sedol"),
                security.get("security_id"),
                security.get("name", "Unknown Security"),
                security_type,
                security.get("is_cash_equivalent", False),
                security.get("close_price"),
                self._parse_date(security.get("close_price_as_of")),
                security.get("currency", "USD"),
            )
            security_id = row["id"]

            # Apply seed tags if available
            await self._apply_seed_tags(conn, security_id, security.get("ticker_symbol"))

        return security_id

    def _map_security_type(self, plaid_type: Optional[str]) -> str:
        """Map Plaid security type to our enum."""
        if not plaid_type:
            return "other"

        type_map = {
            "equity": "equity",
            "etf": "etf",
            "mutual fund": "mutual_fund",
            "fixed income": "bond",
            "cash": "cash",
            "cryptocurrency": "cryptocurrency",
            "derivative": "option",
        }
        return type_map.get(plaid_type.lower(), "other")

    async def _apply_seed_tags(
        self,
        conn,
        security_id: UUID,
        ticker: Optional[str],
    ):
        """Apply tags from security_seed_data if available."""
        if not ticker:
            return

        seed = await conn.fetchrow("""
            SELECT tags, sector, sub_theme
            FROM security_seed_data
            WHERE ticker = $1
        """, ticker)

        if not seed:
            return

        # Apply sector
        if seed["sector"]:
            await conn.execute("""
                UPDATE securities_master SET sector = $2 WHERE id = $1
            """, security_id, seed["sector"])

        # Apply tags
        for tag in seed["tags"] or []:
            await conn.execute("""
                INSERT INTO security_tags (security_id, tag, source, sub_theme, confidence)
                VALUES ($1, $2, 'seed', $3, 1.0)
                ON CONFLICT (security_id, tag, source) DO NOTHING
            """, security_id, tag, seed["sub_theme"])

        logger.debug(f"Applied seed tags to {ticker}: {seed['tags']}")

    async def _upsert_account(
        self,
        conn,
        account: Dict[str, Any],
        item_id: str,
    ) -> UUID:
        """Insert or update a financial account."""
        existing = await conn.fetchrow(
            "SELECT id FROM financial_accounts WHERE plaid_account_id = $1",
            account["account_id"]
        )

        if existing:
            await conn.execute("""
                UPDATE financial_accounts SET
                    account_name = $2,
                    updated_at = NOW()
                WHERE id = $1
            """, existing["id"], account.get("name", "Account"))
            return existing["id"]
        else:
            row = await conn.fetchrow("""
                INSERT INTO financial_accounts (
                    plaid_account_id, plaid_item_id, account_name,
                    account_type, account_subtype, last_synced_at
                ) VALUES ($1, $2, $3, $4, $5, NOW())
                RETURNING id
            """,
                account["account_id"],
                item_id,
                account.get("name", "Account"),
                account.get("type", "investment"),
                account.get("subtype"),
            )
            return row["id"]

    async def _upsert_position(
        self,
        conn,
        holding: Dict[str, Any],
        account_id: Optional[UUID],
        security_id: Optional[UUID],
        snapshot_date: date,
    ):
        """Insert or update a position snapshot."""
        if not account_id or not security_id:
            logger.warning(f"Missing account or security ID for holding")
            return

        # Encrypt dollar amounts
        market_value_encrypted = self._encrypt(holding["institution_value"])
        cost_basis_encrypted = (
            self._encrypt(holding["cost_basis"])
            if holding.get("cost_basis")
            else None
        )

        await conn.execute("""
            INSERT INTO positions_daily (
                account_id, security_id, snapshot_date,
                quantity, market_value_encrypted, cost_basis_encrypted,
                price_per_share
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (account_id, security_id, snapshot_date)
            DO UPDATE SET
                quantity = EXCLUDED.quantity,
                market_value_encrypted = EXCLUDED.market_value_encrypted,
                cost_basis_encrypted = EXCLUDED.cost_basis_encrypted,
                price_per_share = EXCLUDED.price_per_share
        """,
            account_id,
            security_id,
            snapshot_date,
            holding["quantity"],
            market_value_encrypted,
            cost_basis_encrypted,
            holding.get("institution_price"),
        )

    async def _upsert_transaction(
        self,
        conn,
        txn: Dict[str, Any],
        account_id: Optional[UUID],
        security_id: Optional[UUID],
    ):
        """Insert a financial transaction."""
        if not account_id:
            logger.warning(f"Missing account ID for transaction")
            return

        # Map Plaid transaction type to our enum
        txn_type = self._map_transaction_type(txn.get("type"), txn.get("subtype"))

        # Encrypt amounts
        amount_encrypted = self._encrypt(txn["amount"])
        price_encrypted = self._encrypt(txn["price"]) if txn.get("price") else None
        fees_encrypted = self._encrypt(txn["fees"]) if txn.get("fees") else None

        await conn.execute("""
            INSERT INTO financial_transactions (
                account_id, security_id, plaid_transaction_id,
                transaction_type, transaction_date,
                quantity, amount_encrypted, price_encrypted, fees_encrypted,
                description, plaid_subtype
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (plaid_transaction_id) DO NOTHING
        """,
            account_id,
            security_id,
            txn["investment_transaction_id"],
            txn_type,
            self._parse_date(txn.get("date")),
            txn.get("quantity"),
            amount_encrypted,
            price_encrypted,
            fees_encrypted,
            txn.get("name"),
            txn.get("subtype"),
        )

    def _map_transaction_type(
        self,
        plaid_type: Optional[str],
        plaid_subtype: Optional[str],
    ) -> str:
        """Map Plaid transaction type to our enum."""
        if not plaid_type:
            return "other"

        # Plaid uses type + subtype system
        type_map = {
            "buy": "buy",
            "sell": "sell",
            "dividend": "dividend",
            "cash": "dividend" if plaid_subtype == "dividend" else "interest",
            "transfer": "transfer_in",
            "fee": "fee",
        }
        return type_map.get(plaid_type.lower(), "other")

    async def _get_security_id_map(self, conn) -> Dict[str, UUID]:
        """Get mapping of Plaid security IDs to internal UUIDs."""
        rows = await conn.fetch("""
            SELECT plaid_security_id, id FROM securities_master
            WHERE plaid_security_id IS NOT NULL
        """)
        return {row["plaid_security_id"]: row["id"] for row in rows}

    async def _get_account_id_map(self, conn, item_id: str) -> Dict[str, UUID]:
        """Get mapping of Plaid account IDs to internal UUIDs for an item."""
        rows = await conn.fetch("""
            SELECT plaid_account_id, id FROM financial_accounts
            WHERE plaid_item_id = $1
        """, item_id)
        return {row["plaid_account_id"]: row["id"] for row in rows}

    async def _update_sync_status(self, item_id: str, success: bool):
        """Update sync status for an item."""
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            if success:
                await conn.execute("""
                    UPDATE plaid_tokens SET
                        last_successful_sync = NOW(),
                        consecutive_failures = 0,
                        error_code = NULL,
                        error_message = NULL,
                        updated_at = NOW()
                    WHERE item_id = $1
                """, item_id)
            else:
                await conn.execute("""
                    UPDATE plaid_tokens SET
                        consecutive_failures = consecutive_failures + 1,
                        updated_at = NOW()
                    WHERE item_id = $1
                """, item_id)
