from typing import Any

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Asset


def asset_monitoring_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Monitor renewable energy assets using PostgreSQL records."""

    try:
        with SessionLocal() as db:
            assets = db.scalars(
                select(Asset).order_by(Asset.id)
            ).all()

            asset_records = [
                {
                    "id": asset.id,
                    "name": asset.name,
                    "asset_type": asset.asset_type,
                    "capacity_mw": asset.capacity_mw,
                    "location": asset.location,
                    "is_active": asset.is_active,
                }
                for asset in assets
            ]

        if not asset_records:
            summary = {
                "status": "no_assets_found",
                "total_assets": 0,
                "active_assets": 0,
                "inactive_assets": 0,
                "assets": [],
                "message": (
                    "No assets are registered in the database."
                ),
            }

            agent_result = {
                "status": "needs_input",
                "message": (
                    "Register renewable energy assets before monitoring."
                ),
            }

        else:
            active_assets = [
                asset
                for asset in asset_records
                if asset["is_active"]
            ]

            inactive_assets = [
                asset
                for asset in asset_records
                if not asset["is_active"]
            ]

            summary = {
                "status": (
                    "healthy"
                    if not inactive_assets
                    else "attention_required"
                ),
                "total_assets": len(asset_records),
                "active_assets": len(active_assets),
                "inactive_assets": len(inactive_assets),
                "assets": asset_records,
                "inactive_asset_details": inactive_assets,
            }

            agent_result = {
                "status": summary["status"],
                "total_assets": len(asset_records),
                "active_assets": len(active_assets),
                "inactive_assets": len(inactive_assets),
            }

        return {
            "asset_status": summary,
            "agent_results": {
                "asset_monitoring": agent_result,
            },
            "execution_trace": [
                f"asset_monitoring:{agent_result['status']}"
            ],
        }

    except Exception as exc:
        return {
            "asset_status": {
                "status": "error",
                "message": "Asset monitoring could not access the database.",
            },
            "agent_results": {
                "asset_monitoring": {
                    "status": "error",
                    "message": str(exc),
                }
            },
            "execution_trace": [
                "asset_monitoring:error"
            ],
            "errors": [
                f"Asset monitoring failed: {exc}"
            ],
        }