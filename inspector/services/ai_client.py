import os
from typing import Any

import httpx


class AIServiceError(Exception):
    """Base exception for AI service communication errors."""


class AIServiceConnectionError(AIServiceError):
    """Raised when the AI service cannot be reached."""


class AIServiceResponseError(AIServiceError):
    """Raised when the AI service returns an invalid response."""


class AIClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (
            base_url or os.getenv(
                "AI_SERVICE_URL",
                "http://127.0.0.1:8000",
            )
        ).rstrip("/")

        configured_timeout = os.getenv(
            "AI_SERVICE_TIMEOUT",
            "30",
        )

        self.timeout = (
            timeout if timeout is not None
            else float(configured_timeout)
        )

        if not self.base_url:
            raise ValueError("AI service URL cannot be empty.")

        if self.timeout <= 0:
            raise ValueError("AI service timeout must be greater than zero.")

    def _post(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self.base_url}/v1/{endpoint}"

        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

        except httpx.TimeoutException as error:
            raise AIServiceConnectionError(
                "The AI service request timed out."
            ) from error

        except httpx.RequestError as error:
            raise AIServiceConnectionError(
                "Could not connect to the AI service."
            ) from error

        except httpx.HTTPStatusError as error:
            raise AIServiceResponseError(
                f"The AI service returned HTTP {error.response.status_code}."
            ) from error

        try:
            result = response.json()
        except ValueError as error:
            raise AIServiceResponseError(
                "The AI service returned invalid JSON."
            ) from error

        if not isinstance(result, dict):
            raise AIServiceResponseError(
                "The AI service response must be a JSON object."
            )

        return result

    def generate_tests(
        self,
        api_context: dict[str, Any],
        instructions: str = "",
    ) -> dict[str, Any]:
        return self._post(
            "test-generation",
            {
                "api_context": api_context,
                "instructions": instructions,
            },
        )

    def analyze_results(
        self,
        api_context: dict[str, Any],
        test_results: list[dict[str, Any]],
        instructions: str = "",
    ) -> dict[str, Any]:
        return self._post(
            "result-analysis",
            {
                "api_context": api_context,
                "test_results": test_results,
                "instructions": instructions,
            },
        )
