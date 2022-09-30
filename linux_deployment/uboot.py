'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

from linux_deployment import general
from paf.paf_impl import CommunicationMode, logger

class UbootDeploymentTask(general.LinuxDeploymentTask):

    def __init__(self):
        super().__init__()
        self.DOWNLOAD_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}/${ARCH_TYPE}/" + general.UBOOT_FOLDER_PREFIX + "${UBOOT_VERSION}"
        self.SOURCE_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/" + general.UBOOT_FOLDER_PREFIX + "${UBOOT_VERSION}"
        self.BUILD_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/" + general.UBOOT_FOLDER_PREFIX + "${UBOOT_VERSION}"
        self.DEPLOY_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/" + general.UBOOT_FOLDER_PREFIX + "${UBOOT_VERSION}"

    def _get_uboot_config_target(self):
        target = ""

        arch_type = self._get_arch_type()

        if(arch_type == "ARM"):
            target = "qemu_arm_defconfig"
        elif(arch_type == "ARM64"):
            target = "qemu_arm64_defconfig"
        else:
            target = "defconfig"

        return target

class uboot_sync(UbootDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(uboot_sync.__name__)

    def execute(self):

        self.subprocess_must_succeed(f"mkdir -p {self.DOWNLOAD_PATH}")
        self.subprocess_must_succeed(f"mkdir -p {self.SOURCE_PATH}")
        self.subprocess_must_succeed(f"mkdir -p {self.BUILD_PATH}")
        self.subprocess_must_succeed(f"mkdir -p {self.DEPLOY_PATH}")

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH} && "
            f"( if [ ! -d .git ]; then rm -rf {self.SOURCE_PATH}; fi; )")
        self.subprocess_must_succeed("( cd ${ROOT}/${LINUX_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE} && "
            "git clone -b ${UBOOT_VERSION} ${UBOOT_GIT_REFERENCE} " + self.SOURCE_PATH + ") && "
           f"( cd {self.SOURCE_PATH} && " +
            "git checkout tags/${UBOOT_VERSION} -b ${UBOOT_VERSION} ) || :")

class uboot_clean(UbootDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(uboot_clean.__name__)

    def execute(self):
        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} distclean",
                                     communication_mode = CommunicationMode.PIPE_OUTPUT)

class uboot_configure(UbootDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(uboot_configure.__name__)

    def execute(self):

        used_compiler = self._get_compiler()
        target = self._get_uboot_config_target()

        if not self.has_environment_true_param("UBOOT_CONFIGURE_EDIT"):
            self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} V=1 "
                                        "CROSS_COMPILE=" + used_compiler + "- " + target,
                                        communication_mode = CommunicationMode.PIPE_OUTPUT)

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} V=1 "
                                      "CROSS_COMPILE=" + used_compiler + "- -j${BUILD_SYSTEM_CORES_NUMBER} menuconfig",
                                     communication_mode = CommunicationMode.PIPE_OUTPUT)

class uboot_build(UbootDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(uboot_build.__name__)

    def execute(self):

        used_compiler = self._get_compiler()

        self.subprocess_must_succeed(f"cd {self.SOURCE_PATH}; make O={self.BUILD_PATH} -C {self.SOURCE_PATH} V=1 "
                                      "CROSS_COMPILE=" + used_compiler + "- -j${BUILD_SYSTEM_CORES_NUMBER} all",
                                     communication_mode = CommunicationMode.PIPE_OUTPUT)

class uboot_deploy(UbootDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(uboot_deploy.__name__)

    def execute(self):
        self.subprocess_must_succeed(f"rm -rf {self.DEPLOY_PATH}; mkdir -p {self.DEPLOY_PATH};")

        self.subprocess_must_succeed(f"cp {self.BUILD_PATH}/u-boot {self.DEPLOY_PATH}/")
        self.subprocess_must_succeed(f"cp {self.BUILD_PATH}/u-boot.bin {self.DEPLOY_PATH}/")

class uboot_run(UbootDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(uboot_run.__name__)

    def execute( self ):

        arch_type = self._get_arch_type().lower()

        command: str = ""

        if self.has_non_empty_environment_param("QEMU_CONFIG"):
            command += " " + self.get_environment_param("QEMU_CONFIG")
            command += f" -bios ./u-boot.bin"
        else:
            if "arm" == arch_type:
                command += f" -machine virt"
                command += f" -cpu cortex-a15"
            elif "arm64" == arch_type or "aarch64" == arch_type:
                command += f" -machine virt"
                command += f" -cpu cortex-a53"

            command += f" -smp cores=1"
            command += f" -m 512M"
            command += f" -nographic"
            command += f" -serial mon:stdio"
            command += f" -no-reboot"
            command += f" -d guest_errors"
            command += f" -bios ./u-boot.bin"

        self.subprocess_must_succeed(f"cd {self.DEPLOY_PATH} && " + self._get_qemu_path() + command)

class uboot_remove(UbootDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(uboot_remove.__name__)

    def execute( self ):
        self.subprocess_must_succeed(f"rm -rf {self.DOWNLOAD_PATH}")
        self.subprocess_must_succeed(f"rm -rf {self.SOURCE_PATH}")
        self.subprocess_must_succeed(f"rm -rf {self.BUILD_PATH}")
        self.subprocess_must_succeed(f"rm -rf {self.DEPLOY_PATH}")