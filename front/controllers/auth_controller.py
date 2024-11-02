# controllers/auth_api_controller.py
import json
from functools import partial
from typing import Optional, Callable, Any
from kivy.network.urlrequest import UrlRequest
from .base_api_controller import BaseAPIController
import logging

logger = logging.getLogger(__name__)


class AuthAPIController(BaseAPIController):
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url=base_url)
        self.token: Optional[str] = None
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def _handle_login_success(self, req: UrlRequest, result: Any, success_callback: Optional[Callable[[Any], None]]):
        """Handle successful login."""
        self.token = result.get('access_token')
        logger.info("Login successful. Token obtained.")
        if success_callback:
            success_callback(result)

    def _handle_register_success(self, req: UrlRequest, result: Any, success_callback: Optional[Callable[[Any], None]]):
        """Handle successful registration."""
        self.token = result.get('access_token')
        logger.info("Registration successful. Token obtained.")
        if success_callback:
            success_callback(result)

    def login(
            self,
            username: str,
            password: str,
            success_callback: Optional[Callable[[Any], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Asynchronous login via API.
        """
        login_url = "/api/v1/auth/token"
        form_data = f"username={username}&password={password}"
        logger.debug(f"Attempting to login user: {username}")

        self._make_request(
            endpoint=login_url,
            method='POST',
            req_body=form_data,
            headers=self.headers,
            success_callback=partial(self._handle_login_success, success_callback=success_callback),
            error_callback=error_callback
        )

    def register(
            self,
            user_data: dict,
            success_callback: Optional[Callable[[Any], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Asynchronous registration via API.
        """
        register_url = "/api/v1/auth/register"
        logger.debug(f"Attempting to register user with data: {user_data}")

        req_body = json.dumps(user_data)
        headers = self._get_headers(content_type="application/json")

        self._make_request(
            endpoint=register_url,
            method='POST',
            req_body=req_body,
            headers=headers,
            success_callback=partial(self._handle_register_success, success_callback=success_callback),
            error_callback=error_callback
        )

    def get_user_profile(
            self,
            success_callback: Optional[Callable[[Any], None]] = None,
            error_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Retrieve user profile.
        """
        if not self.token:
            logger.warning("Attempted to fetch user profile without a token.")
            if error_callback:
                error_callback("No authentication token available")
            return

        profile_url = "/api/v1/auth/me"
        logger.debug("Fetching user profile.")

        self._make_request(
            endpoint=profile_url,
            method='GET',
            headers=self._get_headers(),
            success_callback=lambda req, result: success_callback(result) if success_callback else None,
            error_callback=error_callback
        )
