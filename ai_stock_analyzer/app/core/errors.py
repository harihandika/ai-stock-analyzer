"""Errors safe to expose to API clients, without provider credentials or payloads."""

from fastapi import HTTPException


class AnalysisError(Exception):
    def __init__(self, code: str, message: str, *, status: int = 502, stage: str = "analyzing"):
        super().__init__(message)
        self.code, self.message, self.status, self.stage = code, message, status, stage


def api_error(code: str, message: str, *, status: int, stage: str, retryable: bool = False):
    return HTTPException(
        status_code=status,
        detail={
            "code": code,
            "message": message,
            "stage": stage,
            "retryable": retryable,
        },
    )
