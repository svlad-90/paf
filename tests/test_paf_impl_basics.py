import json

from paf.paf_impl import Environment
from paf.paf_impl import Task


def test_environment_variables_and_yaml_config_are_copied():
    env = Environment()
    env.setVariableValue("A", "B")
    env.setYamlConfig({"case": {"name": "sample"}})

    yaml_config = env.getYamlConfig()
    yaml_config["case"]["name"] = "changed"

    assert env.getVariableValue("A") == "B"
    assert env.getVariableValue("missing", "default") == "default"
    assert env.getYamlConfig()["case"]["name"] == "sample"

    env.deleteVariableValue("A")
    assert env.getVariableValue("A") is None


def test_task_get_yaml_config_prefers_environment_object():
    env = Environment()
    env.setYamlConfig({"case": {"name": "from-env"}})
    task = Task()
    task.set_environment(env)

    assert task.get_yaml_config()["case"]["name"] == "from-env"


def test_task_get_yaml_config_reads_yaml_conf_file(tmp_path):
    config_path = tmp_path / "case.expanded.json"
    config_path.write_text(json.dumps({"case": {"name": "from-file"}}), encoding="utf-8")
    env = Environment()
    env.setVariableValue("YAML_CONF_FILE", str(config_path))
    task = Task()
    task.set_environment(env)

    assert task.get_yaml_config()["case"]["name"] == "from-file"


def test_task_get_yaml_config_returns_empty_when_unset():
    task = Task()

    assert task.get_yaml_config() == {}
