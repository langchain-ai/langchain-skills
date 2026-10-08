#!/usr/bin/env python3
"""Conservatively compare Harness and Environment tool schemas.

Constraint changes are reported for review rather than treated as semantic
compatibility. External ``$ref`` targets are not loaded or resolved.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class SchemaError(ValueError):
    """Raised when a schema file is malformed."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SchemaError(f"cannot read {path}: {error}") from error


def tool_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict) and "tools" in value:
        value = value["tools"]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise SchemaError("tool file must be a list or an object with a tools list")
    return value


def normalize_tool(value: dict[str, Any]) -> dict[str, Any]:
    function = value.get("function") if isinstance(value.get("function"), dict) else {}
    name = value.get("name") or function.get("name")
    if not isinstance(name, str) or not name:
        raise SchemaError("every tool must have a name")

    def present(*choices: tuple[dict[str, Any], str], default: Any = None) -> Any:
        for source, key in choices:
            if key in source:
                return source[key]
        return default

    input_schema = present(
        (value, "input_schema"),
        (value, "parameters"),
        (function, "parameters"),
    )
    result = {
        "name": name,
        "input": input_schema,
        "output": present((value, "output_schema"), (function, "output_schema")),
        "error": present((value, "error_schema"), (function, "error_schema")),
    }
    for schema_name in ("input", "output", "error"):
        if result[schema_name] is not None:
            validate_schema(result[schema_name], f"tool {name} {schema_name}")
    return result


def validate_schema(value: Any, path: str) -> None:
    """Reject malformed structure used by this conservative comparator."""
    if isinstance(value, bool):
        return
    if not isinstance(value, dict):
        raise SchemaError(f"{path} schema must be an object or boolean")

    schema_type = value.get("type")
    if schema_type is not None:
        valid_types = {"array", "boolean", "integer", "null", "number", "object", "string"}
        types = [schema_type] if isinstance(schema_type, str) else schema_type
        if (
            not isinstance(types, list)
            or not types
            or not all(isinstance(item, str) and item in valid_types for item in types)
            or len(types) != len(set(types))
        ):
            raise SchemaError(f"{path}.type is invalid")

    required = value.get("required")
    if required is not None and (
        not isinstance(required, list)
        or not all(isinstance(item, str) for item in required)
        or len(required) != len(set(required))
    ):
        raise SchemaError(f"{path}.required must be a list of unique strings")

    properties = value.get("properties")
    if properties is not None:
        if not isinstance(properties, dict) or not all(isinstance(name, str) for name in properties):
            raise SchemaError(f"{path}.properties must be an object")
        for name, child in properties.items():
            validate_schema(child, f"{path}.properties.{name}")

    if "items" in value:
        validate_schema(value["items"], f"{path}.items")
    for keyword in ("additionalProperties", "contains", "not", "propertyNames", "unevaluatedItems", "unevaluatedProperties"):
        if keyword in value:
            validate_schema(value[keyword], f"{path}.{keyword}")
    for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
        if keyword in value:
            children = value[keyword]
            if not isinstance(children, list):
                raise SchemaError(f"{path}.{keyword} must be a list")
            for index, child in enumerate(children):
                validate_schema(child, f"{path}.{keyword}[{index}]")

    enum = value.get("enum")
    if enum is not None and (not isinstance(enum, list) or not enum):
        raise SchemaError(f"{path}.enum must be a non-empty list")


def index_tools(value: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw in tool_list(value):
        tool = normalize_tool(raw)
        if tool["name"] in result:
            raise SchemaError(f"duplicate tool: {tool['name']}")
        result[tool["name"]] = tool
    return result


def compare_schema(
    required: Any,
    actual: Any,
    path: str,
    findings: list[dict[str, str]],
    additions: list[dict[str, str]],
    input_schema: bool,
) -> None:
    if isinstance(required, bool) or isinstance(actual, bool):
        if required != actual:
            findings.append(
                {"path": path, "issue": "boolean_schema_changed", "required": repr(required), "actual": repr(actual)}
            )
        return
    if required is None:
        return
    if not isinstance(required, dict) or not isinstance(actual, dict):
        if required != actual:
            findings.append(
                {"path": path, "issue": "value_changed", "required": repr(required), "actual": repr(actual)}
            )
        return

    required_type = required.get("type")
    actual_type = actual.get("type")
    if required_type != actual_type:
        findings.append(
            {"path": f"{path}.type", "issue": "type_changed", "required": str(required_type), "actual": str(actual_type)}
        )

    required_enum = required.get("enum")
    actual_enum = actual.get("enum")
    if isinstance(required_enum, list):
        required_values = {json.dumps(value, sort_keys=True, separators=(",", ":")) for value in required_enum}
        actual_values = (
            {json.dumps(value, sort_keys=True, separators=(",", ":")) for value in actual_enum}
            if isinstance(actual_enum, list)
            else set()
        )
        if required_values != actual_values:
            findings.append(
                {"path": f"{path}.enum", "issue": "enum_changed", "required": repr(required_enum), "actual": repr(actual_enum)}
            )
    elif actual_enum is not None:
        findings.append(
            {"path": f"{path}.enum", "issue": "enum_changed", "required": "<absent>", "actual": repr(actual_enum)}
        )

    strict_keywords = {
        "$ref",
        "additionalProperties",
        "allOf",
        "anyOf",
        "const",
        "contains",
        "dependentRequired",
        "dependentSchemas",
        "else",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "if",
        "maxContains",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minContains",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "multipleOf",
        "not",
        "oneOf",
        "pattern",
        "patternProperties",
        "prefixItems",
        "propertyNames",
        "then",
        "unevaluatedItems",
        "unevaluatedProperties",
        "uniqueItems",
    }
    for keyword in sorted(strict_keywords):
        if keyword not in required and keyword not in actual:
            continue
        required_value = required.get(keyword, "<absent>")
        actual_value = actual.get(keyword, "<absent>")
        if required_value != actual_value:
            findings.append(
                {
                    "path": f"{path}.{keyword}",
                    "issue": "constraint_changed",
                    "required": repr(required_value),
                    "actual": repr(actual_value),
                }
            )

    annotations = {
        "$comment",
        "$id",
        "$schema",
        "default",
        "deprecated",
        "description",
        "examples",
        "readOnly",
        "title",
        "writeOnly",
    }
    handled = {"type", "enum", "required", "properties", "items"} | strict_keywords | annotations
    for keyword in sorted((set(required) | set(actual)) - handled):
        if required.get(keyword, "<absent>") != actual.get(keyword, "<absent>"):
            findings.append(
                {
                    "path": f"{path}.{keyword}",
                    "issue": "unknown_constraint_changed",
                    "required": repr(required.get(keyword, "<absent>")),
                    "actual": repr(actual.get(keyword, "<absent>")),
                }
            )

    required_required = set(required.get("required", []))
    actual_required = set(actual.get("required", []))
    if required_required != actual_required:
        findings.append(
            {
                "path": f"{path}.required",
                "issue": "required_fields_changed",
                "required": repr(sorted(required_required)),
                "actual": repr(sorted(actual_required)),
            }
        )

    required_properties = required.get("properties", {})
    actual_properties = actual.get("properties", {})
    if isinstance(required_properties, dict):
        if not isinstance(actual_properties, dict):
            actual_properties = {}
        for name, child in required_properties.items():
            if name not in actual_properties:
                findings.append(
                    {"path": f"{path}.properties.{name}", "issue": "property_missing", "required": "present", "actual": "missing"}
                )
            else:
                compare_schema(
                    child,
                    actual_properties[name],
                    f"{path}.properties.{name}",
                    findings,
                    additions,
                    input_schema,
                )
        for name in sorted(set(actual_properties) - set(required_properties)):
            if input_schema and name not in actual_required:
                additions.append(
                    {"path": f"{path}.properties.{name}", "change": "optional_property_added"}
                )
            else:
                findings.append(
                    {
                        "path": f"{path}.properties.{name}",
                        "issue": "property_added",
                        "required": "missing",
                        "actual": "present",
                    }
                )

    if "items" in required or "items" in actual:
        if "items" not in actual:
            findings.append(
                {"path": f"{path}.items", "issue": "items_schema_missing", "required": "present", "actual": "missing"}
            )
        elif "items" not in required:
            findings.append(
                {"path": f"{path}.items", "issue": "items_schema_added", "required": "missing", "actual": "present"}
            )
        else:
            compare_schema(
                required["items"],
                actual["items"],
                f"{path}.items",
                findings,
                additions,
                input_schema,
            )


def compare(required_path: Path, actual_path: Path) -> dict[str, Any]:
    required = index_tools(load_json(required_path))
    actual = index_tools(load_json(actual_path))
    findings: list[dict[str, str]] = []
    additions: list[dict[str, str]] = []

    for name in sorted(set(actual) - set(required)):
        additions.append({"path": f"tools.{name}", "change": "tool_added"})

    for name, tool in required.items():
        if name not in actual:
            findings.append(
                {"path": f"tools.{name}", "issue": "tool_missing", "required": "present", "actual": "missing"}
            )
            continue
        for schema_name in ("input", "output", "error"):
            if (tool[schema_name] is None) != (actual[name][schema_name] is None):
                findings.append(
                    {
                        "path": f"tools.{name}.{schema_name}",
                        "issue": "schema_presence_changed",
                        "required": "present" if tool[schema_name] is not None else "missing",
                        "actual": "present" if actual[name][schema_name] is not None else "missing",
                    }
                )
            elif tool[schema_name] is not None:
                compare_schema(
                    tool[schema_name],
                    actual[name][schema_name],
                    f"tools.{name}.{schema_name}",
                    findings,
                    additions,
                    schema_name == "input",
                )

    return {
        "compatible": not findings,
        "required_tools": sorted(required),
        "actual_tools": sorted(actual),
        "additions": additions,
        "findings": findings,
        "limitations": [
            "external JSON Schema $ref targets are not resolved",
            "constraint changes are reported conservatively and require review",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("required", type=Path, help="Harness tool schema JSON")
    parser.add_argument("actual", type=Path, help="Environment tool schema JSON")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = compare(args.required, args.actual)
    except (OSError, SchemaError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    try:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
    except OSError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0 if report["compatible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
