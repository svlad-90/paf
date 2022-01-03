'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

from paf import paf

class LinuxDeploymentTask(paf.SSHLocalClient):
    
    def _get_arch_type(self):
        return self.get_environment_param("ARCH_TYPE")

    def _get_compiler(self):
        compiler = ""
        
        arch_type = self._get_arch_type()
        
        if(arch_type == "ARM"):
            compiler = "${ARM_COMPILER}"
        elif(arch_type == "ARM64"):
            compiler = "${ARM64_COMPILER}"
        else:
            raise Exception("Impossible to determine compiler!")

        return compiler

class prepare_directories(LinuxDeploymentTask):
    
    def __init__(self):
        super().__init__()
        self.set_name(prepare_directories.__name__)
    
    def execute(self):
        
        self.ssh_command_must_succeed("echo '123'")
        
        if self.get_environment_param("CLEAR") == "True":
            self.ssh_command_must_succeed("rm -rf ${ROOT}/${ANDROID_DEPLOYMENT_DIR}")
        
        self.ssh_command_must_succeed("mkdir -p ${ROOT}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${PRODUCT_DIR}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}")

class install_dependencies(LinuxDeploymentTask):
    
    def __init__(self):
        super().__init__()
        self.set_name(install_dependencies.__name__)
    
    def execute(self):
        
        used_compiler = ""
        
        arch_type = self.get_environment_param("ARCH_TYPE")
        
        if(arch_type == "ARM"):
            used_compiler = "${ARM_COMPILER}"
        elif(arch_type == "ARM64"):
            used_compiler = "${ARM64_COMPILER}"
            
        self.ssh_command_must_succeed("sudo apt-get -y install gcc-" + used_compiler + " libssl-dev qemu-system-arm")
        