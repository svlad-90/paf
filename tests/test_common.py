import os

import pytest

from paf import common


def test_load_all_modules_in_dir_registers_dotted_aliases(tmp_path):
    module_root = tmp_path / "sample_modules"
    nested = module_root / "nested"
    nested.mkdir(parents=True)
    (module_root / "tasks.py").write_text(
        "class root_task:\n"
        "    pass\n",
        encoding="utf-8",
    )
    (nested / "tasks.py").write_text(
        "class nested_task:\n"
        "    pass\n",
        encoding="utf-8",
    )

    loaded = common.load_all_modules_in_dir(str(module_root))

    assert "tasks" in loaded
    assert "sample_modules.tasks" in loaded
    assert "nested.tasks" in loaded
    assert "sample_modules.nested.tasks" in loaded
    assert common.create_class_instance("sample_modules.tasks.root_task", loaded).__name__ == "root_task"
    assert common.create_class_instance("sample_modules.nested.tasks.nested_task", loaded).__name__ == "nested_task"


def test_load_all_modules_in_dir_rejects_missing_directory(tmp_path):
    with pytest.raises(Exception, match="is not a directory"):
        common.load_all_modules_in_dir(str(tmp_path / "missing"))


def test_create_class_instance_rejects_unknown_module():
    with pytest.raises(Exception, match="Module 'missing' is not loaded"):
        common.create_class_instance("missing.Task", {})


def test_exec_command_opens_ssh_channel():
    class FakeChannel:
        def __init__(self):
            self.timeout = None
            self.environment = None
            self.command = None

        def settimeout(self, timeout):
            self.timeout = timeout

        def update_environment(self, environment):
            self.environment = environment

        def exec_command(self, command):
            self.command = command

        def makefile_stdin(self, mode, bufsize):
            return ("stdin", mode, bufsize)

        def makefile(self, mode, bufsize):
            return ("stdout", mode, bufsize)

        def makefile_stderr(self, mode, bufsize):
            return ("stderr", mode, bufsize)

    class FakeTransport:
        def __init__(self, channel):
            self.channel = channel
            self.timeout = None

        def open_session(self, timeout=None):
            self.timeout = timeout
            return self.channel

    channel = FakeChannel()
    client = type("FakeClient", (), {"_transport": FakeTransport(channel)})()

    stdin, stdout, stderr = common.exec_command(
        client,
        "echo hello",
        timeout=3,
        environment={"A": "B"},
    )

    assert client._transport.timeout == 3
    assert channel.timeout == 3
    assert channel.environment == {"A": "B"}
    assert channel.command == "echo hello"
    assert stdin == ("stdin", "wb", -1)
    assert stdout == ("stdout", "r", -1)
    assert stderr == ("stderr", "r", -1)


def test_isatty_and_has_fileno_handle_plain_objects():
    class WithoutFileno:
        pass

    assert common.has_fileno(WithoutFileno()) is False
    assert common.isatty(WithoutFileno()) is False
    assert common.has_fileno(open(os.devnull, "rb")) is True
