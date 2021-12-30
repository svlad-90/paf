'''
Created on Dec 30, 2021

@author: vladyslav_goncharuk
'''

from paf import paf

class SyncLinuxKernel(paf.SSHLocalClient):
    
    def __init__(self):
        super().__init__()
        self.set_name(SyncLinuxKernel.__name__)
    
    def execute(self):
        
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${PRODUCT_DIR}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${LINUX_KERNEL_FOLDER_NAME}")
        
        #self.ssh_command_must_succeed("(cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR} && " + 
        #    "git clone ${UBOOT_GIT_REFERENCE}) || (cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/u-boot && git pull)")

class ConfigureLinuxKernel(paf.SSHLocalClient):

    def __init__(self):
        super().__init__()
        self.set_name(ConfigureLinuxKernel.__name__)

    def execute(self):
        pass

class BuildLinuxKernel(paf.SSHLocalClient):
    def __init__(self):
        super().__init__()
        self.set_name(BuildLinuxKernel.__name__)
        
    def execute(self):
        pass

class DeployLinuxKernel(paf.SSHLocalClient):
    def __init__(self):
        super().__init__()
        self.set_name(DeployLinuxKernel.__name__)
        
    def execute(self):         
        pass
                