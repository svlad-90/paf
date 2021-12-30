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

class InstallDependencies(paf.SSHLocalClient):
    
    def __init__(self):
        super().__init__()
        self.set_name(InstallDependencies.__name__)
    
    def execute(self):
        
        used_compiler = ""
        
        arch_type = self.get_environment_param("ARCH_TYPE")
        
        if(arch_type == "ARM"):
            used_compiler = "${ARM_COMPILER}"
        elif(arch_type == "ARM64"):
            used_compiler = "${ARM64_COMPILER}"
            
        self.ssh_command_must_succeed("sudo apt-get -y install gcc-" + used_compiler)
        
        self.ssh_command_must_succeed("sudo apt-get -y install libssl-dev")