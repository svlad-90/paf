import types
from typing import Any

import pytest

from paf import paf_impl
from paf.paf_impl import CommunicationMode
from paf.paf_impl import Config
from paf.paf_impl import Environment
from paf.paf_impl import ExecutionElement
from paf.paf_impl import ExecutionMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import Phase
from paf.paf_impl import Scenario
from paf.paf_impl import SSHConnection
from paf.paf_impl import SSHConnectionCache
from paf.paf_impl import SSHLocalClient
from paf.paf_impl import Task


def test_config_defaults_can_be_changed():
    old_exec = Config.get_default_execution_mode()
    old_interaction = Config.get_default_interaction_mode()
    old_communication = Config.get_default_communication_mode()
    try:
        Config.set_default_execution_mode(ExecutionMode.DEV_NULL)
        Config.set_default_interaction_mode(InteractionMode.IGNORE_INPUT)
        Config.set_default_communication_mode(CommunicationMode.PIPE_OUTPUT)

        assert Config.get_default_execution_mode() == ExecutionMode.DEV_NULL
        assert Config.get_default_interaction_mode() == InteractionMode.IGNORE_INPUT
        assert Config.get_default_communication_mode() == CommunicationMode.PIPE_OUTPUT
    finally:
        Config.set_default_execution_mode(old_exec)
        Config.set_default_interaction_mode(old_interaction)
        Config.set_default_communication_mode(old_communication)


def test_environment_dump_masks_sensitive_values(monkeypatch):
    messages = []
    monkeypatch.setattr(paf_impl.logger, "info", lambda msg, *args, **kwargs: messages.append(msg))
    env = Environment()
    env.setVariableValue("TOKEN", "secret")
    env.setVariableValue("NORMAL", "hello world")
    env.setVariableValue("PAF_SECRET_PARAMS", "CUSTOM")
    env.setVariableValue("CUSTOM", "hidden")

    env.dump()

    assert "export TOKEN=<hidden>" in messages
    assert 'export NORMAL="hello world"' in messages
    assert "export CUSTOM=<hidden>" in messages


def test_logger_file_paths_with_fake_file_logger(monkeypatch):
    calls = []

    class FakeFileLogger:
        def info(self, msg, *args, **kwargs):
            calls.append(("info", msg))

        def warning(self, msg, *args, **kwargs):
            calls.append(("warning", msg))

        def error(self, msg, *args, **kwargs):
            calls.append(("error", msg))

    monkeypatch.setattr(paf_impl.logger, "_logger__log_dir", "/tmp/paf-logs")
    monkeypatch.setattr(paf_impl.logger, "_logger__logging_to_file", FakeFileLogger())

    paf_impl.logger.info("plain")
    paf_impl.logger.warning("warn")
    paf_impl.logger.error("err")
    paf_impl.logger.non_formatted_info_to_file("nf-info")
    paf_impl.logger.non_formatted_warning_to_file("nf-warn")
    paf_impl.logger.non_formatted_error_to_file("nf-err")

    assert calls == [
        ("info", "plain"),
        ("warning", "warn"),
        ("error", "err"),
        ("info", "nf-info"),
        ("warning", "nf-warn"),
        ("error", "nf-err"),
    ]


def test_task_subprocess_success_and_failure_paths():
    task = Task()

    out = task.subprocess_must_succeed(
        ["/bin/echo", "hello"],
        shell=False,
        communication_mode=CommunicationMode.PIPE_OUTPUT,
        interaction_mode=InteractionMode.IGNORE_INPUT,
    )
    assert out == "hello\n"

    with pytest.raises(Exception, match="Subprocess should succeed"):
        task.subprocess_must_succeed(
            ["/bin/sh", "-c", "exit 7"],
            shell=False,
            communication_mode=CommunicationMode.PIPE_OUTPUT,
            interaction_mode=InteractionMode.IGNORE_INPUT,
        )

    out = task.subprocess_must_succeed(
        ["/bin/sh", "-c", "exit 7"],
        shell=False,
        expected_return_codes=[7],
        communication_mode=CommunicationMode.PIPE_OUTPUT,
        interaction_mode=InteractionMode.IGNORE_INPUT,
    )
    assert out == ""


def test_task_exec_subprocess_substitutes_params():
    env = Environment()
    env.setVariableValue("WORD", "hello")
    task = Task()
    task.set_environment(env)

    output = task.exec_subprocess(
        ["/bin/echo", "${WORD}"],
        shell=False,
        communication_mode=CommunicationMode.PIPE_OUTPUT,
        interaction_mode=InteractionMode.IGNORE_INPUT,
    )

    assert output.exit_code == 0
    assert output.stdout == "hello\n"


def test_task_ssh_wrappers_use_connection_cache():
    class Output:
        def __init__(self, exit_code):
            self.exit_code = exit_code
            self.stdout = "ssh-out"

    class FakeCache:
        def __init__(self, exit_code):
            self.exit_code = exit_code
            self.calls = []

        def exec_command(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return Output(self.exit_code)

    task = Task()
    cache = FakeCache(0)
    task._Task__ssh_connection_cache = cache  # type: ignore[attr-defined]

    assert task.ssh_command_must_succeed("echo ${X}", "host", "user") == "ssh-out"
    assert cache.calls[0][0][:4] == ("echo ${X}", "host", "user", 22)

    cache = FakeCache(3)
    task._Task__ssh_connection_cache = cache  # type: ignore[attr-defined]
    with pytest.raises(Exception, match="SSH command should succeed"):
        task.ssh_command_must_succeed("false", "host", "user")
    assert task.exec_ssh_command("false", "host", "user").exit_code == 3


def test_task_docker_wrappers_use_docker_runtime(monkeypatch):
    class Output:
        exit_code = 0
        stdout = "docker-out"

    task = Task()
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def record_exec_subprocess(*args, **kwargs):
        calls.append((args, kwargs))
        return Output()

    monkeypatch.setattr("paf.docker_runtime.ensure_image", lambda task_arg, alias: f"image:{alias}")
    monkeypatch.setattr("paf.docker_runtime.docker_run_command", lambda task_arg, alias, cmd: ["docker", alias, cmd])
    monkeypatch.setattr(task, "exec_subprocess", record_exec_subprocess)

    assert task.ensure_docker_image("builder") == "image:builder"
    assert task.docker_exec_subprocess("container", "echo ok").stdout == "docker-out"
    assert task.docker_subprocess_must_succeed("container", "echo ok") == "docker-out"
    assert calls[0][0][0] == ["docker", "container", "echo ok"]


def test_task_helpers_and_assertions():
    task = Task()
    task.set_name("name")
    assert task.get_name() == "name"
    assert task._get_create_file_marker_command("/tmp/a", "done") == 'echo "done" > /tmp/a'
    assert task._get_file_marker_content_command("/tmp/a") == "[ -f /tmp/a ] && cat /tmp/a"
    assert "MARKER_FILE_CONTENT" in task._wrap_command_with_file_marker_condition("/tmp/a", "echo run", "done")

    with pytest.raises(Exception, match="boom"):
        task.assertion(False, "boom")

    with pytest.raises(Exception, match="boom"):
        task.fail("boom")


def test_task_start_invokes_init_execute_and_exports_environment():
    class RecordingTask(Task):
        def __init__(self):
            super().__init__()
            self.calls: list[tuple[str, Any]] = []

        def init(self):
            self.calls.append(("init", self.VALUE))  # type: ignore[attr-defined]

        def execute(self):
            self.calls.append(("execute", self.VALUE))  # type: ignore[attr-defined]

    env = Environment()
    env.setVariableValue("VALUE", "from-env")
    task = RecordingTask()
    task.set_environment(env)
    task.start()

    assert task.VALUE == "from-env"  # type: ignore[attr-defined]
    assert task.get_environment() is env
    assert task.calls == [("init", "from-env"), ("execute", "from-env")]


def test_task_boolean_and_environment_helpers():
    task = Task()
    task.set_environment_param("YES", "True")
    task.set_environment_param("NO", "false")
    task.set_environment_param("EMPTY", "")

    assert task.has_environment_param("YES")
    assert task.has_environment_true_param("YES")
    assert not task.has_environment_true_param("NO")
    assert not task.has_non_empty_environment_param("EMPTY")
    assert task.get_environment_param("YES") == "True"

    task.delete_environment_param("YES")
    assert not task.has_environment_param("YES")


def test_ssh_connection_cache_reuses_connections(monkeypatch):
    class FakeConnection:
        instances: list["FakeConnection"] = []

        @staticmethod
        def create_connection_key(host, user, port):
            return f"{user}@{host}:{port}"

        def __init__(self, host, user, port, password, key_filename, jumphost=None, passphrase=None):
            self.args = (host, user, port, password, key_filename, jumphost, passphrase)
            self.commands = []
            FakeConnection.instances.append(self)

        def connect(self):
            self.connected = True

        def get_connection_key(self):
            return f"{self.args[0]}:{self.args[1]}:{self.args[2]}:{self.args[4]}"

        def exec_command(self, *args, **kwargs):
            self.commands.append((args, kwargs))
            return types.SimpleNamespace(exit_code=0, stdout="cached")

    monkeypatch.setattr(paf_impl, "SSHConnection", FakeConnection)
    cache = SSHConnectionCache()

    first = cache.find_or_create_connection("host", "user", 22, "pass", "key")
    second = cache.find_or_create_connection("host", "user", 22, "pass", "key")
    output = cache.exec_command("cmd", "host", "user", 22, "pass", "key")

    assert first is second
    assert output.stdout == "cached"
    assert len(FakeConnection.instances) == 1


def test_ssh_connection_executes_with_paramiko_facade(monkeypatch):
    class FakeClient:
        instances: list["FakeClient"] = []

        def __init__(self):
            self.connect_kwargs = None
            self.closed = False
            FakeClient.instances.append(self)

        def set_missing_host_key_policy(self, policy):
            self.policy = policy

        def connect(self, **kwargs):
            self.connect_kwargs = kwargs

        def close(self):
            self.closed = True

    class FakeOutput:
        def __init__(self, exec_mode, stdin, stdout, stderr, *args):
            self.exec_mode = exec_mode
            self.stdin = stdin
            self.stdout = "ssh-output"
            self.stderr = ""
            self.exit_code = 0

    exec_calls: list[tuple[Any, str, int, dict[str, Any]]] = []

    def fake_exec_command(client, cmd, timeout, **kwargs):
        exec_calls.append((client, cmd, timeout, kwargs))
        return "stdin", "stdout", "stderr"

    monkeypatch.setattr(paf_impl.paramiko, "SSHClient", FakeClient)
    monkeypatch.setattr(paf_impl.paramiko, "AutoAddPolicy", lambda: "policy")
    monkeypatch.setattr(paf_impl.common, "get_terminal_dimensions", lambda: (120, 40))
    monkeypatch.setattr(paf_impl.common, "exec_command", fake_exec_command)
    monkeypatch.setattr(paf_impl, "SSHCommandOutput", FakeOutput)

    connection = SSHConnection("host", "user", 2222, password="pass", key_filename=["id"], passphrase="phrase")
    output = connection.exec_command(
        "echo ${WORD}",
        timeout=3,
        params={"WORD": "ok"},
        interaction_mode=InteractionMode.IGNORE_INPUT,
    )
    connection.disconnect()

    assert SSHConnection.create_connection_key("host", "user", 2222) == "user@host:2222"
    assert connection.get_connection_key() == "user@host:2222"
    assert FakeClient.instances[0].connect_kwargs is not None
    assert FakeClient.instances[0].connect_kwargs["hostname"] == "host"
    assert exec_calls[0][1] == "echo ok"
    assert exec_calls[0][2] == 3
    assert output.stdout == "ssh-output"
    assert FakeClient.instances[0].closed

    connection._SSHConnection__connected = False  # type: ignore[attr-defined]
    with pytest.raises(Exception, match="absence of connection"):
        connection.exec_command("true")


def test_ssh_connection_uses_jumphost_channel(monkeypatch):
    class FakeTransport:
        def open_channel(self, channel_type, dest_addr, src_addr):
            self.channel = (channel_type, dest_addr, src_addr)
            return "jump-channel"

    class FakeJumpHost:
        _SSHConnection__client: Any
        _SSHConnection__host: str
        _SSHConnection__port: int

    class FakeClient:
        instances: list["FakeClient"] = []

        def __init__(self):
            self.transport = FakeTransport()
            self.connect_kwargs = None
            FakeClient.instances.append(self)

        def set_missing_host_key_policy(self, policy):
            self.policy = policy

        def get_transport(self):
            return self.transport

        def connect(self, **kwargs):
            self.connect_kwargs = kwargs

    monkeypatch.setattr(paf_impl.paramiko, "SSHClient", FakeClient)
    monkeypatch.setattr(paf_impl.paramiko, "AutoAddPolicy", lambda: "policy")

    jumphost = FakeJumpHost()
    jumphost._SSHConnection__client = FakeClient()
    jumphost._SSHConnection__host = "jump"
    jumphost._SSHConnection__port = 22
    connection = SSHConnection("host", "user", 2222, jumphost=jumphost)

    assert connection.get_connection_key() == "user@host:2222"
    assert FakeClient.instances[-1].connect_kwargs is not None
    assert FakeClient.instances[-1].connect_kwargs["sock"] == "jump-channel"
    assert jumphost._SSHConnection__client.transport.channel == (
        "direct-tcpip",
        ("host", 2222),
        ("jump", 22),
    )


def test_ssh_local_client_delegates_to_localhost():
    class FakeCache:
        def __init__(self):
            self.calls = []

        def exec_command(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return types.SimpleNamespace(exit_code=0, stdout="local")

    client = SSHLocalClient()
    cache = FakeCache()
    client._Task__ssh_connection_cache = cache  # type: ignore[attr-defined]
    client.set_environment_param("LOCAL_HOST_IP_ADDRESS", "127.0.0.1")
    client.set_environment_param("LOCAL_HOST_USER_NAME", "root")
    client.set_environment_param("LOCAL_HOST_SYSTEM_SSH_KEY", "key")
    client.set_environment_param("LOCAL_HOST_SYSTEM_PASSWORD", "pass")

    assert client.local_ssh_command_must_succeed("echo ok") == "local"
    assert client.exec_local_ssh_command("echo ok").stdout == "local"
    assert cache.calls[0][0][:3] == ("echo ok", "127.0.0.1", "root")


def test_phase_scenario_and_execution_element():
    phase = Phase()
    phase.add_task("module.Task", {"A": "B"})
    assert phase.get_tasks() == [("module.Task", {"A": "B"})]

    scenario = Scenario()
    scenario.add_phase("build", {})
    assert scenario.get_phases() == [("build", {})]

    element = ExecutionElement(ExecutionElement.ExecutionElementType_Task, "task")
    assert element.get_element_type() == ExecutionElement.ExecutionElementType_Task
    assert element.get_element_name() == "task"
