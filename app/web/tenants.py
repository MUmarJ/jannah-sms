"""
Tenants web interface routes.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def tenants_list(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    payment_status: Optional[str] = None,
    sort_by: Optional[str] = "name",
    db: Session = Depends(get_db),
):
    """Tenants list page with filtering and pagination."""
    try:
        per_page = 25
        offset = (page - 1) * per_page

        # Build query
        query = db.query(Tenant).filter(Tenant.active == True)

        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                Tenant.name.ilike(search_term)
                | Tenant.phone.ilike(search_term)
                | Tenant.email.ilike(search_term)
                | Tenant.unit_number.ilike(search_term)
            )

        # Apply payment status filter
        if payment_status == "paid":
            query = query.filter(Tenant.is_current_month_rent_paid == True)
        elif payment_status == "unpaid":
            query = query.filter(Tenant.is_current_month_rent_paid == False)
        elif payment_status == "late":
            query = query.filter(Tenant.late_fee_applicable == True)

        # Apply sorting
        if sort_by == "name":
            query = query.order_by(Tenant.name)
        elif sort_by == "unit":
            query = query.order_by(Tenant.unit_number)
        elif sort_by == "payment_date":
            query = query.order_by(Tenant.last_payment_date.desc().nullslast())

        # Get total count for pagination
        total_count = query.count()

        # Get tenants for current page
        tenants = query.offset(offset).limit(per_page).all()

        # Get statistics
        stats = await _get_tenant_stats(db)

        # Pagination info
        total_pages = (total_count + per_page - 1) // per_page
        pagination = (
            {
                "page": page,
                "pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_num": page - 1 if page > 1 else None,
                "next_num": page + 1 if page < total_pages else None,
            }
            if total_pages > 1
            else None
        )

        return templates.TemplateResponse(
            "tenants.html",
            {
                "request": request,
                "tenants": tenants,
                "stats": stats,
                "pagination": pagination,
                "search": search,
                "payment_status": payment_status,
                "sort_by": sort_by,
            },
        )

    except Exception as e:
        logger.error(f"Tenants list error: {e!s}")
        return templates.TemplateResponse(
            "error.html", {"request": request, "error": "Failed to load tenants"}
        )


@router.get("/add", response_class=HTMLResponse)
async def add_tenant_form(request: Request):
    """Add tenant form page."""
    return templates.TemplateResponse(
        "tenant_form.html", {"request": request, "action": "add", "tenant": None}
    )


@router.post("/add")
async def add_tenant_submit(
    request: Request,
    name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: str = Form(...),
    unit_number: Optional[str] = Form(None),
    rent_amount: Optional[float] = Form(None),
    emergency_contact: Optional[str] = Form(None),
    lease_start_date: Optional[str] = Form(None),
    lease_end_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Handle add tenant form submission."""
    try:
        # Check if contact already exists
        existing_tenant = db.query(Tenant).filter(Tenant.contact == phone).first()
        if existing_tenant:
            return RedirectResponse(
                url="/tenants/add?error=phone_exists", status_code=302
            )

        # Parse dates
        lease_start = None
        lease_end = None
        if lease_start_date:
            try:
                lease_start = datetime.strptime(lease_start_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        if lease_end_date:
            try:
                lease_end = datetime.strptime(lease_end_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Create tenant
        tenant = Tenant(
            name=name.strip(),
            contact=phone.strip(),
            building=unit_number.strip() if unit_number else None,
            rent=int(rent_amount) if rent_amount else None,
            notes=notes.strip() if notes else None,
            created_at=datetime.utcnow(),
        )

        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        logger.info(f"Created tenant: {tenant.name} (ID: {tenant.id})")

        return RedirectResponse(url="/tenants?success=tenant_added", status_code=302)

    except Exception as e:
        db.rollback()
        logger.error(f"Add tenant error: {e!s}")
        return RedirectResponse(url="/tenants/add?error=add_failed", status_code=302)


@router.get("/{tenant_id}/edit", response_class=HTMLResponse)
async def edit_tenant_form(
    tenant_id: int, request: Request, db: Session = Depends(get_db)
):
    """Edit tenant form page."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return RedirectResponse(url="/tenants?error=tenant_not_found", status_code=302)

    return templates.TemplateResponse(
        "tenant_form.html", {"request": request, "action": "edit", "tenant": tenant}
    )


@router.post("/{tenant_id}/edit")
async def edit_tenant_submit(
    tenant_id: int,
    request: Request,
    name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: str = Form(...),
    unit_number: Optional[str] = Form(None),
    rent_amount: Optional[float] = Form(None),
    emergency_contact: Optional[str] = Form(None),
    lease_start_date: Optional[str] = Form(None),
    lease_end_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Handle edit tenant form submission."""
    try:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return RedirectResponse(
                url="/tenants?error=tenant_not_found", status_code=302
            )

        # Check if phone change conflicts with existing tenant
        if phone != tenant.contact:
            existing_tenant = (
                db.query(Tenant)
                .filter(Tenant.contact == phone, Tenant.id != tenant_id)
                .first()
            )
            if existing_tenant:
                return RedirectResponse(
                    url=f"/tenants/{tenant_id}/edit?error=phone_exists", status_code=302
                )

        # Parse dates
        lease_start = None
        lease_end = None
        if lease_start_date:
            try:
                lease_start = datetime.strptime(lease_start_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        if lease_end_date:
            try:
                lease_end = datetime.strptime(lease_end_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Update tenant
        tenant.name = name.strip()
        tenant.contact = phone.strip()
        tenant.building = unit_number.strip() if unit_number else None
        tenant.rent = int(rent_amount) if rent_amount else None
        tenant.notes = notes.strip() if notes else None
        tenant.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Updated tenant: {tenant.name} (ID: {tenant.id})")

        return RedirectResponse(url="/tenants?success=tenant_updated", status_code=302)

    except Exception as e:
        db.rollback()
        logger.error(f"Edit tenant error: {e!s}")
        return RedirectResponse(
            url=f"/tenants/{tenant_id}/edit?error=update_failed", status_code=302
        )


@router.get("/import", response_class=HTMLResponse)
async def import_tenants_form(request: Request):
    """Import tenants form page."""
    return templates.TemplateResponse("tenant_import.html", {"request": request})


@router.post("/import")
async def import_tenants_submit(
    request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Handle tenant import form submission."""
    try:
        if not file.filename.endswith(".csv"):
            return RedirectResponse(
                url="/tenants/import?error=invalid_file", status_code=302
            )

        from io import StringIO

        import pandas as pd

        # Read CSV content
        content = await file.read()
        csv_content = StringIO(content.decode("utf-8"))
        df = pd.read_csv(csv_content)

        # Validate required columns
        required_columns = ["Name", "Contact"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return RedirectResponse(
                url=f"/tenants/import?error=missing_columns_{','.join(missing_columns)}",
                status_code=302,
            )

        imported_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Check if tenant already exists
                existing_tenant = (
                    db.query(Tenant)
                    .filter(Tenant.contact == str(row["Contact"]))
                    .first()
                )

                if existing_tenant:
                    errors.append(
                        f"Row {index + 2}: Phone {row['Contact']} already exists"
                    )
                    continue

                # Parse dates
                lease_start = None
                lease_end = None
                if "Lease Start" in row and pd.notna(row["Lease Start"]):
                    try:
                        lease_start = pd.to_datetime(row["Lease Start"]).date()
                    except:
                        pass
                if "Lease End" in row and pd.notna(row["Lease End"]):
                    try:
                        lease_end = pd.to_datetime(row["Lease End"]).date()
                    except:
                        pass

                tenant = Tenant(
                    name=str(row["Name"]).strip(),
                    contact=str(row["Contact"]).strip(),
                    building=(
                        str(row.get("Building", "")).strip()
                        if pd.notna(row.get("Building"))
                        else None
                    ),
                    rent=(
                        int(float(row.get("Rent", 0)))
                        if pd.notna(row.get("Rent")) and row.get("Rent") != 0
                        else None
                    ),
                    due_date=(
                        str(row.get("Due Date", "")).strip()
                        if pd.notna(row.get("Due Date"))
                        else None
                    ),
                    notes=(
                        str(row.get("Notes", "")).strip()
                        if pd.notna(row.get("Notes"))
                        else None
                    ),
                    created_at=datetime.utcnow(),
                )

                db.add(tenant)
                imported_count += 1

            except Exception as e:
                errors.append(f"Row {index + 2}: {e!s}")

        if imported_count > 0:
            db.commit()

        logger.info(f"Imported {imported_count} tenants with {len(errors)} errors")

        return RedirectResponse(
            url=f"/tenants?success=imported_{imported_count}_tenants", status_code=302
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Import tenants error: {e!s}")
        return RedirectResponse(
            url="/tenants/import?error=import_failed", status_code=302
        )


async def _get_tenant_stats(db: Session) -> dict:
    """Get tenant statistics."""
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

        return {
            "total_tenants": total_tenants,
            "paid_tenants": paid_tenants,
            "unpaid_tenants": unpaid_tenants,
            "late_fee_tenants": late_fee_tenants,
        }

    except Exception as e:
        logger.error(f"Error getting tenant stats: {e!s}")
        return {
            "total_tenants": 0,
            "paid_tenants": 0,
            "unpaid_tenants": 0,
            "late_fee_tenants": 0,
        }
