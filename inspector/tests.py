
from django.test import SimpleTestCase

from inspector.services.openapi_converter import (
    OpenAPIConversionError,
    convert_openapi_to_ai_context,
)


class OpenAPIConverterTests(SimpleTestCase):

    def setUp(self):
        self.document = {
            "openapi": "3.0.3",
            "info": {
                "title": "Users API",
                "version": "1.0.0",
                "description": "Users management API",
            },
            "servers": [
                {"url": "https://example.com/api"}
            ],
            "paths": {
                "/users/{id}": {
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "description": "User ID",
                            "schema": {"type": "integer"},
                        }
                    ],
                    "get": {
                        "summary": "Get a user",
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/User"
                                        }
                                    }
                                },
                            }
                        },
                    },
                },
                "/users": {
                    "post": {
                        "summary": "Create a user",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/User"
                                    }
                                }
                            },
                        },
                        "responses": {
                            "201": {
                                "description": "Created"
                            }
                        },
                    }
                },
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "required": ["name", "email"],
                        "properties": {
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "age": {"type": "integer"},
                        },
                    }
                }
            },
        }

    def test_converts_api_metadata(self):
        result = convert_openapi_to_ai_context(self.document)

        self.assertEqual(result["name"], "Users API")
        self.assertEqual(
            result["base_url"],
            "https://example.com/api",
        )
        self.assertEqual(len(result["endpoints"]), 2)

    def test_converts_path_parameters(self):
        result = convert_openapi_to_ai_context(self.document)

        endpoint = result["endpoints"][0]

        self.assertEqual(endpoint["path"], "/users/{id}")
        self.assertEqual(endpoint["method"], "GET")
        self.assertEqual(
            endpoint["parameters"][0]["name"],
            "id",
        )
        self.assertTrue(
            endpoint["parameters"][0]["required"]
        )

    def test_resolves_schema_references(self):
        result = convert_openapi_to_ai_context(self.document)

        endpoint = result["endpoints"][1]
        fields = endpoint["request_body"]["fields"]

        self.assertEqual(
            [field["name"] for field in fields],
            ["name", "email", "age"],
        )

        self.assertTrue(fields[0]["required"])
        self.assertTrue(fields[1]["required"])
        self.assertFalse(fields[2]["required"])

    def test_converts_documented_response_codes(self):
        result = convert_openapi_to_ai_context(self.document)

        endpoint = result["endpoints"][0]

        self.assertEqual(
            endpoint["responses"][0]["status_code"],
            200,
        )

    def test_rejects_unsupported_openapi_version(self):
        document = {
            "openapi": "2.0",
            "info": {"title": "Old API"},
            "paths": {},
        }

        with self.assertRaises(OpenAPIConversionError):
            convert_openapi_to_ai_context(document)

    def test_ignores_unsupported_http_methods(self):
        self.document["paths"]["/users"]["options"] = {
            "summary": "Options"
        }

        result = convert_openapi_to_ai_context(self.document)

        methods = [
            endpoint["method"]
            for endpoint in result["endpoints"]
        ]

        self.assertNotIn("OPTIONS", methods)

from unittest.mock import Mock, patch

import httpx

from inspector.services.ai_client import (
    AIClient,
    AIServiceConnectionError,
    AIServiceResponseError,
)


class AIClientTests(SimpleTestCase):
    def setUp(self):
        self.client = AIClient(
            base_url="http://127.0.0.1:8000/",
            timeout=5,
        )
        self.api_context = {
            "name": "Users API",
            "base_url": "https://example.com",
            "description": "",
            "endpoints": [],
        }

    @patch("inspector.services.ai_client.httpx.post")
    def test_generate_tests_sends_expected_request(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"test_cases": []}
        mock_post.return_value = mock_response

        result = self.client.generate_tests(
            self.api_context,
            instructions="Generate positive tests",
        )

        self.assertEqual(result, {"test_cases": []})
        mock_post.assert_called_once_with(
            "http://127.0.0.1:8000/v1/test-generation",
            json={
                "api_context": self.api_context,
                "instructions": "Generate positive tests",
            },
            timeout=5,
        )

    @patch("inspector.services.ai_client.httpx.post")
    def test_analyze_results_sends_expected_request(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"summary": "Analysis"}
        mock_post.return_value = mock_response
        test_results = [{"status_code": 500, "success": False}]

        result = self.client.analyze_results(
            self.api_context,
            test_results,
        )

        self.assertEqual(result, {"summary": "Analysis"})
        mock_post.assert_called_once_with(
            "http://127.0.0.1:8000/v1/result-analysis",
            json={
                "api_context": self.api_context,
                "test_results": test_results,
                "instructions": "",
            },
            timeout=5,
        )

    @patch("inspector.services.ai_client.httpx.post")
    def test_connection_error_is_translated(self, mock_post):
        mock_post.side_effect = httpx.ConnectError(
            "Connection refused",
            request=httpx.Request(
                "POST",
                "http://127.0.0.1:8000/v1/test-generation",
            ),
        )

        with self.assertRaises(AIServiceConnectionError):
            self.client.generate_tests(self.api_context)

    @patch("inspector.services.ai_client.httpx.post")
    def test_timeout_error_is_translated(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException(
            "Request timed out"
        )

        with self.assertRaises(AIServiceConnectionError):
            self.client.generate_tests(self.api_context)

    @patch("inspector.services.ai_client.httpx.post")
    def test_http_error_is_translated(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = (
            httpx.HTTPStatusError(
                "Service unavailable",
                request=httpx.Request(
                    "POST",
                    "http://127.0.0.1:8000/v1/test-generation",
                ),
                response=httpx.Response(503),
            )
        )
        mock_post.return_value = mock_response

        with self.assertRaises(AIServiceResponseError):
            self.client.generate_tests(self.api_context)

    @patch("inspector.services.ai_client.httpx.post")
    def test_invalid_json_response_is_rejected(self, mock_post):
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        with self.assertRaises(AIServiceResponseError):
            self.client.generate_tests(self.api_context)

    @patch("inspector.services.ai_client.httpx.post")
    def test_non_object_response_is_rejected(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = ["unexpected", "list"]
        mock_post.return_value = mock_response

        with self.assertRaises(AIServiceResponseError):
            self.client.generate_tests(self.api_context)

    def test_non_positive_timeout_is_rejected(self):
        with self.assertRaises(ValueError):
            AIClient(base_url="http://localhost:8000", timeout=0)
