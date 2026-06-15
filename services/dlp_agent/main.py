from fastapi import HTTPException
from pydantic import BaseModel, Field

from shared.config import Settings
from shared.dlp import hard_filter, mask_pii, validate_readonly_sql
from shared.fastapi_app import create_service_app
from shared.logging_setup import setup_logging

settings = Settings()
logger = setup_logging("dlp-agent", settings.log_level)
app = create_service_app("dlp-agent", log_level=settings.log_level)


class MaskRequest(BaseModel):
    text: str = Field(..., min_length=1)


class MaskResponse(BaseModel):
    original_length: int
    masked: str
    findings: list[str]
    blocked: bool
    block_reason: str = ""


class SQLValidateRequest(BaseModel):
    sql: str


class SQLValidateResponse(BaseModel):
    valid: bool
    message: str


@app.post("/mask", response_model=MaskResponse)
async def mask_text(req: MaskRequest):
    result = hard_filter(req.text)
    logger.info(
        "DLP mask applied",
        extra={"findings": result.findings, "blocked": result.blocked},
    )
    return MaskResponse(
        original_length=len(req.text),
        masked=result.masked,
        findings=result.findings,
        blocked=result.blocked,
        block_reason=result.block_reason,
    )


@app.post("/mask/soft", response_model=MaskResponse)
async def mask_soft(req: MaskRequest):
    result = mask_pii(req.text)
    return MaskResponse(
        original_length=len(req.text),
        masked=result.masked,
        findings=result.findings,
        blocked=False,
    )


@app.post("/validate-sql", response_model=SQLValidateResponse)
async def validate_sql(req: SQLValidateRequest):
    valid, message = validate_readonly_sql(req.sql)
    if not valid:
        logger.warning("SQL validation failed", extra={"reason": message})
        raise HTTPException(status_code=400, detail=message)
    return SQLValidateResponse(valid=True, message=message)
