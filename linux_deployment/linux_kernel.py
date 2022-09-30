'''
Created on Dec 30, 2021

@author: vladyslav_goncharuk
'''

import os
import re

from linux_deployment import general
from paf.paf_impl import logger, CommunicationMode

class LinuxKernelDeploymentTask(general.LinuxDeploymentTask):

    def __init__(self):
        super().__init__()

        self.DOWNLOAD_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}/${ARCH_TYPE}/" + general.LINUX_KERNEL_FOLDER_PREFIX + "${LINUX_KERNEL_VERSION}"
        self.SOURCE_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/" + general.LINUX_KERNEL_FOLDER_PREFIX + "${LINUX_KERNEL_VERSION}"
        self.BUILD_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/" + general.LINUX_KERNEL_FOLDER_PREFIX + "${LINUX_KERNEL_VERSION}"
        self.DEPLOY_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/" + general.LINUX_KERNEL_FOLDER_PREFIX + "${LINUX_KERNEL_VERSION}"

    def _get_linux_kernel_config_target(self):
        target = ""

        arch_type = self._get_arch_type()

        if(arch_type == "ARM"):
            target = "vexpress_defconfig"
        elif(arch_type == "ARM64" or arch_type == "AARCH64"):
            target = "defconfig"
        else:
            target = "defconfig"

        return target

class linux_kernel_sync(LinuxKernelDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_sync.__name__)

    def execute(self):

        self.subprocess_must_succeed(f"mkdir -p {self.DOWNLOAD_PATH}")
        self.subprocess_must_succeed(f"mkdir -p {self.SOURCE_PATH}")
        self.subprocess_must_succeed(f"mkdir -p {self.BUILD_PATH}")
        self.subprocess_must_succeed(f"mkdir -p {self.DEPLOY_PATH}")

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH} && "
            f"( if [ ! -d .git ]; then rm -rf {self.SOURCE_PATH}; fi; )")
        self.subprocess_must_succeed("( cd ${ROOT}/${LINUX_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE} && "
            "git clone -b ${LINUX_KERNEL_VERSION} ${LINUX_KERNEL_GIT_REFERENCE} " + self.SOURCE_PATH + " ) && "
            f"( cd {self.SOURCE_PATH} && " +
            "git checkout tags/${LINUX_KERNEL_VERSION} -b ${LINUX_KERNEL_VERSION} ) || :")

class linux_kernel_clean(LinuxKernelDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_clean.__name__)

    def execute(self):

        arch_type = self._get_arch_type()
        used_compiler = self._get_compiler()

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} ARCH=" +
            arch_type.lower() + " CROSS_COMPILE=" + used_compiler + " distclean",
            communication_mode = CommunicationMode.PIPE_OUTPUT)

class linux_kernel_configure(LinuxKernelDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_configure.__name__)

    def execute(self):

        arch_type = self._get_arch_type()
        used_compiler = self._get_compiler()
        target = self._get_linux_kernel_config_target()

        if not self.has_environment_true_param("LINUX_KERNEL_CONFIGURE_EDIT"):
            self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} ARCH=" + arch_type.lower() +
                " CROSS_COMPILE=" + used_compiler + "- " + target,
                communication_mode = CommunicationMode.PIPE_OUTPUT)

        config_flags_raw = self.get_environment().getVariableValue("LINUX_KERNEL_CONFIG_FLAGS")

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

        config_target = ""

        config_adjustment_mode = self.get_environment_param("LINUX_KERNEL_CONFIG_ADJUSTMENT_MODE")

        if  config_adjustment_mode == "PARAMETERS_ONLY":
            config_target = "savedefconfig"
        elif config_adjustment_mode == "USER_INTERACTIVE":
            config_target = "menuconfig"

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} "
            "ARCH=" + arch_type.lower() + " CROSS_COMPILE=" + used_compiler + "- " + config_target,
            communication_mode = CommunicationMode.PIPE_OUTPUT)

class linux_kernel_build(LinuxKernelDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_build.__name__)

    def execute(self):

        arch_type = self._get_arch_type()
        used_compiler = self._get_compiler()

        additional_params = ""

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} ARCH=" +
            arch_type.lower() + " CROSS_COMPILE=" + used_compiler + "- " + "-j${BUILD_SYSTEM_CORES_NUMBER}" +
            additional_params + " all",
            communication_mode = CommunicationMode.PIPE_OUTPUT)

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}/tools/bootconfig; mkdir -p {self.BUILD_PATH}/tools/bootconfig;" +
            f" make O={self.BUILD_PATH}/tools/bootconfig -C {self.SOURCE_PATH}/tools/bootconfig",
            communication_mode = CommunicationMode.PIPE_OUTPUT)

class linux_kernel_deploy(LinuxKernelDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_deploy.__name__)

    def execute(self):

        self.subprocess_must_succeed(f"rm -rf {self.DEPLOY_PATH}; mkdir -p {self.DEPLOY_PATH};")

        products_folder = "arch/" + self._get_arch_type().lower() + "/boot"

        path_prefix = f"{self.BUILD_PATH}"

        files_list: list = [
            os.path.join( path_prefix, products_folder, "Image" ),
            os.path.join( path_prefix, products_folder, "zImage" ),
            os.path.join( path_prefix, products_folder, "Image.gz" ),
            os.path.join( path_prefix, products_folder, "compressed/vmlinux" ) ]

        for file in files_list:
            self.subprocess_must_succeed(f"cp {file} {self.DEPLOY_PATH}/ || :")

        directories_list: list = [
              os.path.join( path_prefix, products_folder, "dts" )
              ]

        for directory in directories_list:
            self.subprocess_must_succeed(f"cp -r {directory} {self.DEPLOY_PATH}/")

class linux_kernel_run(LinuxKernelDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_run.__name__)

    def execute(self):
        arch_type = self._get_arch_type().lower()

        command: str = ""

        if self.has_non_empty_environment_param("QEMU_CONFIG"):
            command += " " + self.get_environment_param("QEMU_CONFIG")

            if "arm" == arch_type:
                command += f" -kernel " + f"{self.DEPLOY_PATH}" + f"/zImage"
                command += f" -append \"root=/dev/ram rw console=ttyAMA0\""
            elif "arm64" == arch_type or "aarch64" == arch_type:
                command += f" -kernel " + f"{self.DEPLOY_PATH}" + f"/Image"
                command += f" -append \"root=/dev/ram rw console=ttyAMA0\""
        else:
            if "arm" == arch_type:
                command += f" -machine virt"
                command += f" -cpu cortex-a15"
                command += f" -kernel " + f"{self.DEPLOY_PATH}" + f"/zImage"
                command += f" -append \"root=/dev/ram rw console=ttyAMA0\""
            elif "arm64" == arch_type or "aarch64" == arch_type:
                command += f" -machine virt"
                command += f" -cpu cortex-a53"
                command += f" -kernel " + f"{self.DEPLOY_PATH}" + f"/Image"
                command += f" -append \"root=/dev/ram rw console=ttyAMA0"

            command += f" -smp cores=1"
            command += f" -m 512M"
            command += f" -nographic"
            command += f" -serial mon:stdio"
            command += f" -no-reboot"
            command += f" -d guest_errors"

        self.subprocess_must_succeed(f"cd {self.DEPLOY_PATH} && " + self._get_qemu_path() + command)

class linux_kernel_remove(LinuxKernelDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_remove.__name__)

    def execute( self ):
        self.subprocess_must_succeed(f"rm -rf {self.DOWNLOAD_PATH}")
        self.subprocess_must_succeed(f"rm -rf {self.SOURCE_PATH}")
        self.subprocess_must_succeed(f"rm -rf {self.BUILD_PATH}")
        self.subprocess_must_succeed(f"rm -rf {self.DEPLOY_PATH}")