
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
