
from unittest.mock import Mock, patch

import httpx

from django.test import SimpleTestCase

from rest_framework import status
from rest_framework.test import APITestCase

from inspector.models import Application, Specification

from inspector.services.ai_client import (
    AIClient,
    AIServiceConnectionError,
    AIServiceResponseError,
)

from inspector.services.openapi_converter import (
    OpenAPIConversionError,
    convert_openapi_to_ai_context,
)


# ============================================================
# OpenAPI Converter Tests
# ============================================================

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


# ============================================================
# AI Client Tests
# ============================================================

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

        test_results = [
            {"status_code": 500, "success": False}
        ]

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
            AIClient(
                base_url="http://localhost:8000",
                timeout=0,
            )


# ============================================================
# AI Endpoint Integration Tests
# ============================================================

class AIEndpointTests(APITestCase):

    def setUp(self):
        self.user = self.create_user("owner@example.com")
        self.client.force_authenticate(user=self.user)

        self.application = Application.objects.create(
            owner=self.user,
            name="Test Application",
            description="Application for AI tests",
        )

        self.document = {
            "openapi": "3.0.3",
            "info": {
                "title": "Users API",
                "version": "1.0.0",
            },
            "servers": [
                {"url": "https://example.com"}
            ],
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {
                            "200": {
                                "description": "Successful response"
                            }
                        },
                    }
                }
            },
        }

        self.specification = Specification.objects.create(
            application=self.application,
            name="Users Specification",
            description="Users API specification",
            api_version="1.0.0",
            openapi_version="3.0.3",
            document=self.document,
        )

        self.generate_url = (
            f"/api/specifications/{self.specification.pk}/"
            "ai/generate-tests/"
        )

        self.analysis_url = (
            f"/api/specifications/{self.specification.pk}/"
            "ai/analyze-results/"
        )

    def create_user(self, email):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            email=email,
            password="TestPassword123!",
            is_active=True,
        )

    @patch("inspector.views.AIClient")
    def test_generate_tests_endpoint(self, mock_client_class):
        mock_client = mock_client_class.return_value

        mock_client.generate_tests.return_value = {
            "test_cases": [
                {
                    "name": "Get users",
                    "description": "Retrieve all users",
                }
            ]
        }

        response = self.client.post(
            self.generate_url,
            {
                "instructions": "Generate positive tests",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertIn("test_cases", response.data)

        mock_client.generate_tests.assert_called_once()

        call_kwargs = (
            mock_client.generate_tests.call_args.kwargs
        )

        self.assertEqual(
            call_kwargs["api_context"]["name"],
            "Users API",
        )

        self.assertEqual(
            call_kwargs["instructions"],
            "Generate positive tests",
        )

    @patch("inspector.views.AIClient")
    def test_analyze_results_endpoint(self, mock_client_class):
        mock_client = mock_client_class.return_value

        mock_client.analyze_results.return_value = {
            "summary": "All tests analyzed",
            "findings": [],
        }

        response = self.client.post(
            self.analysis_url,
            {
                "test_results": [
                    {
                        "status_code": 200,
                        "success": True,
                    }
                ],
                "instructions": "Analyze results",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["summary"],
            "All tests analyzed",
        )

        mock_client.analyze_results.assert_called_once()

    @patch("inspector.views.AIClient")
    def test_sensitive_data_is_removed_before_analysis(
        self,
        mock_client_class,
    ):
        mock_client = mock_client_class.return_value

        mock_client.analyze_results.return_value = {
            "summary": "Analysis completed",
            "findings": [],
        }

        test_results = [
            {
                "status_code": 200,
                "success": True,
                "headers": {
                    "Authorization": "Bearer secret-token",
                    "Content-Type": "application/json",
                },
                "body": {
                    "username": "test-user",
                    "password": "secret-password",
                    "access_token": "secret-access-token",
                    "profile": {
                        "client_secret": "hidden-secret",
                        "name": "Test User",
                    },
                },
            }
        ]

        response = self.client.post(
            self.analysis_url,
            {
                "test_results": test_results,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        sent_results = (
            mock_client.analyze_results.call_args.kwargs[
                "test_results"
            ]
        )

        self.assertEqual(
            sent_results[0]["headers"],
            {
                "Content-Type": "application/json",
            },
        )

        self.assertEqual(
            sent_results[0]["body"],
            {
                "username": "test-user",
                "profile": {
                    "name": "Test User",
                },
            },
        )

    def test_generation_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.generate_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_analysis_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.analysis_url,
            {
                "test_results": [],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    @patch("inspector.views.AIClient")
    def test_user_cannot_access_another_users_specification(
        self,
        mock_client_class,
    ):
        another_user = self.create_user(
            "another@example.com"
        )

        another_application = Application.objects.create(
            owner=another_user,
            name="Another Application",
        )

        another_specification = Specification.objects.create(
            application=another_application,
            name="Private Specification",
            api_version="1.0.0",
            openapi_version="3.0.3",
            document=self.document,
        )

        url = (
            f"/api/specifications/{another_specification.pk}/"
            "ai/generate-tests/"
        )

        response = self.client.post(
            url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        mock_client_class.assert_not_called()

    @patch("inspector.views.AIClient")
    def test_ai_connection_error_returns_503(
        self,
        mock_client_class,
    ):
        mock_client = mock_client_class.return_value

        mock_client.generate_tests.side_effect = (
            AIServiceConnectionError(
                "Connection refused"
            )
        )

        response = self.client.post(
            self.generate_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @patch("inspector.views.AIClient")
    def test_invalid_ai_response_returns_502(
        self,
        mock_client_class,
    ):
        mock_client = mock_client_class.return_value

        mock_client.generate_tests.side_effect = (
            AIServiceResponseError(
                "Invalid response"
            )
        )

        response = self.client.post(
            self.generate_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_502_BAD_GATEWAY,
        )

    def test_analysis_rejects_invalid_test_results(self):
        response = self.client.post(
            self.analysis_url,
            {
                "test_results": "not-a-list",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_generation_rejects_long_instructions(self):
        response = self.client.post(
            self.generate_url,
            {
                "instructions": "x" * 4001,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
