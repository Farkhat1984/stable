from typing import Dict, Any, Optional, Callable
from functools import partial
from .base_api_controller import BaseAPIController
import logging
from urllib.parse import urlencode, quote
from datetime import datetime

logger = logging.getLogger(__name__)


class HistoryAPIController(BaseAPIController):
    def __init__(self, base_url: str = "http://localhost:8000", auth_controller: Optional[Any] = None):
        super().__init__(base_url=base_url, auth_controller=auth_controller)

    def _prepare_filters(self, filters: Optional[Dict[str, Any]]) -> str:
        """
        Подготовка фильтров для URL с правильным кодированием.
        """
        if not filters:
            return ""

        encoded_filters = {}
        for key, value in filters.items():
            if value is not None:
                # Особая обработка для дат
                if isinstance(value, datetime):
                    encoded_filters[key] = value.isoformat()
                # Особая обработка для булевых значений
                elif isinstance(value, bool):
                    encoded_filters[key] = str(value).lower()
                # Особая обработка для чисел
                elif isinstance(value, (int, float)):
                    encoded_filters[key] = str(value)
                else:
                    encoded_filters[key] = str(value)

        if encoded_filters:
            return "?" + urlencode(encoded_filters, quote_via=quote)
        return ""

    def get_invoices(
            self,
            success_callback: Optional[Callable[[Any], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None,
            filters: Optional[Dict[str, Any]] = None
    ):
        """Получение списка накладных с опциональными фильтрами."""
        endpoint = "/api/v1/invoices/"

        # Добавляем фильтры к URL
        query_string = self._prepare_filters(filters)
        if query_string:
            endpoint += query_string
            logger.debug(f"Fetching invoices with filters: {filters}")
            logger.debug(f"Constructed endpoint: {endpoint}")

        def success_wrapper(req, result):
            """Обработка успешного ответа с проверкой формата"""
            try:
                if success_callback:
                    if isinstance(result, (list, dict)):
                        success_callback(result)
                    else:
                        logger.error(f"Unexpected response format: {result}")
                        if error_callback:
                            error_callback("Unexpected response format from server")
            except Exception as e:
                logger.error(f"Error in success callback: {e}")
                if error_callback:
                    error_callback(str(e))

        self._make_request(
            endpoint=endpoint,
            method='GET',
            headers=self._get_headers(),
            success_callback=success_wrapper,
            error_callback=error_callback
        )

    def delete_invoice(
            self,
            invoice_id: int,
            success_callback: Optional[Callable[[], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """Удаление конкретной накладной."""
        if not isinstance(invoice_id, int):
            if error_callback:
                error_callback("Invalid invoice ID")
            return

        endpoint = f"/api/v1/invoices/{invoice_id}"
        logger.debug(f"Attempting to delete invoice with ID: {invoice_id}")

        self._make_request(
            endpoint=endpoint,
            method='DELETE',
            headers=self._get_headers(),
            success_callback=lambda req, result: success_callback() if success_callback else None,
            error_callback=error_callback
        )

    def get_invoice_details(
            self,
            invoice_id: int,
            success_callback: Optional[Callable[[Any], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """Получение детальной информации о конкретной накладной."""
        if not isinstance(invoice_id, int):
            if error_callback:
                error_callback("Invalid invoice ID")
            return

        endpoint = f"/api/v1/invoices/{invoice_id}"
        logger.debug(f"Fetching details for invoice ID: {invoice_id}")

        def success_wrapper(req, result):
            """Обработка успешного ответа с проверкой формата"""
            try:
                if success_callback:
                    if isinstance(result, dict):
                        success_callback(result)
                    else:
                        logger.error(f"Unexpected response format: {result}")
                        if error_callback:
                            error_callback("Unexpected response format from server")
            except Exception as e:
                logger.error(f"Error in success callback: {e}")
                if error_callback:
                    error_callback(str(e))

        self._make_request(
            endpoint=endpoint,
            method='GET',
            headers=self._get_headers(),
            success_callback=success_wrapper,
            error_callback=error_callback
        )