from __future__ import annotations

import structlog
from src.config import settings

try:
    from twilio.base.exceptions import TwilioException  # type: ignore
    from twilio.rest import Client  # type: ignore
    _TWILIO_IMPORT_ERROR: Exception | None = None
except ModuleNotFoundError as exc:
    TwilioException = Exception  # type: ignore
    Client = None  # type: ignore
    _TWILIO_IMPORT_ERROR = exc


class TwilioService:
    """
    Thin wrapper around the Twilio REST client for sending SMS notifications.

    Lazily initialises the underlying client and no-ops when credentials are absent.
    """

    def __init__(self) -> None:
        self.logger = structlog.get_logger(__name__)
        self._enabled = all(
            [
                settings.twilio_account_sid,
                settings.twilio_auth_token,
                settings.twilio_from_number,
                Client is not None,
            ]
        )
        self._client: Client | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _get_client(self) -> Client:
        if not self._enabled:
            raise RuntimeError("Twilio credentials are not configured.")
        if Client is None:
            raise RuntimeError("Twilio SDK is not installed.") from _TWILIO_IMPORT_ERROR
        if self._client is None:
            self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        return self._client

    def send_sms(self, to_number: str, body: str) -> tuple[bool, str | None]:
        if not self._enabled:
            self.logger.warning("twilio_sms_skipped", reason="credentials_missing")
            return False, "Twilio credentials are not configured."

        if not to_number:
            self.logger.warning("twilio_sms_skipped", reason="missing_destination_number")
            return False, "Missing destination phone number."

        try:
            client = self._get_client()
            message = client.messages.create(
                to=to_number,
                from_=settings.twilio_from_number,
                body=body,
            )
            self.logger.info("twilio_sms_sent", sid=message.sid, to=to_number)
            return True, None
        except TwilioException as exc:
            error_text = str(exc)
            self.logger.error("twilio_sms_failed", to=to_number, error=error_text)
            return False, error_text


