# src/integrations/plaid/client.py
"""
Plaid API Client

Low-level client for Plaid Investment API.
Handles authentication, rate limiting, and error handling.

Privacy: Access tokens encrypted before storage.
Audit: All API calls logged for compliance.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.investments_transactions_get_request import InvestmentsTransactionsGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode

logger = logging.getLogger(__name__)


class PlaidClient:
    """
    Plaid API client for investment data.

    Usage:
        client = PlaidClient()

        # Get Link token for frontend
        link_token = client.create_link_token(user_id="user123")

        # Exchange public token for access token
        access_token, item_id = client.exchange_public_token(public_token)

        # Fetch investment data
        holdings = client.get_investment_holdings(access_token)
        transactions = client.get_investment_transactions(access_token, start_date, end_date)
    """

    def __init__(self):
        """Initialize Plaid client with credentials from environment."""
        self.client_id = os.getenv("PLAID_CLIENT_ID")
        self.secret = os.getenv("PLAID_SECRET")
        self.environment = os.getenv("PLAID_ENV", "sandbox")

        if not self.client_id or not self.secret:
            raise ValueError(
                "PLAID_CLIENT_ID and PLAID_SECRET must be set in environment. "
                "Get credentials from https://dashboard.plaid.com"
            )

        # Configure Plaid client
        configuration = plaid.Configuration(
            host=self._get_host(),
            api_key={
                "clientId": self.client_id,
                "secret": self.secret,
            }
        )

        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

        logger.info(f"PlaidClient initialized (env: {self.environment})")

    def _get_host(self) -> str:
        """Get Plaid API host based on environment."""
        hosts = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Sandbox,  # Dev uses sandbox endpoint
            "production": plaid.Environment.Production,
        }
        return hosts.get(self.environment, plaid.Environment.Sandbox)

    def create_link_token(
        self,
        user_id: str,
        products: List[str] = None,
        redirect_uri: str = None,
    ) -> Dict[str, Any]:
        """
        Create a Link token for the Plaid Link flow.

        Args:
            user_id: Unique identifier for the user
            products: List of products to request (default: investments, transactions)
            redirect_uri: OAuth redirect URI (required for OAuth institutions)

        Returns:
            Dict with link_token and expiration
        """
        if products is None:
            products = ["investments", "transactions"]

        product_enums = [Products(p) for p in products]

        request = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id=user_id),
            client_name="ACMS Financial",
            products=product_enums,
            country_codes=[CountryCode("US")],
            language="en",
        )

        if redirect_uri:
            request.redirect_uri = redirect_uri

        try:
            response = self.client.link_token_create(request)

            logger.info(f"Link token created for user {user_id}")

            return {
                "link_token": response.link_token,
                "expiration": response.expiration,
                "request_id": response.request_id,
            }
        except plaid.ApiException as e:
            logger.error(f"Failed to create link token: {e}")
            raise

    def exchange_public_token(self, public_token: str) -> tuple[str, str]:
        """
        Exchange public token from Link for access token.

        SECURITY: Access token must be encrypted immediately after this call.
        Never log the access token in plain text.

        Args:
            public_token: Public token from Plaid Link success callback

        Returns:
            Tuple of (access_token, item_id)
        """
        request = ItemPublicTokenExchangeRequest(public_token=public_token)

        try:
            response = self.client.item_public_token_exchange(request)

            # Log without exposing token
            logger.info(f"Public token exchanged, item_id: {response.item_id}")

            return response.access_token, response.item_id
        except plaid.ApiException as e:
            logger.error(f"Failed to exchange public token: {e}")
            raise

    def get_item(self, access_token: str) -> Dict[str, Any]:
        """Get Item metadata (institution info, status)."""
        request = ItemGetRequest(access_token=access_token)

        try:
            response = self.client.item_get(request)

            return {
                "item_id": response.item.item_id,
                "institution_id": response.item.institution_id,
                "consent_expiration": response.item.consent_expiration_time,
                "error": response.item.error,
                "available_products": [str(p) for p in response.item.available_products],
                "billed_products": [str(p) for p in response.item.billed_products],
            }
        except plaid.ApiException as e:
            logger.error(f"Failed to get item: {e}")
            raise

    def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get all accounts for an Item."""
        request = AccountsGetRequest(access_token=access_token)

        try:
            response = self.client.accounts_get(request)

            accounts = []
            for account in response.accounts:
                accounts.append({
                    "account_id": account.account_id,
                    "name": account.name,
                    "official_name": account.official_name,
                    "type": str(account.type),
                    "subtype": str(account.subtype) if account.subtype else None,
                    "mask": account.mask,
                    "balances": {
                        "current": account.balances.current,
                        "available": account.balances.available,
                        "limit": account.balances.limit,
                        "currency": account.balances.iso_currency_code,
                    },
                })

            logger.info(f"Retrieved {len(accounts)} accounts")
            return accounts
        except plaid.ApiException as e:
            logger.error(f"Failed to get accounts: {e}")
            raise

    def get_investment_holdings(self, access_token: str) -> Dict[str, Any]:
        """
        Get investment holdings for all accounts.

        Returns holdings, securities, and accounts data.
        """
        request = InvestmentsHoldingsGetRequest(access_token=access_token)

        try:
            response = self.client.investments_holdings_get(request)

            # Process holdings
            holdings = []
            for h in response.holdings:
                holdings.append({
                    "account_id": h.account_id,
                    "security_id": h.security_id,
                    "quantity": float(h.quantity),
                    "institution_price": float(h.institution_price),
                    "institution_value": float(h.institution_value),
                    "cost_basis": float(h.cost_basis) if h.cost_basis else None,
                    "institution_price_as_of": h.institution_price_as_of,
                    "currency": h.iso_currency_code,
                })

            # Process securities
            securities = []
            for s in response.securities:
                securities.append({
                    "security_id": s.security_id,
                    "ticker_symbol": s.ticker_symbol,
                    "name": s.name,
                    "type": str(s.type) if s.type else None,
                    "cusip": s.cusip,
                    "isin": s.isin,
                    "sedol": s.sedol,
                    "close_price": float(s.close_price) if s.close_price else None,
                    "close_price_as_of": s.close_price_as_of,
                    "is_cash_equivalent": s.is_cash_equivalent,
                    "currency": s.iso_currency_code,
                })

            # Process accounts
            accounts = []
            for a in response.accounts:
                accounts.append({
                    "account_id": a.account_id,
                    "name": a.name,
                    "type": str(a.type),
                    "subtype": str(a.subtype) if a.subtype else None,
                    "mask": a.mask,
                })

            logger.info(
                f"Retrieved {len(holdings)} holdings, "
                f"{len(securities)} securities, "
                f"{len(accounts)} accounts"
            )

            return {
                "holdings": holdings,
                "securities": securities,
                "accounts": accounts,
                "request_id": response.request_id,
            }
        except plaid.ApiException as e:
            logger.error(f"Failed to get investment holdings: {e}")
            raise

    def get_investment_transactions(
        self,
        access_token: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Get investment transactions for date range.

        Args:
            access_token: Plaid access token
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dict with transactions, securities, and accounts
        """
        from datetime import date

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        request = InvestmentsTransactionsGetRequest(
            access_token=access_token,
            start_date=start,
            end_date=end,
        )

        try:
            response = self.client.investments_transactions_get(request)

            # Process transactions
            transactions = []
            for t in response.investment_transactions:
                transactions.append({
                    "investment_transaction_id": t.investment_transaction_id,
                    "account_id": t.account_id,
                    "security_id": t.security_id,
                    "date": t.date.isoformat() if t.date else None,
                    "name": t.name,
                    "type": str(t.type) if t.type else None,
                    "subtype": str(t.subtype) if t.subtype else None,
                    "quantity": float(t.quantity) if t.quantity else None,
                    "amount": float(t.amount),
                    "price": float(t.price) if t.price else None,
                    "fees": float(t.fees) if t.fees else None,
                    "currency": t.iso_currency_code,
                })

            # Process securities (same as holdings)
            securities = []
            for s in response.securities:
                securities.append({
                    "security_id": s.security_id,
                    "ticker_symbol": s.ticker_symbol,
                    "name": s.name,
                    "type": str(s.type) if s.type else None,
                    "cusip": s.cusip,
                    "isin": s.isin,
                    "close_price": float(s.close_price) if s.close_price else None,
                })

            logger.info(f"Retrieved {len(transactions)} investment transactions")

            return {
                "transactions": transactions,
                "securities": securities,
                "total_transactions": response.total_investment_transactions,
                "request_id": response.request_id,
            }
        except plaid.ApiException as e:
            logger.error(f"Failed to get investment transactions: {e}")
            raise

    def remove_item(self, access_token: str) -> bool:
        """
        Remove an Item (disconnect the account).

        This revokes the access token and removes ACMS's access to the account.
        """
        request = ItemRemoveRequest(access_token=access_token)

        try:
            self.client.item_remove(request)
            logger.info("Item removed successfully")
            return True
        except plaid.ApiException as e:
            logger.error(f"Failed to remove item: {e}")
            raise
