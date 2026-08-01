from paf import docker_runtime


class FakeInspectOutput:
    exit_code = 0


class FakeTask:
    WORKSPACE_ROOT = "/host/workspace"

    def __init__(self):
        self.commands = []
        self.config = {
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
        return FakeInspectOutput()


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
