import logging
from typing import TypeVar, Type, Callable

from fastapi import HTTPException
from pydantic import ValidationError

from src.models.base import SessionLocal
from src.models.domain.request import VapiRequest
from src.models.domain.tool import ValidatedToolCall
from src.utils.helpers import parse_json_args

logger = logging.getLogger(__name__)

T = TypeVar('T')

async def get_db() -> SessionLocal:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_validated_tool_call(function_name: str, args_model: Type[T]) -> Callable[[VapiRequest], ValidatedToolCall[T]]:
    def validate_dependency(request: VapiRequest) -> ValidatedToolCall[T]:
        logger.info(f"Validating tool call for function: {function_name}")
        
        try:
            for tool_call in request.message.toolCalls:
                if tool_call.function.name == function_name:
                    args_dict = parse_json_args(tool_call.function.arguments)
                    validated_args = args_model(**args_dict)
                    
                    return ValidatedToolCall(
                        tool_call_id=tool_call.id,
                        args=validated_args
                    )
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid Request: Expected '{function_name}' function call"
            )
            
        except ValidationError as e:
            logger.error(f"Validation error for {function_name}: {str(e)}")
            raise HTTPException(
                status_code=422,
                detail=f"Invalid arguments for {function_name}: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error validating {function_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return validate_dependency