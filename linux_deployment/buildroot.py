'''
Created on Sep 8, 2022

@author: vladyslav_goncharuk
'''

import os
import re

from linux_deployment import general
from paf.paf_impl import logger, CommunicationMode

class BuildrootDeploymentTask(general.LinuxDeploymentTask):

    def __init__(self):
        super().__init__()

        self.DOWNLOAD_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}/${ARCH_TYPE}/" + general.BUILDROOT_FOLDER_PREFIX + "${BUILDROOT_VERSION}"
        self.SOURCE_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/" + general.BUILDROOT_FOLDER_PREFIX + "${BUILDROOT_VERSION}"
        self.BUILD_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/" + general.BUILDROOT_FOLDER_PREFIX + "${BUILDROOT_VERSION}"
        self.DEPLOY_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/" + general.BUILDROOT_FOLDER_PREFIX + "${BUILDROOT_VERSION}"

    def _get_buildroot_config_target(self):
        target = ""

        arch_type = self._get_arch_type()

        if(arch_type == "ARM"):
            target = "qemu_arm_vexpress_defconfig"
        elif(arch_type == "ARM64" or arch_type == "AARCH64"):
            target = "qemu_aarch64_virt_defconfig"
        else:
            target = "defconfig"

        return target

class buildroot_sync(BuildrootDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(buildroot_sync.__name__)

    def execute(self):

        self.subprocess_must_succeed(f"mkdir -p {self.DOWNLOAD_PATH}")
        self.subprocess_must_succeed(f"mkdir -p {self.SOURCE_PATH}")
        self.subprocess_must_succeed(f"mkdir -p {self.BUILD_PATH}")
        self.subprocess_must_succeed(f"mkdir -p {self.DEPLOY_PATH}")

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH} && "
            f"( if [ ! -d .git ]; then rm -rf {self.SOURCE_PATH}; fi; )")
        self.subprocess_must_succeed("( cd ${ROOT}/${LINUX_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE} && "
            "export GIT_SSH_COMMAND=\"ssh -o StrictHostKeyChecking=accept-new\" && "
            "git clone -b ${BUILDROOT_VERSION} ${BUILDROOT_GIT_REFERENCE} " + self.SOURCE_PATH + " ) && "
            f"( cd {self.SOURCE_PATH} && " +
            "git checkout tags/${BUILDROOT_VERSION} -b ${BUILDROOT_VERSION} ) || :")

class buildroot_clean(BuildrootDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(buildroot_clean.__name__)

    def execute(self):
        arch_type = self._get_arch_type()
        used_compiler = self._get_compiler()

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} ARCH=" +
            arch_type.lower() + " CROSS_COMPILE=" + used_compiler + " distclean",
            communication_mode = CommunicationMode.PIPE_OUTPUT)

class buildroot_configure(BuildrootDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(buildroot_configure.__name__)

    def execute(self):
        arch_type = self._get_arch_type()
        used_compiler = self._get_compiler()

        if not self.has_environment_true_param("BUILDROOT_CONFIGURE_EDIT"):
            self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} ARCH=" + arch_type.lower() +
                " CROSS_COMPILE=" + used_compiler + "- " + self._get_buildroot_config_target(),
                communication_mode = CommunicationMode.PIPE_OUTPUT)

        config_flags_raw = self.get_environment().getVariableValue("BUILDROOT_CONFIG_FLAGS")

        config_dict = {}

        if config_flags_raw:

            logger.info(f"config_flags_raw - '{config_flags_raw}'")

            splited_config_flags = re.compile("[ ]*\|[ ]*").split(config_flags_raw)
            config_key_value_pair_regex = re.compile("[ ]*=[ ]*")

            for config_flag in splited_config_flags:

                logger.info(f"Config flag - '{config_flag}'")

                splited_config_key_value = config_key_value_pair_regex.split(config_flag)
                if len(splited_config_key_value) == 2:
                    config_dict[splited_config_key_value[0]] = splited_config_key_value[1]
                    logger.info(f"Parsed key - '{splited_config_key_value[0]}'; parsed value - '{splited_config_key_value[1]}'")

        for config_key in config_dict:
            self.subprocess_must_succeed(f"sed -i -E '/{config_key}(=| )/d' {self.BUILD_PATH}/.config; "
                                          f"echo \'{config_key}={config_dict[config_key]}\' >> " + f"{self.BUILD_PATH}/.config")

        config_adjustment_mode = self.get_environment_param("BUILDROOT_CONFIG_ADJUSTMENT_MODE")

        if  config_adjustment_mode == "PARAMETERS_ONLY":
            pass
        elif config_adjustment_mode == "USER_INTERACTIVE":
            self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} "
            "ARCH=" + arch_type.lower() + " CROSS_COMPILE=" + used_compiler + "- " + 'menuconfig',
            communication_mode = CommunicationMode.PIPE_OUTPUT)

class buildroot_build(BuildrootDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(buildroot_build.__name__)

    def execute(self):

        arch_type = self._get_arch_type()
        used_compiler = self._get_compiler()

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} ARCH=" + arch_type.lower() +
            " CROSS_COMPILE=" + used_compiler + "- -j${BUILD_SYSTEM_CORES_NUMBER} all",
            communication_mode = CommunicationMode.PIPE_OUTPUT)

class buildroot_deploy(BuildrootDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(buildroot_deploy.__name__)

    def execute(self):

        products_folder = "images"

        self.subprocess_must_succeed(f"rm -rf {self.DEPLOY_PATH}; mkdir -p {self.DEPLOY_PATH};")

        files_list: list = [
            os.path.join( f"{self.BUILD_PATH}", products_folder, "Image"),
            os.path.join( f"{self.BUILD_PATH}", products_folder, "zImage"),
            os.path.join( f"{self.BUILD_PATH}", products_folder, "rootfs.ext2"),
            os.path.join( f"{self.BUILD_PATH}", products_folder, "rootfs.tar"),
            os.path.join( f"{self.BUILD_PATH}", products_folder, "rootfs.cpio"),
        ]

        for file in files_list:
            self.subprocess_must_succeed(f"cp {file} {self.DEPLOY_PATH} || :")

class buildroot_run(BuildrootDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(buildroot_run.__name__)

    def execute(self):
        arch_type = self._get_arch_type().lower()

        command: str = ""

        if self.has_non_empty_environment_param("QEMU_CONFIG"):
            command += " " + self.get_environment_param("QEMU_CONFIG")

            if "arm" == arch_type:
                command += f" -kernel " + f"{self.LINUX_KERNEL_IMAGE_PATH}" + f"/zImage"
                command += f" -append \"root=/dev/ram rw console=ttyAMA0\""
            elif "arm64" == arch_type or "aarch64" == arch_type:
                command += f" -kernel " + f"{self.LINUX_KERNEL_IMAGE_PATH}" + f"/Image"
                command += f" -append \"root=/dev/ram rw console=ttyAMA0\""

            command += f" -initrd {self.DEPLOY_PATH}/rootfs.cpio"
        else:
            if "arm" == arch_type:
                command += f" -machine virt"
                command += f" -cpu cortex-a15"
                command += f" -append \"root=/dev/ram rw console=ttyAMA0\""
                command += f" -kernel " + f"{self.LINUX_KERNEL_IMAGE_PATH}" + f"/zImage"
            elif "arm64" == arch_type or "aarch64" == arch_type:
                command += f" -machine virt"
                command += f" -cpu cortex-a53"
                command += f" -append \"root=/dev/ram rw console=ttyAMA0\""
                command += f" -kernel " + f"{self.LINUX_KERNEL_IMAGE_PATH}" + f"/Image"

            command += f" -smp cores=1"
            command += f" -m 512M"
            command += f" -nographic"
            command += f" -serial mon:stdio"
            command += f" -no-reboot"
            command += f" -d guest_errors"
            command += f" -initrd {self.DEPLOY_PATH}/rootfs.cpio"

        self.subprocess_must_succeed(f"cd {self.DEPLOY_PATH} && " + self._get_qemu_path() + command)

class buildroot_remove(BuildrootDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(buildroot_remove.__name__)

    def execute(self):
        self.subprocess_must_succeed(f"rm -rf {self.DOWNLOAD_PATH}")
        self.subprocess_must_succeed(f"rm -rf {self.SOURCE_PATH}")
        self.subprocess_must_succeed(f"rm -rf {self.BUILD_PATH}")
        self.subprocess_must_succeed(f"rm -rf {self.DEPLOY_PATH}")
