'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

from paf import paf

class SyncUBoot(paf.SSHLocalClient):
    
    def __init__(self):
        super().__init__()
        self.set_name(SyncUBoot.__name__)
    
    def execute(self):
        
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}/${UBOOT_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${UBOOT_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${UBOOT_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${PRODUCT_DIR}/${UBOOT_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${UBOOT_FOLDER_NAME}")
        
        self.ssh_command_must_succeed("(cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR} && " + 
            "git clone ${UBOOT_GIT_REFERENCE}) || (cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/u-boot && git pull)")
        
        self.ssh_command_must_succeed("sudo apt-get -y install libssl-dev")

class ConfigureUBoot(paf.SSHLocalClient):

    def __init__(self):
        super().__init__()
        self.set_name(ConfigureUBoot.__name__)

    def execute(self):
        
        used_compiler = ""
        target = ""
        
        arch_type = self.get_environment_param("ARCH_TYPE")
        
        if(arch_type == "ARM"):
            used_compiler = "${ARM_COMPILER}"
            target = "${UBOOT_CONFIG_TARGET_ARM}"
        elif(arch_type == "ARM64"):
            used_compiler = "${ARM64_COMPILER}"
            target = "${UBOOT_CONFIG_TARGET_ARM64}"
        else:
            target = "defconfig"
        
        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${UBOOT_FOLDER_NAME}; "
                                      "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${UBOOT_FOLDER_NAME} "
                                      "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${UBOOT_FOLDER_NAME} V=1 "
                                      "CROSS_COMPILE=" + used_compiler + "- " + target)

class BuildUBoot(paf.SSHLocalClient):
    def __init__(self):
        super().__init__()
        self.set_name(BuildUBoot.__name__)
        
    def execute(self):
        arch_type = self.get_environment_param("ARCH_TYPE")
            
        if(arch_type == "ARM"):
            used_compiler = "${ARM_COMPILER}"
        elif(arch_type == "ARM64"):
            used_compiler = "${ARM64_COMPILER}"
        else:
            raise Exception(f"Not expected arch type '{arch_type}'")
            
        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${UBOOT_FOLDER_NAME}; "
                                      "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${UBOOT_FOLDER_NAME} "
                                      "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${UBOOT_FOLDER_NAME} V=1 "
                                      "CROSS_COMPILE=" + used_compiler + "- -j${BUILD_SYSTEM_CORES_NUMBER} all")

class DeployUBoot(paf.SSHLocalClient):
    def __init__(self):
        super().__init__()
        self.set_name(DeployUBoot.__name__)
        
    def execute(self):         
      self.ssh_command_must_succeed("cp ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${UBOOT_FOLDER_NAME}/u-boot "
                                    "${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${UBOOT_FOLDER_NAME}/")
      self.ssh_command_must_succeed("cp ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${UBOOT_FOLDER_NAME}/u-boot.bin "
                                    "${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${UBOOT_FOLDER_NAME}/")   
                