'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

from scenarios import general

class uboot_sync(general.LinuxDeploymentTask):
    
    def __init__(self):
        super().__init__()
        self.set_name(uboot_sync.__name__)
    
    def execute(self):
        
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${PRODUCT_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}")
        
        self.ssh_command_must_succeed("(cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE} && " + 
            "git clone ${UBOOT_GIT_REFERENCE}) || (cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} && git pull)")

class uboot_clean(general.LinuxDeploymentTask):
    
    def __init__(self):
        super().__init__()
        self.set_name(uboot_clean.__name__)
    
    def execute(self):
        
        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}; "
                                      "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} "
                                      "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} "
                                      "distclean")


class uboot_configure(general.LinuxDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(uboot_configure.__name__)

    def execute(self):
        
        used_compiler = self._get_compiler()
        target = self._get_target()
        
        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}; "
                                      "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} "
                                      "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} V=1 "
                                      "CROSS_COMPILE=" + used_compiler + "- " + target)

class uboot_build(general.LinuxDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(uboot_build.__name__)
        
    def execute(self):
        
        used_compiler = self._get_compiler()
            
        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}; "
                                      "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} "
                                      "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} V=1 "
                                      "CROSS_COMPILE=" + used_compiler + "- -j${BUILD_SYSTEM_CORES_NUMBER} all")
        
        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}; "
                                      "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} "
                                      "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} V=1 "
                                      "CROSS_COMPILE=" + used_compiler + "- -j${BUILD_SYSTEM_CORES_NUMBER} menuconfig")

class uboot_deploy(general.LinuxDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(uboot_deploy.__name__)
        
    def execute(self):         
        self.ssh_command_must_succeed("cp ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}/u-boot "
            "${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}/")
        self.ssh_command_must_succeed("cp ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}/u-boot.bin "
            "${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}/")

class uboot_run(general.LinuxDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(uboot_run.__name__)
        
    def execute( self ):

        arch_type = self._get_arch_type()

        if arch_type == "ARM":
            self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} && " + 
            "qemu-system-arm -machine ${UBOOT_ARM_MACHINE_TYPE} -nographic -smp 1 "
            "-m 512M -kernel ./u-boot")
        elif arch_type == "ARM64":
            self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} && " + 
            "qemu-system-aarch64 -machine ${UBOOT_ARM64_MACHINE_TYPE} -cpu cortex-a53 -machine type=\"${UBOOT_ARM64_MACHINE_TYPE}\" -nographic -smp 1 "
            "-m 512M -kernel ./u-boot")
        else:
            raise Exception( f"Unsupported architecture {arch_type}" )
                