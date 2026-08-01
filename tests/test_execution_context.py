import pytest

from paf.paf_impl import Environment
from paf.paf_impl import ExecutionContext
from paf.paf_impl import ExecutionElement


def test_execution_context_runs_xml_scenario(tmp_path):
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    marker = tmp_path / "marker.txt"
    (module_dir / "tasks.py").write_text(
        "from paf.paf_impl import Task\n"
        "class write_marker(Task):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        self.set_name(write_marker.__name__)\n"
        "    def execute(self):\n"
        "        with open(self.MARKER, 'w', encoding='utf-8') as stream:\n"
        "            stream.write(self.VALUE)\n",
        encoding="utf-8",
    )
    config = tmp_path / "scenario.xml"
    config.write_text(
        "<paf_config>"
        "  <param name='MARKER' value='" + str(marker) + "'/>"
        "  <param name='VALUE' value='done'/>"
        "  <phase name='write'>"
        "    <task name='modules.tasks.write_marker'>"
        "      <condition name='RUN' value='yes'/>"
        "    </task>"
        "  </phase>"
        "  <scenario name='default'>"
        "    <phase name='write'/>"
        "  </scenario>"
        "</paf_config>",
        encoding="utf-8",
    )
    env = Environment()
    env.setVariableValue("RUN", "yes")
    context = ExecutionContext(str(tmp_path / "logs"))
    context.import_modules([str(module_dir)])
    context.add_execution_element(ExecutionElement.ExecutionElementType_Scenario, "default")
    context.parse_config(str(config), context, env)

    context.execute(env)

    assert marker.read_text(encoding="utf-8") == "done"


def test_execution_context_skips_unmet_conditions(tmp_path):
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    marker = tmp_path / "marker.txt"
    (module_dir / "tasks.py").write_text(
        "from paf.paf_impl import Task\n"
        "class write_marker(Task):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        self.set_name(write_marker.__name__)\n"
        "    def execute(self):\n"
        "        open(self.MARKER, 'w').close()\n",
        encoding="utf-8",
    )
    config = tmp_path / "scenario.xml"
    config.write_text(
        "<paf_config>"
        "  <param name='MARKER' value='" + str(marker) + "'/>"
        "  <phase name='write'>"
        "    <task name='modules.tasks.write_marker'>"
        "      <condition name='RUN' value='yes'/>"
        "    </task>"
        "  </phase>"
        "</paf_config>",
        encoding="utf-8",
    )
    env = Environment()
    env.setVariableValue("RUN", "no")
    context = ExecutionContext(str(tmp_path / "logs"))
    context.import_modules([str(module_dir)])
    context.add_execution_element(ExecutionElement.ExecutionElementType_Phase, "write")
    context.parse_config(str(config), context, env)

    context.execute(env)

    assert not marker.exists()


def test_execution_context_rejects_bad_xml(tmp_path):
    env = Environment()
    context = ExecutionContext(str(tmp_path / "logs"))
    config = tmp_path / "bad.xml"
    config.write_text("<wrong/>", encoding="utf-8")

    with pytest.raises(Exception, match="Wrong XML format"):
        context.parse_config(str(config), context, env)


def test_execution_context_rejects_unknown_phase_and_scenario(tmp_path):
    env = Environment()
    context = ExecutionContext(str(tmp_path / "logs"))
    context.add_execution_element(ExecutionElement.ExecutionElementType_Phase, "missing")

    with pytest.raises(Exception, match="Phase 'missing' was not found"):
        context.execute(env)

    context = ExecutionContext(str(tmp_path / "logs2"))
    context.add_execution_element(ExecutionElement.ExecutionElementType_Scenario, "missing")
    with pytest.raises(Exception, match="Scenario 'missing' was not found"):
        context.execute(env)


@pytest.mark.parametrize(
    "xml,match",
    [
        ("<paf_config><param value='x'/></paf_config>", "Unexpected number"),
        ("<paf_config><param name='x' value='y' extra='z'/></paf_config>", "Unexpected number"),
        ("<paf_config><phase><task name='t'/></phase></paf_config>", "phase"),
        ("<paf_config><phase name='p'><bad/></phase></paf_config>", "Unexpected XML tag"),
        ("<paf_config><phase name='p'><task/></phase></paf_config>", "task"),
        ("<paf_config><phase name='p'><task name='t'><condition value='x'/></task></phase></paf_config>", "condition"),
        ("<paf_config><scenario><phase name='p'/></scenario></paf_config>", "scenario"),
        ("<paf_config><scenario name='s'><bad/></scenario></paf_config>", "Unexpected XML tag"),
        ("<paf_config><scenario name='s'><phase/></scenario></paf_config>", "phase"),
        ("<paf_config><unexpected/></paf_config>", "Unexpected XML tag"),
    ],
)
def test_execution_context_rejects_bad_config_shapes(tmp_path, xml, match):
    env = Environment()
    context = ExecutionContext(str(tmp_path / "logs"))
    config = tmp_path / "bad-shape.xml"
    config.write_text(xml, encoding="utf-8")

    with pytest.raises(Exception, match=match):
        context.parse_config(str(config), context, env)
