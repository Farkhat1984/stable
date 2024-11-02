# controllers/invoice_api_controller.py
from datetime import timedelta, datetime
from typing import Dict, Any, Optional, Callable
from .base_api_controller import BaseAPIController
import json
import logging

logger = logging.getLogger(__name__)


class InvoiceAPIController(BaseAPIController):
    def __init__(self, base_url: str = "http://localhost:8000", auth_controller: Optional[Any] = None):
        super().__init__(base_url=base_url, auth_controller=auth_controller)

    def create_invoice(
            self,
            invoice_data: Dict[str, Any],
            success_callback: Optional[Callable[[Any], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """Create a new invoice."""
        endpoint = "/api/v1/invoices/"
        logger.debug(f"Creating invoice with data: {invoice_data}")

        # Prepare invoice data for API
        try:
            api_invoice_data = {
                "shop_id": int(invoice_data.get("shop_id", 1)),
                "contact_info": str(invoice_data.get("contact", "")),
                "additional_info": str(invoice_data.get("additional_info", "")),
                "total_amount": float(invoice_data.get("total", 0)),
                "is_paid": bool(invoice_data.get("is_paid", False)),
                "items": [
                    {
                        "name": item["name"],
                        "article": item.get("article", ""),
                        "quantity": float(item["quantity"]),
                        "price": float(item["price"]),
                        "total": float(item["sum"])
                    }
                    for item in invoice_data.get("items", [])
                    if item.get("name") and item.get("quantity") and item.get("price")
                ]
            }
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid invoice data: {e}")
            if error_callback:
                error_callback(f"Invalid invoice data: {e}")
            return

        logger.debug(f"Prepared invoice data for API: {api_invoice_data}")

        req_body = json.dumps(api_invoice_data)
        self._make_request(
            endpoint=endpoint,
            method='POST',
            req_body=req_body,
            headers=self._get_headers(),
            success_callback=lambda req, result: success_callback(result) if success_callback else None,
            error_callback=error_callback
        )

    def update_invoice(
            self,
            invoice_id: int,
            invoice_data: Dict[str, Any],
            success_callback: Optional[Callable[[Any], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """Update an existing invoice."""
        endpoint = f"/api/v1/invoices/{invoice_id}"
        logger.debug(f"Updating invoice ID: {invoice_id} with data: {invoice_data}")

        # Prepare update data
        try:
            update_data = {
                "contact_info": str(invoice_data.get("contact", "")),
                "additional_info": str(invoice_data.get("additional_info", "")),
                "total_amount": float(invoice_data.get("total", 0)),
                "is_paid": bool(invoice_data.get("is_paid", False)),
                "items": [
                    {
                        "name": item["name"],
                        "article": item.get("article", ""),
                        "quantity": float(item["quantity"]),
                        "price": float(item["price"]),
                        "total": float(item["sum"])
                    }
                    for item in invoice_data.get("items", [])
                    if item.get("name") and item.get("quantity") and item.get("price")
                ]
            }
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Invalid invoice update data: {e}")
            if error_callback:
                error_callback(f"Invalid invoice update data: {e}")
            return

        logger.debug(f"Prepared update data for API: {update_data}")

        req_body = json.dumps(update_data)
        self._make_request(
            endpoint=endpoint,
            method='PATCH',
            req_body=req_body,
            headers=self._get_headers(),
            success_callback=lambda req, result: success_callback(result) if success_callback else None,
            error_callback=error_callback
        )

    def get_invoice_details(
            self,
            invoice_id: int,
            success_callback: Optional[Callable[[Any], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """Retrieve detailed information about a specific invoice."""
        endpoint = f"/api/v1/invoices/{invoice_id}"
        logger.debug(f"Fetching invoice details for ID: {invoice_id}")

        self._make_request(
            endpoint=endpoint,
            method='GET',
            headers=self._get_headers(),
            success_callback=lambda req, result: success_callback(result) if success_callback else None,
            error_callback=error_callback
        )

    def update_invoice_status(
            self,
            invoice_id: int,
            is_paid: bool,
            success_callback: Optional[Callable[[Any], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """Update the payment status of an invoice."""
        endpoint = f"/api/v1/invoices/{invoice_id}/status"
        logger.debug(f"Updating invoice ID: {invoice_id} payment status to: {is_paid}")

        data = {"is_paid": is_paid}
        req_body = json.dumps(data)

        self._make_request(
            endpoint=endpoint,
            method='PATCH',
            req_body=req_body,
            headers=self._get_headers(),
            success_callback=lambda req, result: success_callback(result) if success_callback else None,
            error_callback=error_callback
        )

    def delete_invoice(
            self,
            invoice_id: int,
            success_callback: Optional[Callable[[], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """Delete a specific invoice."""
        endpoint = f"/api/v1/invoices/{invoice_id}"
        logger.debug(f"Attempting to delete invoice ID: {invoice_id}")

        self._make_request(
            endpoint=endpoint,
            method='DELETE',
            headers=self._get_headers(),
            success_callback=lambda req, result: success_callback() if success_callback else None,
            error_callback=error_callback
        )


