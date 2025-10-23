from fastapi import APIRouter, Depends, HTTPException

from src.core.deps import get_fontis_client
from src.core.security import verify_api_key
from src.schemas.tools import ContractsTool
from src.services.fontis_client import FontisClient
from src.core.exceptions import FontisAPIError

router = APIRouter(prefix="/tools/contracts", tags=["tools-contracts"])


@router.post("/get-contracts", dependencies=[Depends(verify_api_key)])
async def get_customer_contracts(
    params: ContractsTool,
    fontis: FontisClient = Depends(get_fontis_client)
) -> dict:
    """
    Get customer contracts and service agreements.
    
    Tool ID: 13e223880330066e44c1f2119c0c5aba
    Fontis Endpoint: POST /api/v1/customers/{customerId}/contracts
    Method: GetCustomerContracts
    
    Purpose:
    Retrieve all active and historical service agreements (contracts) associated 
    with a customer's account and delivery stop.
    
    Contract Types:
    - SA: Service Agreement (water-only, month-to-month)
    - Equipment: 12-month rental agreement (auto-renewing)
    
    Business Rules:
    - Water-only customers: Month-to-month, no commitment
    - Equipment rentals: 12-month term, auto-renews annually
    - Early cancellation: $100 or remaining months' balance, whichever is greater
    - All Fontis customers have at least one contract record
    
    AI Usage Guidelines:
    - Use to verify contract type, duration, and expiration
    - Explain renewal status or upcoming expiration
    - Reference authorized signer for service questions
    - NEVER share Document GUIDs or PDF links
    - Documents are internal reference only
    """
    try:
        response = await fontis.get_customer_contracts(
            customer_id=params.customer_id,
            delivery_id=params.delivery_id
        )
        
        if not response.get("success"):
            return {
                "success": False,
                "message": response.get("message", "Failed to retrieve contracts")
            }
        
        contracts = response.get("data", [])
        
        # Format contract information for AI
        formatted_contracts = []
        for contract in contracts:
            contract_type = contract.get("ContractType", "")
            duration = contract.get("Duration", 0)
            
            # Determine contract terms
            if contract_type == "SA":
                terms_description = "Service Agreement - Month-to-month, no commitment"
            elif duration == 12:
                terms_description = "12-month auto-renewing agreement, $100 or remaining balance early termination fee"
            else:
                terms_description = f"{duration}-month agreement"
            
            formatted_contracts.append({
                "contractNumber": contract.get("ContractNumber"),
                "contractType": contract_type,
                "startDate": contract.get("StartingDate"),
                "expirationDate": contract.get("ExpirationDate"),
                "duration": duration,
                "durationUnit": "months",
                "authorizedPerson": contract.get("AuthrorizedPerson"),  # Note: API has typo
                "authorizedTitle": contract.get("AuthorizedTitle"),
                "termsDescription": terms_description,
                "hasDocuments": len(contract.get("Documents", [])) > 0,
                "createdBy": contract.get("CreatedBy")
            })
        
        return {
            "success": True,
            "message": f"Found {len(contracts)} contract(s)",
            "data": formatted_contracts
        }
        
    except FontisAPIError as e:
        raise HTTPException(status_code=500, detail=str(e))

