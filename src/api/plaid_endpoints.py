# src/api/plaid_endpoints.py
"""
Plaid REST API Endpoints for Desktop UI

Provides endpoints for:
- OAuth2 flow (Link token, exchange, status, disconnect)
- Account syncing (holdings, transactions)
- Connection status monitoring

Privacy: Dollar amounts encrypted at rest.
LLM Boundary: Financial data NEVER sent to external LLMs.
"""

import logging
from typing import Optional, List
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plaid", tags=["plaid"])


# ==========================================
# RESPONSE MODELS
# ==========================================

class PlaidConnectionStatus(BaseModel):
    """Plaid connection status."""
    connected: bool
    active_connections: int = 0
    institutions: List[dict] = []
    message: Optional[str] = None
    environment: Optional[str] = None  # sandbox, development, production


class LinkTokenResponse(BaseModel):
    """Plaid Link token for frontend."""
    link_token: str
    expiration: str
    request_id: str


class ItemInfo(BaseModel):
    """Connected Plaid Item info."""
    item_id: str
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    products: List[str] = []


class SyncResult(BaseModel):
    """Sync operation result."""
    success: bool
    item_id: str
    synced_at: str
    securities: int
    accounts: int
    positions: int
    transactions: int


# ==========================================
# OAUTH ENDPOINTS
# ==========================================

@router.get("/oauth-callback")
async def oauth_callback(
    request: Request,
    oauth_state_id: Optional[str] = Query(None, description="Plaid OAuth state ID"),
):
    """
    OAuth callback endpoint for Plaid Link.

    When using OAuth institutions (Fidelity, Wells Fargo, etc.) in production,
    Plaid redirects here after the user authenticates with their bank.

    The Electron app should handle this redirect and resume Plaid Link
    using the oauth_state_id parameter.

    This endpoint is configured in Plaid Dashboard > Team Settings > Allowed redirect URIs
    """
    logger.info(f"OAuth callback received with state_id: {oauth_state_id}")

    # Return an HTML page that tells the Electron app to resume Plaid Link
    # The Electron app can intercept this or the user can be redirected
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ACMS - Connecting Account</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: #1e1e1e;
                color: #fff;
            }}
            .container {{
                text-align: center;
                padding: 40px;
            }}
            h1 {{ color: #4CAF50; }}
            p {{ color: #ccc; }}
            .state-id {{
                font-family: monospace;
                background: #333;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }}
        </style>
        <script>
            // Try to close the window and return to the app
            // The Electron app should intercept this URL
            window.onload = function() {{
                // If this is a popup, close it and signal the parent
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'plaid-oauth-callback',
                        oauth_state_id: '{oauth_state_id or ""}'
                    }}, '*');
                    window.close();
                }}
            }};
        </script>
    </head>
    <body>
        <div class="container">
            <h1>Account Connected!</h1>
            <p>Return to the ACMS app to complete the connection.</p>
            <p class="state-id">OAuth State: {oauth_state_id or 'N/A'}</p>
        </div>
    </body>
    </html>
    """

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)


@router.get("/status", response_model=PlaidConnectionStatus)
async def get_connection_status(request: Request, user_id: str = "default"):
    """
    Check Plaid connection status.

    Returns list of connected institutions and their sync status.
    """
    import os
    plaid_env = os.getenv("PLAID_ENV", "sandbox")

    try:
        from src.integrations.plaid import PlaidOAuth

        db_pool = request.app.state.db_pool
        oauth = PlaidOAuth(db_pool=db_pool)

        status = await oauth.get_connection_status(user_id)
        status["environment"] = plaid_env

        return PlaidConnectionStatus(**status)

    except Exception as e:
        logger.warning(f"Failed to check Plaid status: {e}")
        return PlaidConnectionStatus(
            connected=False,
            message="Unable to check connection status",
            environment=plaid_env
        )


@router.get("/link-token", response_model=LinkTokenResponse)
async def create_link_token(
    request: Request,
    user_id: str = Query("default", description="User identifier"),
):
    """
    Create a Plaid Link token for frontend.

    The frontend uses this token to initiate the Plaid Link flow
    where users select and authenticate with their financial institution.

    NOTE: For OAuth institutions (Fidelity, Wells Fargo, etc.) in production,
    we pass a redirect_uri that must be configured in Plaid Dashboard.
    """
    import os

    try:
        from src.integrations.plaid import PlaidOAuth

        db_pool = request.app.state.db_pool
        oauth = PlaidOAuth(db_pool=db_pool)

        # OAuth redirect URI for OAuth-based institutions (Fidelity, Wells Fargo, Chase)
        # Using Vercel-hosted HTTPS callback page
        plaid_env = os.getenv("PLAID_ENV", "sandbox")
        redirect_uri = None

        if plaid_env == "production":
            # Vercel-hosted OAuth callback (HTTPS required for production)
            redirect_uri = "https://vercel-oauth-handler-sage.vercel.app/oauth-callback"
            logger.info(f"Using OAuth redirect_uri: {redirect_uri}")

        result = await oauth.create_link_token(
            user_id=user_id,
            products=["investments", "transactions"],
            redirect_uri=redirect_uri,
        )

        return LinkTokenResponse(
            link_token=result["link_token"],
            expiration=str(result["expiration"]),
            request_id=result["request_id"],
        )

    except Exception as e:
        logger.error(f"Failed to create Link token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExchangeRequest(BaseModel):
    """Request body for token exchange."""
    public_token: str
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    user_id: str = "default"


@router.post("/exchange", response_model=ItemInfo)
async def exchange_public_token(
    request: Request,
    body: ExchangeRequest,
):
    """
    Exchange public token for access token.

    Called after user completes Plaid Link flow.
    Access token is encrypted immediately before storage.

    SECURITY: Access token NEVER logged in plain text.
    """
    try:
        from src.integrations.plaid import PlaidOAuth

        db_pool = request.app.state.db_pool
        oauth = PlaidOAuth(db_pool=db_pool)

        result = await oauth.handle_link_success(
            public_token=body.public_token,
            institution_name=body.institution_name,
            user_id=body.user_id,
        )

        logger.info(f"Plaid account connected: {result['institution_name']}")

        return ItemInfo(
            item_id=result["item_id"],
            institution_id=result.get("institution_id"),
            institution_name=result.get("institution_name"),
            products=result.get("products", []),
        )

    except Exception as e:
        logger.error(f"Failed to exchange public token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_item(
    request: Request,
    item_id: str = Query(..., description="Plaid Item ID to disconnect"),
):
    """
    Disconnect a Plaid Item.

    Revokes access with Plaid and marks token as inactive.
    """
    try:
        from src.integrations.plaid import PlaidOAuth

        db_pool = request.app.state.db_pool
        oauth = PlaidOAuth(db_pool=db_pool)

        success = await oauth.disconnect(item_id)

        if success:
            return {"success": True, "message": f"Disconnected {item_id}"}
        else:
            raise HTTPException(status_code=404, detail="Item not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# SYNC ENDPOINTS
# ==========================================

@router.post("/sync/{item_id}", response_model=SyncResult)
async def sync_item(
    request: Request,
    item_id: str,
):
    """
    Sync all data for a Plaid Item.

    Fetches and stores:
    - Securities master data
    - Account information
    - Position snapshots
    - Recent transactions (90 days)

    PRIVACY: Dollar amounts encrypted before storage.
    """
    try:
        from src.integrations.plaid import PlaidSyncService

        db_pool = request.app.state.db_pool
        sync = PlaidSyncService(db_pool=db_pool)

        result = await sync.sync_item(item_id)

        return SyncResult(
            success=True,
            item_id=result["item_id"],
            synced_at=result["synced_at"],
            securities=result["securities"],
            accounts=result["accounts"],
            positions=result["positions"],
            transactions=result["transactions"],
        )

    except Exception as e:
        logger.error(f"Sync failed for item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-all")
async def sync_all_items(request: Request, user_id: str = "default"):
    """
    Sync all connected Plaid Items for a user.

    Iterates through all active connections and syncs each.
    Returns summary of all sync operations.
    """
    try:
        from src.integrations.plaid import PlaidOAuth, PlaidSyncService

        db_pool = request.app.state.db_pool
        oauth = PlaidOAuth(db_pool=db_pool)
        sync = PlaidSyncService(db_pool=db_pool)

        # Get all active connections
        status = await oauth.get_connection_status(user_id)

        if not status["connected"]:
            return {
                "success": False,
                "message": "No connected accounts",
                "synced": [],
            }

        results = []
        for inst in status["institutions"]:
            if inst["is_active"]:
                try:
                    result = await sync.sync_item(inst["item_id"])
                    results.append({
                        "item_id": inst["item_id"],
                        "institution": inst["institution_name"],
                        "success": True,
                        **result,
                    })
                except Exception as e:
                    results.append({
                        "item_id": inst["item_id"],
                        "institution": inst["institution_name"],
                        "success": False,
                        "error": str(e),
                    })

        successful = sum(1 for r in results if r["success"])

        return {
            "success": successful == len(results),
            "message": f"Synced {successful}/{len(results)} accounts",
            "synced": results,
        }

    except Exception as e:
        logger.error(f"Sync all failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# PORTFOLIO DATA ENDPOINTS
# ==========================================

@router.get("/holdings")
async def get_holdings(
    request: Request,
    user_id: str = "default",
    snapshot_date: Optional[str] = Query(None, description="Date for snapshot (YYYY-MM-DD)"),
):
    """
    Get current investment holdings.

    Returns positions across all connected accounts.
    Dollar amounts are decrypted for display.
    """
    try:
        from src.storage.database import get_db_connection

        snapshot = date.fromisoformat(snapshot_date) if snapshot_date else date.today()

        async with get_db_connection() as conn:
            # Get positions with security and account info
            rows = await conn.fetch("""
                SELECT
                    p.id,
                    p.snapshot_date,
                    p.quantity,
                    p.market_value_encrypted,
                    p.cost_basis_encrypted,
                    p.price_per_share,
                    s.ticker,
                    s.name as security_name,
                    s.security_type,
                    s.sector,
                    a.account_name,
                    pt.institution_name
                FROM positions_daily p
                JOIN securities_master s ON p.security_id = s.id
                JOIN financial_accounts a ON p.account_id = a.id
                JOIN plaid_tokens pt ON a.plaid_item_id = pt.item_id
                WHERE pt.user_id = $1
                  AND p.snapshot_date = $2
                ORDER BY s.ticker
            """, user_id, snapshot)

            # Decrypt amounts
            from src.integrations.plaid import PlaidSyncService
            db_pool = request.app.state.db_pool
            sync = PlaidSyncService(db_pool=db_pool)

            holdings = []
            total_value = 0
            total_cost = 0

            for row in rows:
                market_value = sync._decrypt(row["market_value_encrypted"])
                cost_basis = sync._decrypt(row["cost_basis_encrypted"]) if row["cost_basis_encrypted"] else None

                total_value += market_value
                if cost_basis:
                    total_cost += cost_basis

                holdings.append({
                    "ticker": row["ticker"],
                    "name": row["security_name"],
                    "security_type": row["security_type"],
                    "sector": row["sector"],
                    "account": row["account_name"],
                    "institution": row["institution_name"],
                    "quantity": float(row["quantity"]),
                    "price": float(row["price_per_share"]) if row["price_per_share"] else None,
                    "market_value": market_value,
                    "cost_basis": cost_basis,
                    "gain_loss": market_value - cost_basis if cost_basis else None,
                    "gain_loss_pct": ((market_value / cost_basis) - 1) * 100 if cost_basis else None,
                })

        return {
            "snapshot_date": snapshot.isoformat(),
            "total_value": total_value,
            "total_cost": total_cost,
            "total_gain_loss": total_value - total_cost,
            "holdings": holdings,
            "count": len(holdings),
        }

    except Exception as e:
        logger.error(f"Failed to get holdings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
async def get_transactions(
    request: Request,
    user_id: str = "default",
    days: int = Query(90, ge=1, le=365, description="Number of days of history"),
    transaction_type: Optional[str] = Query(None, description="Filter by type: buy, sell, dividend, etc."),
):
    """
    Get investment transactions.

    Returns transactions across all connected accounts.
    Dollar amounts are decrypted for display.
    """
    try:
        from src.storage.database import get_db_connection

        start_date = date.today() - timedelta(days=days)

        async with get_db_connection() as conn:
            query = """
                SELECT
                    t.id,
                    t.transaction_date,
                    t.transaction_type,
                    t.quantity,
                    t.amount_encrypted,
                    t.price_encrypted,
                    t.fees_encrypted,
                    t.description,
                    s.ticker,
                    s.name as security_name,
                    a.account_name,
                    pt.institution_name
                FROM financial_transactions t
                LEFT JOIN securities_master s ON t.security_id = s.id
                JOIN financial_accounts a ON t.account_id = a.id
                JOIN plaid_tokens pt ON a.plaid_item_id = pt.item_id
                WHERE pt.user_id = $1
                  AND t.transaction_date >= $2
            """
            params = [user_id, start_date]

            if transaction_type:
                query += " AND t.transaction_type = $3"
                params.append(transaction_type)

            query += " ORDER BY t.transaction_date DESC"

            rows = await conn.fetch(query, *params)

            # Decrypt amounts
            from src.integrations.plaid import PlaidSyncService
            db_pool = request.app.state.db_pool
            sync = PlaidSyncService(db_pool=db_pool)

            transactions = []
            for row in rows:
                amount = sync._decrypt(row["amount_encrypted"])
                price = sync._decrypt(row["price_encrypted"]) if row["price_encrypted"] else None
                fees = sync._decrypt(row["fees_encrypted"]) if row["fees_encrypted"] else None

                transactions.append({
                    "date": row["transaction_date"].isoformat(),
                    "type": row["transaction_type"],
                    "ticker": row["ticker"],
                    "security_name": row["security_name"],
                    "account": row["account_name"],
                    "institution": row["institution_name"],
                    "quantity": float(row["quantity"]) if row["quantity"] else None,
                    "amount": amount,
                    "price": price,
                    "fees": fees,
                    "description": row["description"],
                })

        return {
            "start_date": start_date.isoformat(),
            "end_date": date.today().isoformat(),
            "transactions": transactions,
            "count": len(transactions),
        }

    except Exception as e:
        logger.error(f"Failed to get transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts")
async def get_accounts(
    request: Request,
    user_id: str = "default",
):
    """
    Get connected financial accounts.

    Returns all accounts across all connected Plaid Items.
    """
    try:
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            rows = await conn.fetch("""
                SELECT
                    a.id,
                    a.account_name,
                    a.account_type,
                    a.account_subtype,
                    a.last_synced_at,
                    pt.institution_name,
                    pt.item_id
                FROM financial_accounts a
                JOIN plaid_tokens pt ON a.plaid_item_id = pt.item_id
                WHERE pt.user_id = $1
                  AND pt.is_active = TRUE
                ORDER BY pt.institution_name, a.account_name
            """, user_id)

            accounts = []
            for row in rows:
                accounts.append({
                    "id": str(row["id"]),
                    "name": row["account_name"],
                    "type": row["account_type"],
                    "subtype": row["account_subtype"],
                    "institution": row["institution_name"],
                    "item_id": row["item_id"],
                    "last_synced": row["last_synced_at"].isoformat() if row["last_synced_at"] else None,
                })

        return {
            "accounts": accounts,
            "count": len(accounts),
        }

    except Exception as e:
        logger.error(f"Failed to get accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# SECURITIES ENDPOINTS
# ==========================================

@router.get("/securities")
async def get_securities(
    request: Request,
    security_type: Optional[str] = Query(None, description="Filter by type: equity, etf, mutual_fund, etc."),
    sector: Optional[str] = Query(None, description="Filter by sector"),
):
    """
    Get securities master data.

    Returns all securities in the system with tags and metadata.
    """
    try:
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            query = """
                SELECT
                    s.id,
                    s.ticker,
                    s.cusip,
                    s.isin,
                    s.name,
                    s.security_type,
                    s.sector,
                    s.is_cash_equivalent,
                    s.last_close_price,
                    s.last_close_date,
                    s.currency,
                    array_agg(DISTINCT st.tag) FILTER (WHERE st.tag IS NOT NULL) as tags
                FROM securities_master s
                LEFT JOIN security_tags st ON s.id = st.security_id
                WHERE 1=1
            """
            params = []
            param_idx = 1

            if security_type:
                query += f" AND s.security_type = ${param_idx}"
                params.append(security_type)
                param_idx += 1

            if sector:
                query += f" AND s.sector = ${param_idx}"
                params.append(sector)
                param_idx += 1

            query += " GROUP BY s.id ORDER BY s.ticker"

            rows = await conn.fetch(query, *params)

            securities = []
            for row in rows:
                securities.append({
                    "id": str(row["id"]),
                    "ticker": row["ticker"],
                    "cusip": row["cusip"],
                    "isin": row["isin"],
                    "name": row["name"],
                    "type": row["security_type"],
                    "sector": row["sector"],
                    "is_cash": row["is_cash_equivalent"],
                    "last_price": float(row["last_close_price"]) if row["last_close_price"] else None,
                    "price_date": row["last_close_date"].isoformat() if row["last_close_date"] else None,
                    "currency": row["currency"],
                    "tags": row["tags"] or [],
                })

        return {
            "securities": securities,
            "count": len(securities),
        }

    except Exception as e:
        logger.error(f"Failed to get securities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/securities/{ticker}/tag")
async def add_security_tag(
    request: Request,
    ticker: str,
    tag: str = Query(..., description="Tag to add"),
    sub_theme: Optional[str] = Query(None, description="Sub-theme classification"),
):
    """
    Add a tag to a security.

    Tags are used for allocation bucket mapping and Constitution rules.
    Manual tags take precedence over seed and inferred tags.
    """
    try:
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            # Get security ID
            security = await conn.fetchrow(
                "SELECT id FROM securities_master WHERE ticker = $1",
                ticker.upper()
            )

            if not security:
                raise HTTPException(status_code=404, detail=f"Security {ticker} not found")

            # Add tag
            await conn.execute("""
                INSERT INTO security_tags (security_id, tag, source, sub_theme, confidence)
                VALUES ($1, $2, 'manual', $3, 1.0)
                ON CONFLICT (security_id, tag, source)
                DO UPDATE SET sub_theme = EXCLUDED.sub_theme, updated_at = NOW()
            """, security["id"], tag.upper(), sub_theme)

        return {
            "success": True,
            "ticker": ticker.upper(),
            "tag": tag.upper(),
            "source": "manual",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/securities/{ticker}/tag")
async def remove_security_tag(
    request: Request,
    ticker: str,
    tag: str = Query(..., description="Tag to remove"),
):
    """
    Remove a tag from a security.
    """
    try:
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            # Get security ID
            security = await conn.fetchrow(
                "SELECT id FROM securities_master WHERE ticker = $1",
                ticker.upper()
            )

            if not security:
                raise HTTPException(status_code=404, detail=f"Security {ticker} not found")

            # Remove tag
            result = await conn.execute("""
                DELETE FROM security_tags
                WHERE security_id = $1 AND tag = $2
            """, security["id"], tag.upper())

        return {
            "success": True,
            "ticker": ticker.upper(),
            "tag_removed": tag.upper(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))
