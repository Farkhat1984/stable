from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query  # добавляем status
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.config import get_db
from app.api.auth_handlers import get_current_user
from app.crud import crud
from app.models.models import User, Invoice
from app.schemas.schemas import InvoiceCreate, InvoiceResponse, InvoiceFilter, InvoiceUpdate

router = APIRouter(prefix="/api/v1")


# Добавьте этот эндпоинт в ваш существующий router

@router.get("/invoices/next-invoice-id", response_model=Dict[str, Any])
async def get_next_invoice_id(
        shop_id: int,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    try:
        # Проверяем доступ к магазину
        has_access = await crud.check_user_shop_access(session, current_user.id, shop_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="No access to this shop")

        # Получаем максимальный ID для данного магазина за текущий день
        today = datetime.now().date()
        query = select(func.coalesce(func.max(Invoice.id), 0)).where(
            and_(
                Invoice.shop_id == shop_id,
                func.date(Invoice.created_at) == today
            )
        )
        result = await session.execute(query)
        current_max_id = result.scalar()

        # Получаем общий максимальный ID
        query_total = select(func.coalesce(func.max(Invoice.id), 0))
        result_total = await session.execute(query_total)
        total_max_id = result_total.scalar()

        next_id = total_max_id + 1

        # Форматируем номер инвойса: YYYYMMDD-SHOPID-XXX
        today_str = today.strftime("%Y%m%d")
        shop_count_query = select(func.count(Invoice.id)).where(
            and_(
                Invoice.shop_id == shop_id,
                func.date(Invoice.created_at) == today
            )
        )
        shop_count_result = await session.execute(shop_count_query)
        shop_count = shop_count_result.scalar() or 0
        sequence_number = str(shop_count + 1).zfill(3)

        formatted_number = f"{today_str}-{shop_id}-{sequence_number}"

        return {
            "next_id": next_id,
            "formatted_number": formatted_number,
            "shop_id": shop_id,
            "date": today.strftime("%Y-%m-%d")
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoices/", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
        invoice_data: InvoiceCreate,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    try:
        invoice = await crud.insert_invoice(
            session=session,
            invoice_data=invoice_data,
            current_user=current_user
        )
        return invoice

    except HTTPException as e:
        await session.rollback()
        raise e
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/invoices/", response_model=List[InvoiceResponse])
async def list_invoices(
        shop_id: Optional[int] = None,
        is_paid: Optional[bool] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        skip: int = Query(default=0, ge=0),
        limit: int = Query(default=100, le=100),
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):

    filters = InvoiceFilter(
        shop_id=shop_id,
        is_paid=is_paid,
        created_after=created_after,
        created_before=created_before,
        min_amount=min_amount,
        max_amount=max_amount
    )
    try:
        invoices = await crud.fetch_invoices_with_filters(
            session,
            current_user,
            filters,
            skip,
            limit
        )
        return invoices
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
        invoice_id: int,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):

    try:
        invoice = await crud.fetch_invoice(session, invoice_id, current_user)
        return invoice
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
        invoice_id: int,
        invoice_data: InvoiceUpdate,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):

    try:
        invoice = await crud.update_invoice(
            session,
            invoice_id,
            invoice_data,
            current_user
        )
        return invoice
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/invoices/{invoice_id}", status_code=204)
async def delete_invoice(
        invoice_id: int,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):

    try:
        await crud.delete_invoice(session, invoice_id, current_user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Additional route for quick status update
@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
        invoice_id: int,
        is_paid: bool,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):

    update_data = InvoiceUpdate(is_paid=is_paid)
    try:
        invoice = await crud.update_invoice(
            session,
            invoice_id,
            update_data,
            current_user
        )
        return invoice
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Statistics route
@router.get("/invoices/stats/summary")
async def get_invoice_stats(
        shop_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):

    try:
        # Create base query
        query = select(
            func.count(Invoice.id).label('total_invoices'),
            func.sum(Invoice.total_amount).label('total_amount'),
            func.avg(Invoice.total_amount).label('average_amount'),
            func.sum(case((Invoice.is_paid, 1), else_=0)).label('paid_invoices'),
        )

        # Apply filters
        if shop_id:
            has_access = await crud.check_user_shop_access(session, current_user.id, shop_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="No access to this shop")
            query = query.where(Invoice.shop_id == shop_id)

        if start_date:
            query = query.where(Invoice.created_at >= start_date)

        if end_date:
            query = query.where(Invoice.created_at <= end_date)

        # Execute query
        result = await session.execute(query)
        stats = result.first()

        # Безопасное получение значений с обработкой NULL
        total_invoices = stats.total_invoices or 0
        total_amount = float(stats.total_amount or 0)
        average_amount = float(stats.average_amount or 0)
        paid_invoices = stats.paid_invoices or 0

        return {
            "total_invoices": total_invoices,
            "total_amount": total_amount,
            "average_amount": average_amount,
            "paid_invoices": paid_invoices,
            "unpaid_invoices": total_invoices - paid_invoices
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
