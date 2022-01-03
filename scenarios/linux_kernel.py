'''
Created on Dec 30, 2021

@author: vladyslav_goncharuk
'''

from scenarios import general

class linux_kernel_sync(general.LinuxDeploymentTask):
    
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_sync.__name__)
    
    def execute(self):
        
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${PRODUCT_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        
        self.ssh_command_must_succeed("(cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE} && " + 
            "git clone ${LINUX_KERNEL_GIT_REFERENCE}) || (cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME} && git pull)")

class linux_kernel_clean(general.LinuxDeploymentTask):
    
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_clean.__name__)
    
    def execute(self):
        
        arch_type = self._get_arch_type()
        used_compiler = self._get_compiler()
            
        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME}; "
                              "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} "
                              "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${UBOOT_FOLDER_NAME} "
                              "ARCH=" + arch_type.lower() + " CROSS_COMPILE=" + used_compiler + " distclean")

class linux_kernel_configure(general.LinuxDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_configure.__name__)

    def execute(self):
        pass

class linux_kernel_build(general.LinuxDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_build.__name__)
        
    def execute(self):
        pass

class linux_kernel_deploy(general.LinuxDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_deploy.__name__)
        
    def execute(self):         
        pass
                