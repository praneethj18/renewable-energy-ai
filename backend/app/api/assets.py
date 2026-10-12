from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Asset

router = APIRouter(prefix="/assets", tags=["Assets"])


class AssetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    asset_type: str = Field(pattern="^(solar|wind|battery)$")
    capacity_mw: float = Field(gt=0)
    location: str = Field(min_length=2, max_length=200)


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    asset_type: str | None = Field(default=None, pattern="^(solar|wind|battery)$")
    capacity_mw: float | None = Field(default=None, gt=0)
    location: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool | None = None


class AssetResponse(BaseModel):
    id: int
    name: str
    asset_type: str
    capacity_mw: float
    location: str
    is_active: bool

    model_config = {"from_attributes": True}


@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/", response_model=list[AssetResponse])
def list_assets(db: Session = Depends(get_db)):
    return db.query(Asset).order_by(Asset.id).all()


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)

    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    return asset


@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")

    for field, value in changes.items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)
    return asset
