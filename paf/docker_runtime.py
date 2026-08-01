'''
Docker runtime helpers for PAF tasks.
'''

from paf.paf_impl import CommunicationMode
from paf.paf_impl import InteractionMode
from paf.paf_impl import logger


def _require_mapping(value, description):
    if not isinstance(value, dict):
        raise Exception(f"{description} must be an object")
    return value


def _require_string(value, description):
    if not isinstance(value, str) or not value:
        raise Exception(f"{description} must be a non-empty string")
    return value


def _docker_config(task):
    config = task.get_yaml_config()
    docker_config = config.get("docker", {})
    return _require_mapping(docker_config, "docker")


def _substitute(task, value):
    if isinstance(value, str):
        return task.substitute_parameters(value)
    if isinstance(value, list):
        return [_substitute(task, item) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(task, item) for key, item in value.items()}
    return value


def image_config(task, image_alias):
    images = _require_mapping(_docker_config(task).get("images", {}), "docker.images")
    config = images.get(image_alias)
    if not config:
        raise Exception(f"Docker image alias '{image_alias}' is not defined")
    return _substitute(task, _require_mapping(config, f"docker.images.{image_alias}"))


def container_config(task, container_alias):
    containers = _require_mapping(_docker_config(task).get("containers", {}), "docker.containers")
    config = containers.get(container_alias)
    if not config:
        raise Exception(f"Docker container alias '{container_alias}' is not defined")
    return _substitute(task, _require_mapping(config, f"docker.containers.{container_alias}"))


def ensure_image(task, image_alias):
    config = image_config(task, image_alias)
    image = _require_string(config.get("image"), f"docker.images.{image_alias}.image")

    inspect = task.exec_subprocess(
        ["docker", "image", "inspect", image],
        shell=False,
        communication_mode=CommunicationMode.PIPE_OUTPUT,
        interaction_mode=InteractionMode.IGNORE_INPUT,
        avoid_printing_command_output=True,
        avoid_printing_command_output_reason="Docker image inspect output is hidden",
    )
    if inspect.exit_code == 0:
        logger.info(f"Docker image alias '{image_alias}' is available as '{image}'")
        return image

    dockerfile = config.get("dockerfile")
    context = config.get("context")
    if not dockerfile or not context:
        raise Exception(
            f"Docker image '{image}' for alias '{image_alias}' does not exist "
            "and dockerfile/context are not defined"
        )

    build_cmd = ["docker", "build", "-t", image, "-f", dockerfile]
    if config.get("network"):
        build_cmd.extend(["--network", str(config["network"])])
    if config.get("target"):
        build_cmd.extend(["--target", str(config["target"])])

    for key, value in _require_mapping(config.get("build_args", {}), "build_args").items():
        build_cmd.extend(["--build-arg", f"{key}={value}"])

    build_cmd.append(context)
    task.subprocess_must_succeed(
        build_cmd,
        shell=False,
        communication_mode=CommunicationMode.PIPE_OUTPUT,
        interaction_mode=InteractionMode.IGNORE_INPUT,
    )
    return image


def _mount_args(mounts):
    result = []
    for index, mount in enumerate(mounts or []):
        mount = _require_mapping(mount, f"docker.containers.*.mounts[{index}]")
        source = _require_string(mount.get("source"), f"mounts[{index}].source")
        target = _require_string(mount.get("target"), f"mounts[{index}].target")
        mode = mount.get("mode")
        if mode and mode not in ("ro", "rw"):
            raise Exception(f"mounts[{index}].mode must be 'ro' or 'rw'")
        value = f"type=bind,source={source},target={target}"
        if mode:
            value += f",readonly" if mode == "ro" else ""
        result.extend(["--mount", value])
    return result


def _env_args(env):
    result = []
    for key, value in _require_mapping(env or {}, "docker.containers.*.env").items():
        result.extend(["-e", f"{key}={value}"])
    return result


def _port_args(ports):
    result = []
    for index, port in enumerate(ports or []):
        if isinstance(port, str):
            result.extend(["-p", port])
            continue

        port = _require_mapping(port, f"docker.containers.*.ports[{index}]")
        host_value = port.get("host")
        container_value = port.get("container")
        if host_value is None or container_value is None:
            raise Exception(f"ports[{index}] must define host and container")
        host = _require_string(str(host_value), f"ports[{index}].host")
        container = _require_string(str(container_value), f"ports[{index}].container")
        protocol = port.get("protocol")
        value = f"{host}:{container}"
        if protocol:
            value += f"/{protocol}"
        result.extend(["-p", value])
    return result


def _device_args(devices):
    result = []
    for device in devices or []:
        result.extend(["--device", _require_string(device, "device")])
    return result


def docker_run_command(task, container_alias, cmd):
    config = container_config(task, container_alias)
    image_alias = _require_string(config.get("image"), f"docker.containers.{container_alias}.image")
    image = ensure_image(task, image_alias)

    result = ["docker", "run", "--rm"]
    if config.get("name"):
        result.extend(["--name", str(config["name"])])
    if config.get("privileged"):
        result.append("--privileged")
    if config.get("user"):
        result.extend(["--user", str(config["user"])])
    if config.get("workdir"):
        result.extend(["-w", str(config["workdir"])])

    result.extend(_mount_args(config.get("mounts", [])))
    result.extend(_env_args(config.get("env", {})))
    result.extend(_port_args(config.get("ports", [])))
    result.extend(_device_args(config.get("devices", [])))
    result.extend(config.get("extra_args", []))
    result.extend([image, "/bin/bash", "-lc", cmd])
    return result
