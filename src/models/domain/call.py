from pydantic import BaseModel, Field

class CustomerInfo(BaseModel):
    number: str = Field(..., description="Customer phone number")

class CallRequest(BaseModel):
    assistant_id: str = Field(..., description="ID of the Vapi assistant")
    phone_number_id: str = Field(..., description="ID of the phone number to use")
    customer: CustomerInfo = Field(..., description="Customer information")

class CallResponse(BaseModel):
    call_id: str = Field(..., description="ID of the created call")
    status: str = Field(..., description="Status of the call")
