"""
Tenants API endpoints for managing tenant information and payment status.
"""

import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tenant import (
    Tenant,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantStats,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=TenantStats)
async def get_tenant_stats(db: Session = Depends(get_db)):
    """Get tenant statistics for dashboard."""
    try:
        total_tenants = db.query(Tenant).filter(Tenant.active == True).count()
        paid_tenants = (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.is_current_month_rent_paid == True)
            .count()
        )
        unpaid_tenants = total_tenants - paid_tenants
        late_fee_tenants = (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.late_fee_applicable == True)
            .count()
        )

        return TenantStats(
            total=total_tenants,
            paid=paid_tenants,
            unpaid=unpaid_tenants,
            late_fees=late_fee_tenants,
        )

    except Exception as e:
        logger.error(f"Failed to get tenant stats: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve tenant statistics"
        )


@router.get("/", response_model=List[TenantResponse])
async def get_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("name"),
    db: Session = Depends(get_db),
):
    """Get list of tenants with filtering and pagination."""
    try:
        query = db.query(Tenant).filter(Tenant.active == True)

        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                Tenant.name.ilike(search_term)
                | Tenant.contact.ilike(search_term)
            )

        # Payment status filter
        if payment_status == "paid":
            query = query.filter(Tenant.is_current_month_rent_paid == True)
        elif payment_status == "unpaid":
            query = query.filter(Tenant.is_current_month_rent_paid == False)
        elif payment_status == "late":
            query = query.filter(Tenant.late_fee_applicable == True)

        # Sorting
        if sort_by == "name":
            query = query.order_by(Tenant.name)
        elif sort_by == "building":
            query = query.order_by(Tenant.building)
        elif sort_by == "payment_date":
            query = query.order_by(Tenant.last_payment_date.desc().nullslast())

        tenants = query.offset(skip).limit(limit).all()
        return tenants

    except Exception as e:
        logger.error(f"Failed to get tenants: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tenants")


@router.get("/export")
async def export_tenants(db: Session = Depends(get_db)):
    """Export tenants to CSV file."""
    try:
        from fastapi.responses import StreamingResponse
        from io import StringIO
        import csv

        tenants = (
            db.query(Tenant).filter(Tenant.active == True).order_by(Tenant.name).all()
        )

        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = [
            "Name", "Email", "Phone", "Unit", "Rent Amount", "Emergency Contact",
            "Lease Start", "Lease End", "Tenant Type", "Rent Paid", "Last Payment", 
            "Late Fee", "Notes"
        ]
        writer.writerow(headers)
        
        # Write tenant data
        for tenant in tenants:
            row = [
                tenant.name,
                "",  # No email field in current schema
                tenant.contact,  # Using existing contact field
                tenant.building or "",  # Using existing building field
                tenant.rent or 0,  # Using existing rent field
                "",  # No emergency_contact field in current schema
                "",  # No lease_start_date field in current schema
                "",  # No lease_end_date field in current schema
                tenant.tenant_type,
                "Yes" if tenant.is_current_month_rent_paid else "No",
                tenant.last_payment_date.strftime("%Y-%m-%d") if tenant.last_payment_date else "",
                "Yes" if tenant.late_fee_applicable else "No",
                tenant.notes or "",
            ]
            writer.writerow(row)

        output.seek(0)

        return StreamingResponse(
            StringIO(output.getvalue()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=tenants_{datetime.now().strftime('%Y%m%d')}.csv"
            },
        )

    except Exception as e:
        logger.error(f"Failed to export tenants: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export tenants")


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    """Get single tenant by ID."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.post("/", response_model=TenantResponse)
async def create_tenant(tenant_data: TenantCreate, db: Session = Depends(get_db)):
    """Create new tenant."""
    try:
        # Check if phone already exists
        existing_tenant = (
            db.query(Tenant).filter(Tenant.contact == tenant_data.contact).first()
        )
        if existing_tenant:
            raise HTTPException(status_code=400, detail="Contact number already exists")

        tenant = Tenant(
            name=tenant_data.name,
            contact=tenant_data.contact,
            rent=tenant_data.rent,
            due_date=tenant_data.due_date,
            building=tenant_data.building,
            tenant_type=tenant_data.tenant_type,
            notes=tenant_data.notes,
            created_at=datetime.utcnow(),
        )

        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        logger.info(f"Created tenant: {tenant.name} (ID: {tenant.id})")
        return tenant

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create tenant: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create tenant")


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int, tenant_data: TenantUpdate, db: Session = Depends(get_db)
):
    """Update tenant information."""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Check if phone change conflicts with existing tenant
        if tenant_data.contact and tenant_data.contact != tenant.contact:
            existing_tenant = (
                db.query(Tenant)
                .filter(Tenant.contact == tenant_data.contact, Tenant.id != tenant_id)
                .first()
            )
            if existing_tenant:
                raise HTTPException(
                    status_code=400, detail="Contact number already exists"
                )

        # Update fields
        update_data = tenant_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        tenant.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(tenant)

        logger.info(f"Updated tenant: {tenant.name} (ID: {tenant.id})")
        return tenant

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update tenant")


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    """Soft delete tenant (mark as inactive)."""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.active = False
        tenant.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Deleted tenant: {tenant.name} (ID: {tenant.id})")
        return {"message": "Tenant deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete tenant {tenant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete tenant")


@router.post("/{tenant_id}/mark-paid")
async def mark_tenant_paid(tenant_id: int, db: Session = Depends(get_db)):
    """Mark tenant as having paid rent for current month."""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.is_current_month_rent_paid = True
        tenant.last_payment_date = datetime.utcnow()
        tenant.late_fee_applicable = False  # Clear late fee when paid
        tenant.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Marked tenant as paid: {tenant.name} (ID: {tenant.id})")
        return {"message": f"Tenant {tenant.name} marked as paid"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to mark tenant {tenant_id} as paid: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark tenant as paid")


@router.post("/bulk-mark-paid")
async def mark_all_tenants_paid(db: Session = Depends(get_db)):
    """Mark all tenants as having paid rent for current month."""
    try:
        updated_count = (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.is_current_month_rent_paid == False)
            .update(
                {
                    Tenant.is_current_month_rent_paid: True,
                    Tenant.last_payment_date: datetime.utcnow(),
                    Tenant.late_fee_applicable: False,
                    Tenant.updated_at: datetime.utcnow(),
                }
            )
        )

        db.commit()

        logger.info(f"Marked {updated_count} tenants as paid")
        return {"message": f"Marked {updated_count} tenants as paid"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to mark all tenants as paid: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to mark all tenants as paid"
        )


@router.post("/reset-monthly-status")
async def reset_monthly_payment_status(db: Session = Depends(get_db)):
    """Reset all tenants' monthly payment status (typically run at start of month)."""
    try:
        updated_count = (
            db.query(Tenant)
            .filter(Tenant.active == True)
            .update(
                {
                    Tenant.is_current_month_rent_paid: False,
                    Tenant.late_fee_applicable: False,
                    Tenant.updated_at: datetime.utcnow(),
                }
            )
        )

        db.commit()

        logger.info(f"Reset payment status for {updated_count} tenants")
        return {"message": f"Reset payment status for {updated_count} tenants"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset monthly payment status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset payment status")


@router.post("/apply-late-fees")
async def apply_late_fees(days_overdue: int = Query(5), db: Session = Depends(get_db)):
    """Apply late fees to tenants with overdue rent."""
    try:
        # Find tenants who haven't paid and are past due date
        updated_count = (
            db.query(Tenant)
            .filter(
                Tenant.active == True,
                Tenant.is_current_month_rent_paid == False,
                Tenant.late_fee_applicable == False,
            )
            .update(
                {Tenant.late_fee_applicable: True, Tenant.updated_at: datetime.utcnow()}
            )
        )

        db.commit()

        logger.info(f"Applied late fees to {updated_count} tenants")
        return {"message": f"Applied late fees to {updated_count} tenants"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to apply late fees: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to apply late fees")


@router.get("/unpaid/list", response_model=List[TenantResponse])
async def get_unpaid_tenants(db: Session = Depends(get_db)):
    """Get list of tenants who haven't paid rent."""
    try:
        tenants = (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.is_current_month_rent_paid == False)
            .order_by(Tenant.name)
            .all()
        )

        return tenants

    except Exception as e:
        logger.error(f"Failed to get unpaid tenants: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get unpaid tenants")


@router.get("/late-fees/list", response_model=List[TenantResponse])
async def get_late_fee_tenants(db: Session = Depends(get_db)):
    """Get list of tenants with late fees."""
    try:
        tenants = (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.late_fee_applicable == True)
            .order_by(Tenant.name)
            .all()
        )

        return tenants

    except Exception as e:
        logger.error(f"Failed to get late fee tenants: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get late fee tenants")


@router.post("/import")
async def import_tenants(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import tenants from CSV file."""
    try:
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="File must be a CSV")

        import pandas as pd
        from io import StringIO

        # Read CSV content
        content = await file.read()
        csv_content = StringIO(content.decode("utf-8"))
        df = pd.read_csv(csv_content)

        # Validate required columns
        required_columns = ["Name", "Contact"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}",
            )

        imported_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Check if tenant already exists
                existing_tenant = (
                    db.query(Tenant).filter(Tenant.contact == str(row["Contact"])).first()
                )

                if existing_tenant:
                    errors.append(
                        f"Row {index + 2}: Phone {row['Contact']} already exists"
                    )
                    continue

                tenant = Tenant(
                    name=str(row["Name"]),
                    contact=str(row["Contact"]),
                    rent=int(row.get("Rent", 0)) if row.get("Rent") else None,
                    due_date=str(row.get("Due Date", "")),
                    building=str(row.get("Building", "")),
                    notes=str(row.get("Notes", "")),
                    created_at=datetime.utcnow(),
                )

                db.add(tenant)
                imported_count += 1

            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")

        if imported_count > 0:
            db.commit()

        logger.info(f"Imported {imported_count} tenants with {len(errors)} errors")

        return {
            "message": f"Successfully imported {imported_count} tenants",
            "imported_count": imported_count,
            "errors": errors[:10],  # Limit error list
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to import tenants: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to import tenants")


