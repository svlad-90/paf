import pytest
from typing import Any

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
                "containers": {
                    "builder-container": {
                        "image": "builder",
                        "workdir": "/workspace",
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
            "containers": {
                "builder-container": {
                    "image": "builder",
                    "workdir": "/case-workspace",
                },
            },
        },
    }

    merged = yaml_config.apply_domain_defaults(config, domains)

    assert merged["docker"]["images"]["builder"]["image"] == "case/override:latest"
    assert merged["docker"]["images"]["builder"]["dockerfile"] == "Dockerfile"
    assert merged["docker"]["images"]["builder"]["context"] == "."
    assert merged["docker"]["containers"]["builder-container"]["image"] == "builder"
    assert merged["docker"]["containers"]["builder-container"]["workdir"] == "/case-workspace"


def test_domain_yaml_parameter_updates_descriptor_before_validation():
    descriptor: dict[str, Any] = {
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


def test_yaml_file_loading_and_deep_merge(tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    sequence = tmp_path / "sequence.yaml"
    sequence.write_text("- bad\n", encoding="utf-8")

    assert yaml_config.load_yaml_file(str(empty)) == {}
    with pytest.raises(Exception, match="document root"):
        yaml_config.load_yaml_file(str(sequence))

    merged = yaml_config.deep_merge(
        {"a": {"b": 1}, "list": [1]},
        {"a": {"c": 2}, "list": [2]},
    )

    assert merged == {"a": {"b": 1, "c": 2}, "list": [2]}


def test_yaml_parameters_create_nested_objects_and_lists():
    config: dict[str, Any] = {}

    yaml_config.apply_yaml_parameters(
        config,
        [
            "root.items[1].name = item",
            "root.enabled=true",
            "root.empty=",
            "root.none=null",
        ],
    )

    assert config["root"]["items"][0] == {}
    assert config["root"]["items"][1]["name"] == "item"
    assert config["root"]["enabled"] is True
    assert config["root"]["empty"] == ""
    assert config["root"]["none"] is None


@pytest.mark.parametrize(
    "parameter",
    [
        "missing_separator",
        "=value",
    ],
)
def test_yaml_parameter_rejects_wrong_assignment(parameter):
    with pytest.raises(Exception, match="Wrong YAML parameter override format"):
        yaml_config.parse_yaml_parameter(parameter)


@pytest.mark.parametrize(
    "path",
    [
        ".bad=value",
        "bad[]=value",
        "0bad=value",
    ],
)
def test_yaml_parameter_rejects_wrong_path(path):
    config: dict[str, Any] = {}
    with pytest.raises(Exception, match="Wrong YAML parameter path"):
        yaml_config.apply_yaml_parameters(config, [path])


def test_yaml_parameter_rejects_incompatible_existing_shape():
    config = {"root": "scalar", "items": {}}

    with pytest.raises(Exception, match="expects an object"):
        yaml_config.apply_yaml_parameter(config, "root.child", "value")

    with pytest.raises(Exception, match="expects a list"):
        yaml_config.apply_yaml_parameter(config, "items[0]", "value")


def test_discover_domains_and_resolve_schema_paths(tmp_path):
    module_dir = tmp_path / "modules"
    domain_dir = module_dir / "domain"
    domain_dir.mkdir(parents=True)
    schema = domain_dir / "schema.yaml"
    schema.write_text("type: object\n", encoding="utf-8")
    (domain_dir / "domain.yaml").write_text(
        "name: sample\n"
        "schema: schema.yaml\n"
        "requires:\n"
        "  images:\n"
        "    builder:\n"
        "      image: default:latest\n"
        "  containers:\n"
        "    build:\n"
        "      image: builder\n"
        "      workdir: /workspace\n",
        encoding="utf-8",
    )

    domains = yaml_config.discover_domains_with_overrides(
        [str(module_dir)],
        ["sample.requires.images.builder.image=override:latest"],
    )
    config = {"uses": [{"domain": "sample"}, {"domain": "sample"}]}

    assert domains["sample"]["requires"]["images"]["builder"]["image"] == "override:latest"
    assert yaml_config.resolve_schema_paths(config, domains, ["explicit.yaml"]) == [
        "explicit.yaml",
        str(schema),
    ]
    assert yaml_config.apply_domain_defaults(config, domains)["docker"]["images"]["builder"]["image"] == "override:latest"
    assert yaml_config.apply_domain_defaults(config, domains)["docker"]["containers"]["build"]["workdir"] == "/workspace"


def test_domain_resolution_rejects_missing_domain():
    config = {"case": {"domain": "missing"}}

    with pytest.raises(Exception, match="was not found"):
        yaml_config.apply_domain_defaults(config, {})

    with pytest.raises(Exception, match="was not found"):
        yaml_config.resolve_schema_paths(config, {}, [])


def test_validate_case_config_uses_explicit_schema(tmp_path):
    schema = tmp_path / "schema.yaml"
    schema.write_text(
        "type: object\n"
        "required: [case]\n"
        "properties:\n"
        "  case:\n"
        "    type: object\n",
        encoding="utf-8",
    )

    yaml_config.validate_case_config({"case": {}}, [str(schema)])
    with pytest.raises(Exception, match="YAML schema validation failed"):
        yaml_config.validate_case_config({"wrong": {}}, [str(schema)])


def test_load_case_config_and_write_expanded_config(tmp_path):
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text("case:\n  name: sample\nvalue: old\n", encoding="utf-8")
    second.write_text("value: new\n", encoding="utf-8")

    config = yaml_config.load_case_config(
        [str(first), str(second)],
        ["items[0].name=created"],
    )
    output_path = yaml_config.write_expanded_config(config, str(tmp_path))

    assert config["value"] == "new"
    assert config["items"][0]["name"] == "created"
    assert output_path.endswith("generated/sample/case.expanded.json")
    assert '"value": "new"' in (tmp_path / "generated" / "sample" / "case.expanded.json").read_text(
        encoding="utf-8",
    )
