'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

from paf import paf

class PrepareDirectories(paf.SSHLocalClient):
    
    def __init__(self):
        super().__init__()
        self.set_name(PrepareDirectories.__name__)
    
    def execute(self):
        
        if self.get_environment_param("CLEAR") == "True":
            self.ssh_command_must_succeed("rm -rf ${ROOT}/${ANDROID_DEPLOYMENT_DIR}")
        
        self.ssh_command_must_succeed("mkdir -p ${ROOT}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${PRODUCT_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}")