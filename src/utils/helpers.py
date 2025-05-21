import json
from typing import Any, Dict, TypeVar
import logging
from fastapi import HTTPException
from typing_extensions import NoReturn

T = TypeVar('T')

def parse_json_args(args: str | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(args, str):
        return json.loads(args)
    return args

def handle_service_error(error: Exception, service_name: str, operation: str, status_code: int = 500) -> NoReturn:
    logger = logging.getLogger(service_name)
    logger.error(f"Error in {service_name} - {operation}: {str(error)}")

    raise HTTPException(
        status_code=status_code,
        detail=f"Operation failed: {operation}. Error: {str(error)}"
    )