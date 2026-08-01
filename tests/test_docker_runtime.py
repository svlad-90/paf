from typing import Any

from paf import docker_runtime
import pytest


class FakeInspectOutput:
    def __init__(self, exit_code=0):
        self.exit_code = exit_code


class FakeTask:
    WORKSPACE_ROOT = "/host/workspace"

    def __init__(self, inspect_exit_code=0):
        self.commands: list[list[str]] = []
        self.must_succeed_commands: list[list[str]] = []
        self.inspect_exit_code = inspect_exit_code
        self.config: dict[str, Any] = {
            "docker": {
                "images": {
                    "builder-img": {
                        "image": "ubuntu:24.04",
                    },
                },
                "containers": {
                    "builder": {
                        "image": "builder-img",
                        "workdir": "/workspace",
                        "mounts": [
                            {
                                "source": "${WORKSPACE_ROOT}",
                                "target": "/workspace",
                                "mode": "rw",
                            },
                        ],
                        "env": {
                            "A": "B",
                        },
                        "ports": [
                            "127.0.0.1:10022:22",
                            {
                                "host": 8080,
                                "container": 80,
                                "protocol": "tcp",
                            },
                        ],
                        "devices": [
                            "/dev/kvm",
                        ],
                        "extra_args": [
                            "--pull=never",
                        ],
                    },
                },
            },
        }

    def get_yaml_config(self):
        return self.config

    def substitute_parameters(self, value):
        return value.replace("${WORKSPACE_ROOT}", self.WORKSPACE_ROOT)

    def exec_subprocess(self, cmd, **kwargs):
        self.commands.append(cmd)
        return FakeInspectOutput(self.inspect_exit_code)

    def subprocess_must_succeed(self, cmd, **kwargs):
        self.must_succeed_commands.append(cmd)
        return ""


def test_docker_run_command_uses_container_alias_and_mounts():
    task = FakeTask()

    cmd = docker_runtime.docker_run_command(task, "builder", "echo ok")

    assert task.commands == [["docker", "image", "inspect", "ubuntu:24.04"]]
    assert cmd[:3] == ["docker", "run", "--rm"]
    assert "ubuntu:24.04" in cmd
    assert cmd[-3:] == ["/bin/bash", "-lc", "echo ok"]
    assert "--mount" in cmd
    assert "type=bind,source=/host/workspace,target=/workspace" in cmd
    assert "-w" in cmd
    assert "/workspace" in cmd
    assert "-e" in cmd
    assert "A=B" in cmd
    assert "-p" in cmd
    assert "127.0.0.1:10022:22" in cmd
    assert "8080:80/tcp" in cmd
    assert "--device" in cmd
    assert "/dev/kvm" in cmd
    assert "--pull=never" in cmd


def test_ensure_image_builds_missing_image_from_alias():
    task = FakeTask(inspect_exit_code=1)
    task.config["docker"]["images"]["builder-img"].update(
        {
            "dockerfile": "Dockerfile",
            "context": ".",
            "network": "host",
            "target": "runtime",
            "build_args": {"A": "B"},
        },
    )

    assert docker_runtime.ensure_image(task, "builder-img") == "ubuntu:24.04"
    assert task.must_succeed_commands == [
        [
            "docker",
            "build",
            "-t",
            "ubuntu:24.04",
            "-f",
            "Dockerfile",
            "--network",
            "host",
            "--target",
            "runtime",
            "--build-arg",
            "A=B",
            ".",
        ],
    ]


def test_ensure_image_rejects_missing_build_description():
    task = FakeTask(inspect_exit_code=1)

    with pytest.raises(Exception, match="dockerfile/context"):
        docker_runtime.ensure_image(task, "builder-img")


@pytest.mark.parametrize(
    "config,call,match",
    [
        ({}, lambda task: docker_runtime.image_config(task, "missing"), "image alias"),
        ({}, lambda task: docker_runtime.container_config(task, "missing"), "container alias"),
        (
            {"docker": []},
            lambda task: docker_runtime.container_config(task, "builder"),
            "docker must be an object",
        ),
        (
            {"docker": {"images": []}},
            lambda task: docker_runtime.image_config(task, "builder-img"),
            "docker.images must be an object",
        ),
    ],
)
def test_docker_runtime_rejects_invalid_alias_config(config, call, match):
    task = FakeTask()
    task.config = config

    with pytest.raises(Exception, match=match):
        call(task)


def test_docker_run_command_rejects_invalid_container_fields():
    task = FakeTask()
    task.config["docker"]["containers"]["builder"]["mounts"] = [
        {"source": "/host", "target": "/container", "mode": "bad"},
    ]
    with pytest.raises(Exception, match="mounts\\[0\\].mode"):
        docker_runtime.docker_run_command(task, "builder", "true")

    task = FakeTask()
    task.config["docker"]["containers"]["builder"]["ports"] = [{"host": 1}]
    with pytest.raises(Exception, match="ports\\[0\\]"):
        docker_runtime.docker_run_command(task, "builder", "true")

    task = FakeTask()
    task.config["docker"]["containers"]["builder"]["devices"] = [""]
    with pytest.raises(Exception, match="device"):
        docker_runtime.docker_run_command(task, "builder", "true")
