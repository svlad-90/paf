'''
YAML case configuration support for PAF.
'''

import copy
import json
import os
import re

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from paf.paf_impl import logger


DOCKER_IMAGE_SCHEMA = {
    "type": "object",
    "required": ["image"],
    "properties": {
        "image": {"type": "string", "minLength": 1},
        "dockerfile": {"type": "string", "minLength": 1},
        "context": {"type": "string", "minLength": 1},
        "target": {"type": "string", "minLength": 1},
        "network": {"type": "string", "minLength": 1},
        "build_args": {
            "type": "object",
            "additionalProperties": {
                "type": ["string", "number", "boolean"],
            },
        },
    },
    "additionalProperties": False,
}


DOCKER_CONTAINER_SCHEMA = {
    "type": "object",
    "required": ["image"],
    "properties": {
        "image": {"type": "string", "minLength": 1},
        "name": {"type": "string"},
        "workdir": {"type": "string"},
        "user": {"type": "string"},
        "privileged": {"type": "boolean"},
        "env": {
            "type": "object",
            "additionalProperties": {
                "type": ["string", "number", "boolean"],
            },
        },
        "mounts": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "target"],
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "mode": {"enum": ["ro", "rw"]},
                },
                "additionalProperties": False,
            },
        },
        "ports": {
            "type": "array",
            "items": {
                "oneOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "required": ["host", "container"],
                        "properties": {
                            "host": {"type": ["string", "number"]},
                            "container": {"type": ["string", "number"]},
                            "protocol": {"enum": ["tcp", "udp"]},
                        },
                        "additionalProperties": False,
                    },
                ],
            },
        },
        "devices": {
            "type": "array",
            "items": {"type": "string"},
        },
        "extra_args": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}


BUILTIN_CASE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "docker": {
            "type": "object",
            "properties": {
                "images": {
                    "type": "object",
                    "additionalProperties": DOCKER_IMAGE_SCHEMA,
                },
                "containers": {
                    "type": "object",
                    "additionalProperties": DOCKER_CONTAINER_SCHEMA,
                },
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": True,
}


DOMAIN_DESCRIPTOR_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
        },
        "schema": {
            "type": "string",
            "minLength": 1,
        },
        "handler": {
            "type": "string",
            "minLength": 1,
        },
        "projection": {
            "type": "object",
            "properties": {
                "prefix": {
                    "type": "string",
                    "pattern": "^[A-Z_][A-Z0-9_]*$",
                },
            },
            "additionalProperties": False,
        },
        "requires": {
            "type": "object",
            "properties": {
                "images": {
                    "type": "object",
                    "additionalProperties": DOCKER_IMAGE_SCHEMA,
                },
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


def load_yaml_file(path):
    with open(path, "r", encoding="utf-8") as stream:
        loaded = yaml.safe_load(stream)

    if loaded is None:
        return {}

    if not isinstance(loaded, dict):
        raise Exception(f"YAML config '{path}' must contain an object at the document root")

    return loaded


def deep_merge(base, overlay):
    if isinstance(base, dict) and isinstance(overlay, dict):
        result = copy.deepcopy(base)
        for key, value in overlay.items():
            if key in result:
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    return copy.deepcopy(overlay)


def parse_yaml_parameter(parameter):
    split_parameter = re.compile("[ ]*=[ ]*", re.ASCII).split(parameter, maxsplit=1)
    if len(split_parameter) != 2 or not split_parameter[0]:
        raise Exception(f"Wrong YAML parameter override format: '{parameter}'")

    value = yaml.safe_load(split_parameter[1])
    if value is None and split_parameter[1].strip().lower() != "null":
        value = ""

    return split_parameter[0], value


def _parse_path(path):
    result = []
    for part in path.split("."):
        if not part:
            raise Exception(f"Wrong YAML parameter path: '{path}'")

        position = 0
        match = re.match(r"^[A-Za-z_][A-Za-z0-9_-]*", part)
        if not match:
            raise Exception(f"Wrong YAML parameter path element: '{part}'")

        result.append(match.group(0))
        position = match.end()

        while position < len(part):
            match = re.match(r"\[([0-9]+)\]", part[position:])
            if not match:
                raise Exception(f"Wrong YAML parameter path element: '{part}'")

            result.append(int(match.group(1)))
            position += match.end()

    return result


def apply_yaml_parameter(config, path, value):
    parsed_path = _parse_path(path)
    current = config

    for index, element in enumerate(parsed_path[:-1]):
        next_element = parsed_path[index + 1]
        if isinstance(element, int):
            if not isinstance(current, list):
                raise Exception(f"YAML path '{path}' expects a list before index {element}")
            while len(current) <= element:
                current.append({} if not isinstance(next_element, int) else [])
            current = current[element]
        else:
            if not isinstance(current, dict):
                raise Exception(f"YAML path '{path}' expects an object before '{element}'")
            if element not in current or current[element] is None:
                current[element] = [] if isinstance(next_element, int) else {}
            current = current[element]

    last = parsed_path[-1]
    if isinstance(last, int):
        if not isinstance(current, list):
            raise Exception(f"YAML path '{path}' expects a list before index {last}")
        while len(current) <= last:
            current.append(None)
        current[last] = value
    else:
        if not isinstance(current, dict):
            raise Exception(f"YAML path '{path}' expects an object before '{last}'")
        current[last] = value


def load_case_config(config_paths, yaml_parameters):
    merged = {}
    for config_path in config_paths or []:
        logger.info(f"Attempt to parse YAML config file '{config_path}'")
        merged = deep_merge(merged, load_yaml_file(config_path))

    for yaml_parameter in yaml_parameters or []:
        path, value = parse_yaml_parameter(yaml_parameter)
        logger.info(f"Apply YAML parameter override: {path}={value}")
        apply_yaml_parameter(merged, path, value)

    return merged


def apply_yaml_parameters(config, yaml_parameters):
    for yaml_parameter in yaml_parameters or []:
        path, value = parse_yaml_parameter(yaml_parameter)
        logger.info(f"Apply YAML parameter override: {path}={value}")
        apply_yaml_parameter(config, path, value)


def _validate_with_schema(data, schema, description):
    validator = Draft202012Validator(schema)
    error = best_match(validator.iter_errors(data))
    if not error:
        return

    path = ".".join(str(element) for element in error.absolute_path)
    if path:
        raise Exception(f"{description} validation failed at '{path}': {error.message}")
    raise Exception(f"{description} validation failed: {error.message}")


def validate_domain_descriptor(descriptor, domain_path):
    _validate_with_schema(
        descriptor,
        DOMAIN_DESCRIPTOR_SCHEMA,
        f"Domain descriptor '{domain_path}'",
    )


def apply_domain_yaml_parameters(descriptor, domain_name, domain_yaml_parameters):
    prefix = f"{domain_name}."
    for domain_yaml_parameter in domain_yaml_parameters or []:
        path, value = parse_yaml_parameter(domain_yaml_parameter)
        if not path.startswith(prefix):
            continue

        domain_path = path[len(prefix):]
        if not domain_path:
            raise Exception(f"Wrong domain YAML parameter path: '{path}'")

        logger.info(f"Apply domain YAML parameter override: {path}={value}")
        apply_yaml_parameter(descriptor, domain_path, value)


def discover_domains(module_dirs):
    return discover_domains_with_overrides(module_dirs, None)


def discover_domains_with_overrides(module_dirs, domain_yaml_parameters):
    domains = {}
    for module_dir in module_dirs or []:
        for root, _, files in os.walk(module_dir):
            if "domain.yaml" not in files:
                continue

            domain_path = os.path.join(root, "domain.yaml")
            descriptor = load_yaml_file(domain_path)
            domain_name = descriptor.get("name")
            if not domain_name:
                raise Exception(f"Domain descriptor '{domain_path}' does not define 'name'")

            apply_domain_yaml_parameters(descriptor, domain_name, domain_yaml_parameters)
            validate_domain_descriptor(descriptor, domain_path)

            descriptor["_path"] = domain_path
            descriptor["_root"] = root
            domains[domain_name] = descriptor
            logger.info(f"Registered YAML domain '{domain_name}' from '{domain_path}'")

    return domains


def _case_domain_names(config):
    result = []
    case = config.get("case")
    if isinstance(case, dict) and case.get("domain"):
        result.append(case.get("domain"))

    uses = config.get("uses")
    if isinstance(uses, list):
        for entry in uses:
            if isinstance(entry, dict) and entry.get("domain"):
                result.append(entry.get("domain"))

    return list(dict.fromkeys(result))


def apply_domain_defaults(config, domains):
    default_config = {"docker": {"images": {}}}

    for domain_name in _case_domain_names(config):
        domain_descriptor = domains.get(domain_name)
        if not domain_descriptor:
            raise Exception(f"YAML domain '{domain_name}' was not found in imported module dirs")

        required_images = domain_descriptor.get("requires", {}).get("images", {})
        for image_alias, image_config in required_images.items():
            default_config["docker"]["images"][image_alias] = image_config

    return deep_merge(default_config, config)


def _resolve_schema_path(schema_path, domain_descriptor):
    if os.path.isabs(schema_path):
        return schema_path
    if domain_descriptor:
        return os.path.join(domain_descriptor["_root"], schema_path)
    return schema_path


def resolve_schema_paths(config, domains, explicit_schema_paths):
    result = []

    for schema_path in explicit_schema_paths or []:
        result.append(_resolve_schema_path(schema_path, None))

    for domain_name in _case_domain_names(config):
        domain_descriptor = domains.get(domain_name)
        if not domain_descriptor:
            raise Exception(f"YAML domain '{domain_name}' was not found in imported module dirs")

        schema_path = domain_descriptor.get("schema")
        if schema_path:
            result.append(_resolve_schema_path(schema_path, domain_descriptor))

    return list(dict.fromkeys(result))


def validate_case_config(config, schema_paths):
    _validate_with_schema(config, BUILTIN_CASE_SCHEMA, "Built-in YAML schema")
    for schema_path in schema_paths:
        logger.info(f"Validate YAML config with schema '{schema_path}'")
        schema = load_yaml_file(schema_path)
        _validate_with_schema(config, schema, "YAML schema")


def _safe_env_name(path_elements):
    raw_name = "_".join(str(element) for element in path_elements)
    return re.sub("[^A-Za-z0-9_]", "_", raw_name).upper()


def _stringify_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


def _project_value(value, path_elements, prefix, variables):
    if isinstance(value, dict):
        for key, child in value.items():
            _project_value(child, path_elements + [key], prefix, variables)
    elif isinstance(value, list):
        variables[prefix + _safe_env_name(path_elements + ["count"])] = str(len(value))
        for index, child in enumerate(value):
            _project_value(child, path_elements + [index], prefix, variables)
    else:
        variables[prefix + _safe_env_name(path_elements)] = _stringify_value(value)


def project_config(config, prefix="YAML_CONF_"):
    variables = {}
    _project_value(config, [], prefix, variables)
    return variables


def _case_name(config):
    case = config.get("case")
    if isinstance(case, dict) and case.get("name"):
        return str(case.get("name"))
    return "case"


def write_expanded_config(config, output_root):
    generated_root = os.path.join(output_root, "generated", _case_name(config))
    os.makedirs(generated_root, exist_ok=True)
    output_path = os.path.join(generated_root, "case.expanded.json")

    with open(output_path, "w", encoding="utf-8") as stream:
        json.dump(config, stream, indent=2, sort_keys=True)
        stream.write("\n")

    return output_path
