import pytest

from paf import yaml_config


def test_apply_domain_defaults_then_case_overrides():
    domains = {
        "sample": {
            "requires": {
                "images": {
                    "builder": {
                        "image": "domain/default:latest",
                        "dockerfile": "Dockerfile",
                        "context": ".",
                    },
                },
            },
        },
    }
    config = {
        "case": {"name": "case", "domain": "sample"},
        "docker": {
            "images": {
                "builder": {
                    "image": "case/override:latest",
                },
            },
        },
    }

    merged = yaml_config.apply_domain_defaults(config, domains)

    assert merged["docker"]["images"]["builder"]["image"] == "case/override:latest"
    assert merged["docker"]["images"]["builder"]["dockerfile"] == "Dockerfile"
    assert merged["docker"]["images"]["builder"]["context"] == "."


def test_domain_yaml_parameter_updates_descriptor_before_validation():
    descriptor = {
        "name": "sample",
        "requires": {
            "images": {
                "builder": {
                    "image": "domain/default:latest",
                },
            },
        },
    }

    yaml_config.apply_domain_yaml_parameters(
        descriptor,
        "sample",
        ["sample.requires.images.builder.image=custom/image:debug"],
    )
    yaml_config.validate_domain_descriptor(descriptor, "domain.yaml")

    assert descriptor["requires"]["images"]["builder"]["image"] == "custom/image:debug"


def test_domain_descriptor_rejects_unknown_fields():
    descriptor = {
        "name": "sample",
        "schemas": "schema.yaml",
    }

    with pytest.raises(Exception, match="Additional properties"):
        yaml_config.validate_domain_descriptor(descriptor, "domain.yaml")


def test_builtin_schema_validates_docker_section():
    config = {
        "case": {"name": "case"},
        "docker": {
            "containers": {
                "build": {
                    "image": "builder",
                    "mounts": [
                        {
                            "source": "/workspace",
                            "target": "/workspace",
                            "mode": "invalid",
                        },
                    ],
                },
            },
        },
    }

    with pytest.raises(Exception, match="Built-in YAML schema validation failed"):
        yaml_config.validate_case_config(config, [])


def test_yaml_projection_includes_counts_and_flat_values():
    config = {
        "case": {"name": "case"},
        "validation": {"expected": ["PASS", "DONE"]},
    }

    projected = yaml_config.project_config(config)

    assert projected["YAML_CONF_CASE_NAME"] == "case"
    assert projected["YAML_CONF_VALIDATION_EXPECTED_COUNT"] == "2"
    assert projected["YAML_CONF_VALIDATION_EXPECTED_1"] == "DONE"
