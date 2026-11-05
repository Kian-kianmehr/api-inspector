
from typing import Any


SUPPORTED_METHODS = {
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
}


class OpenAPIConversionError(ValueError):
    """Raised when an OpenAPI document cannot be converted safely."""


def _resolve_pointer(document: dict, reference: str) -> dict:
    if not reference.startswith("#/"):
        raise OpenAPIConversionError(
            f"External references are not supported: {reference}"
        )

    current: Any = document

    for part in reference[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")

        if not isinstance(current, dict) or part not in current:
            raise OpenAPIConversionError(
                f"Unresolved OpenAPI reference: {reference}"
            )

        current = current[part]

    if not isinstance(current, dict):
        raise OpenAPIConversionError(
            f"Reference does not point to an object: {reference}"
        )

    return current


def _resolve_schema(
    schema: dict | None,
    document: dict,
    reference_stack: set[str] | None = None,
) -> dict:
    if not isinstance(schema, dict):
        return {}

    reference_stack = reference_stack or set()
    resolved = dict(schema)

    reference = resolved.pop("$ref", None)

    if reference:
        if reference in reference_stack:
            return {}

        referenced_schema = _resolve_pointer(document, reference)

        resolved_reference = _resolve_schema(
            referenced_schema,
            document,
            reference_stack | {reference},
        )

        resolved_reference.update(resolved)
        resolved = resolved_reference

    if "allOf" in resolved:
        merged_properties = {}
        merged_required = []

        for item in resolved.pop("allOf"):
            item_schema = _resolve_schema(
                item,
                document,
                reference_stack,
            )

            merged_properties.update(
                item_schema.get("properties", {})
            )

            merged_required.extend(
                item_schema.get("required", [])
            )

        merged_properties.update(
            resolved.get("properties", {})
        )

        merged_required.extend(
            resolved.get("required", [])
        )

        if merged_properties:
            resolved["properties"] = merged_properties

        if merged_required:
            resolved["required"] = list(set(merged_required))

    return resolved


def _schema_type(schema: dict) -> str:
    data_type = schema.get("type", "object" if "properties" in schema else "unknown")

    if isinstance(data_type, list):
        data_type = next(
            (item for item in data_type if item != "null"),
            "unknown",
        )

    return str(data_type)


def _extract_fields(
    schema: dict | None,
    document: dict,
    reference_stack: set[str] | None = None,
) -> list[dict]:
    schema = _resolve_schema(
        schema,
        document,
        reference_stack,
    )

    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    if not isinstance(properties, dict):
        return []

    fields = []

    for name, property_schema in properties.items():
        if not isinstance(property_schema, dict):
            continue

        resolved_property = _resolve_schema(
            property_schema,
            document,
            reference_stack,
        )

        data_type = _schema_type(resolved_property)

        nested_schema = resolved_property

        if data_type == "array":
            nested_schema = _resolve_schema(
                resolved_property.get("items"),
                document,
                reference_stack,
            )

        nested_fields = _extract_fields(
            nested_schema,
            document,
            reference_stack,
        )

        fields.append({
            "name": name,
            "data_type": data_type,
            "required": name in required_fields,
            "description": resolved_property.get("description", ""),
            "fields": nested_fields,
        })

    return fields


def _extract_parameter(
    parameter: dict,
) -> dict | None:
    location = parameter.get("in")

    if location not in {"path", "query", "header", "cookie"}:
        return None

    return {
        "name": parameter.get("name", ""),
        "location": location,
        "required": (
            True if location == "path"
            else bool(parameter.get("required", False))
        ),
        "description": parameter.get("description", ""),
    }


def _extract_parameters(
    path_item: dict,
    operation: dict,
) -> list[dict]:
    merged = {}

    for parameter in path_item.get("parameters", []):
        if isinstance(parameter, dict):
            key = (parameter.get("name"), parameter.get("in"))
            merged[key] = parameter

    for parameter in operation.get("parameters", []):
        if isinstance(parameter, dict):
            key = (parameter.get("name"), parameter.get("in"))
            merged[key] = parameter

    parameters = []

    for parameter in merged.values():
        extracted = _extract_parameter(parameter)

        if extracted:
            parameters.append(extracted)

    return parameters


def _extract_request_body(
    request_body: dict | None,
    document: dict,
) -> dict | None:
    if not isinstance(request_body, dict):
        return None

    request_body = _resolve_schema(
        request_body,
        document,
    )

    content = request_body.get("content", {})

    if not isinstance(content, dict) or not content:
        return {
            "content_type": "application/json",
            "required": bool(request_body.get("required", False)),
            "description": request_body.get("description", ""),
            "fields": [],
        }

    content_type, media = next(iter(content.items()))

    if not isinstance(media, dict):
        media = {}

    schema = media.get("schema", {})

    return {
        "content_type": content_type,
        "required": bool(request_body.get("required", False)),
        "description": request_body.get("description", ""),
        "fields": _extract_fields(schema, document),
    }


def _extract_responses(
    responses: dict | None,
    document: dict,
) -> list[dict]:
    if not isinstance(responses, dict):
        return []

    extracted_responses = []

    for status_code, response in responses.items():
        if not str(status_code).isdigit():
            continue

        if not isinstance(response, dict):
            continue

        response = _resolve_schema(response, document)

        content = response.get("content", {})

        content_type = "application/json"
        fields = []

        if isinstance(content, dict) and content:
            content_type, media = next(iter(content.items()))

            if isinstance(media, dict):
                fields = _extract_fields(
                    media.get("schema", {}),
                    document,
                )

        extracted_responses.append({
            "status_code": int(status_code),
            "content_type": content_type,
            "description": response.get("description", ""),
            "fields": fields,
        })

    return extracted_responses


def convert_openapi_to_ai_context(
    specification: dict,
    specification_name: str = "",
) -> dict:
    """
    Convert an OpenAPI 3.x document into the API Context
    expected by API Inspector AI.
    """

    if not isinstance(specification, dict):
        raise OpenAPIConversionError(
            "OpenAPI document must be a JSON object."
        )

    openapi_version = specification.get("openapi", "")

    if not str(openapi_version).startswith("3."):
        raise OpenAPIConversionError(
            "Only OpenAPI 3.x documents are supported."
        )

    info = specification.get("info", {})

    if not isinstance(info, dict):
        raise OpenAPIConversionError(
            "OpenAPI info section must be an object."
        )

    paths = specification.get("paths", {})

    if not isinstance(paths, dict):
        raise OpenAPIConversionError(
            "OpenAPI paths section must be an object."
        )

    servers = specification.get("servers", [])

    base_url = ""

    if servers and isinstance(servers[0], dict):
        base_url = servers[0].get("url", "")

    api_name = (
        info.get("title")
        or specification_name
        or "Unnamed API"
    )

    api_description = info.get("description", "")

    endpoints = []

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            method = str(method).upper()

            if method not in SUPPORTED_METHODS:
                continue

            if not isinstance(operation, dict):
                continue

            description = (
                operation.get("description")
                or operation.get("summary")
                or ""
            )

            operation_responses = operation.get("responses")
            if not isinstance(operation_responses, dict) or not operation_responses:
                if (
                    isinstance(operation.get("requestBody"), dict)
                    and "responses" in operation["requestBody"]
                ):
                    raise OpenAPIConversionError(
                        f"Responses for {method} {path} must be defined "
                        "at the operation level, alongside requestBody."
                    )

                raise OpenAPIConversionError(
                    f"Operation {method} {path} must define a non-empty "
                    "responses object."
                )

            endpoints.append({
                "path": path,
                "method": method,
                "description": description,
                "parameters": _extract_parameters(
                    path_item,
                    operation,
                ),
                "request_body": _extract_request_body(
                    operation.get("requestBody"),
                    specification,
                ),
                "responses": _extract_responses(
                    operation_responses,
                    specification,
                ),
            })

    return {
        "name": api_name,
        "base_url": base_url,
        "description": api_description,
        "endpoints": endpoints,
    }
