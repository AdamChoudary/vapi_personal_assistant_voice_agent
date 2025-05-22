import logging
import requests

from fastapi import HTTPException

from src.config.settings import VapiSettings
from src.models.domain.call import CallRequest, CallResponse
from src.utils.helpers import handle_service_error

logger = logging.getLogger(__name__)

class CallService:
    def __init__(self):
        try:
            self.settings = VapiSettings()
            if not self.settings.vapi_api_key:
                logger.error("Vapi API key is not configured")
                raise ValueError(
                    "Vapi API key is not configured. Please set VAPI_API_KEY environment variable or add it to .env file.")
        except Exception as e:
            logger.error(f"Failed to load Vapi API settings: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize call service. Check environment variables."
            )
    
    async def make_call(self, call_data: CallRequest) -> CallResponse:
        try:
            request_data = {
                "assistantId": call_data.assistant_id,
                "phoneNumberId": call_data.phone_number_id,
                "customer": {
                    "number": call_data.customer.number
                }
            }

            response = requests.post(
                f"{self.settings.vapi_api_url}/call",
                headers={
                    "Authorization": f"Bearer {self.settings.vapi_api_key}"
                },
                json=request_data,
            )

            response.raise_for_status()
            response_data = response.json()
            
            logger.info(f"Response data: {response_data}")
            logger.info(f"Successfully created call with ID: {response_data.get('id')}")

            return CallResponse(
                call_id=response_data.get("id"),
                status=response_data.get("status", "unknown")
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to make call via Vapi API: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                error_detail = f"Vapi API error: {e.response.text}"
            else:
                status_code = 500
                error_detail = f"Failed to connect to Vapi API: {str(e)}"
            
            raise HTTPException(status_code=status_code, detail=error_detail)
        except Exception as e:
            handle_service_error(e, "call_service", "make_call")
