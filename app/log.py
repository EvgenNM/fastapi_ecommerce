from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

import app.config as conf


logger.add(
    conf.LOGGER_FILE,
    format=conf.LOGGER_FORMAT,
    level=conf.LOGGER_LEVEL,
    rotation=conf.LOGGER_ROTATION,
    retention=conf.LOGGER_RETENTION,
    compression=conf.LOGGER_COMPRESSION,
    enqueue=conf.LOGGER_ENQUEUE
)


async def log_middleware(request: Request, call_next):
    log_id = str(uuid4())
    with logger.contextualize(log_id=log_id):
        try:
            response = await call_next(request)
            status_code = response.status_code
            if status_code in conf.LOGGER_WARNING_LIST_STATUS_CODE:
                logger.warning(
                    f'Request to {request.url.path} failed'
                    f' ({status_code})'
                )
            else:
                logger.info(
                    f'Successfully accessed {request.url.path} ({status_code})'
                )
        except Exception as ex:
            logger.error(f"Request to {request.url.path} failed: {ex}")
            response = JSONResponse(
                content={"success": False},
                status_code=conf.LOGGER_EXCEPTION_STATUS_CODE
            )
        return response
