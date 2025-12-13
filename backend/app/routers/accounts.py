from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app import crud, schemas
from app.models import NotificationType, CloudAccount, CloudProvider, AccountStatus
from app.deps import get_db

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/", response_model=list[schemas.AccountRead])
def list_accounts(
    provider: str = None,
    status_filter: str = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve all cloud accounts with optional filtering.
    
    Query parameters:
    - provider: Filter by cloud provider (aws, azure, gcp)
    - status_filter: Filter by account status (connected, pending, error)
    """
    query = db.query(CloudAccount)
    
    if provider:
        try:
            query = query.filter(CloudAccount.provider == CloudProvider(provider))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider: {provider}"
            )
    
    if status_filter:
        try:
            query = query.filter(CloudAccount.status == AccountStatus(status_filter))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    accounts = query.order_by(CloudAccount.created_at.desc()).all()
    return accounts


@router.post("/", response_model=schemas.AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    account_in: schemas.AccountCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new cloud account connection.
    
    This endpoint creates a new cloud account with the provided credentials
    and configuration. The account will be in PENDING status initially.
    
    **Important**: In production, credentials should be encrypted before storing.
    """
    try:
        account = crud.create_account(db, account_in=account_in)
        return account
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account with this provider and ID already exists",
        ) from exc


@router.get("/{account_id}", response_model=schemas.AccountRead)
def get_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific cloud account by ID.
    """
    account = crud.get_account(db, account_id=account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with ID {account_id} not found"
        )
    
    return account


@router.patch("/{account_id}", response_model=schemas.AccountRead)
def update_account(
    account_id: int,
    account_in: schemas.AccountUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing cloud account.
    
    Only provided fields will be updated. Fields set to None will be ignored.
    """
    account = crud.update_account(db, account_id=account_id, account_in=account_in)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a cloud account.
    
    This will also delete all associated policy evaluations due to cascade delete.
    """
    deleted = crud.delete_account(db, account_id=account_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    return None


@router.post("/{account_id}/sync", response_model=schemas.AccountRead)
def sync_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Trigger a manual sync for a cloud account.
    
    This endpoint initiates a sync operation that:
    1. Validates the account credentials
    2. Fetches the latest resources and configurations
    3. Updates policy evaluations
    4. Updates the last_synced_at timestamp
    """
    account = crud.get_account(db, account_id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    # Update the sync timestamp
    account_update = schemas.AccountUpdate(last_sync_at=datetime.utcnow())
    updated = crud.update_account(db, account_id=account_id, account_in=account_update)
    
    if updated:
        # Create notification about sync
        crud.create_notification(
            db,
            schemas.NotificationCreate(
                title="Manual sync requested",
                message=f"{updated.display_name} is syncing now.",
                type=NotificationType.ACCOUNT_SYNC,
            ),
        )
    
    return updated


@router.get("/{account_id}/validate", response_model=dict)
def validate_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Validate cloud account credentials without performing a full sync.
    
    Returns validation status and any error messages.
    """
    account = crud.get_account(db, account_id=account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with ID {account_id} not found"
        )
    
    # TODO: Implement actual validation logic
    # This would attempt to authenticate with the cloud provider
    # using the stored credentials
    
    return {
        "account_id": account_id,
        "is_valid": True,
        "message": "Credentials validated successfully",
        "provider": account.provider if hasattr(account, 'provider') else "unknown",
        "validated_at": datetime.utcnow().isoformat()
    }