'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

import general
from paf.paf_impl import Task

LINUX_KERNEL_FOLDER_PREFIX = "lk_"
BUSYBOX_FOLDER_PREFIX = "bb_"
UBOOT_FOLDER_PREFIX = "ub_"
BUILDROOT_FOLDER_PREFIX = "br_"

class LinuxDeploymentTask(Task):

    def __init__(self):
        super().__init__()
        self.LINUX_KERNEL_IMAGE_PATH = "${ROOT}/${LINUX_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/" + general.LINUX_KERNEL_FOLDER_PREFIX + "${LINUX_KERNEL_VERSION}"

    def _get_arch_type(self):
        return self.get_environment_param("ARCH_TYPE")

    def _get_compiler(self):
        arch_type = self._get_arch_type()
        return "${" + arch_type + "_COMPILER}"

    def _get_compiler_path(self):
        arch_type = self._get_arch_type()
        return "${" + arch_type + "_COMPILER_PATH}"

    def _get_qemu_executable_name(self):

        prefix = ""

        if self.has_non_empty_environment_param("QEMU_FOLDER"):
            prefix = self.get_environment_param("QEMU_FOLDER") + "/"

        arch_type = self._get_arch_type().lower()
        if "x86" == arch_type:
            return prefix + "qemu-system-x86_64"
        elif "x86_64" == arch_type:
            return prefix + "qemu-system-x86_64"
        elif "arm" == arch_type or "arm32" == arch_type:
            return prefix + "qemu-system-arm"
        elif "arm64" == arch_type or "aarch64" == arch_type:
            return prefix + "qemu-system-aarch64"

class prepare_directories(LinuxDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(prepare_directories.__name__)

    def execute(self):
        if self.get_environment_param("CLEAR") == "True":
            self.subprocess_must_succeed("rm -rf ${ROOT}/${LINUX_DEPLOYMENT_DIR}")

        self.subprocess_must_succeed("mkdir -p ${ROOT}")
        self.subprocess_must_succeed("mkdir -p ${ROOT}/${LINUX_DEPLOYMENT_DIR}")
        self.subprocess_must_succeed("mkdir -p ${ROOT}/${LINUX_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}")
        self.subprocess_must_succeed("mkdir -p ${ROOT}/${LINUX_DEPLOYMENT_DIR}/${SOURCE_DIR}")
        self.subprocess_must_succeed("mkdir -p ${ROOT}/${LINUX_DEPLOYMENT_DIR}/${BUILD_DIR}")
        self.subprocess_must_succeed("mkdir -p ${ROOT}/${LINUX_DEPLOYMENT_DIR}/${DEPLOY_DIR}")

class install_dependencies(LinuxDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(install_dependencies.__name__)

    def execute(self):
        self.subprocess_must_succeed("sudo -S apt-get -y install gcc-" + self._get_compiler() + " libssl-dev qemu-system-arm")
