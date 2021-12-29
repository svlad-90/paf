'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

from paf import paf

class InstallARMToolchain(paf.SSHLocalClient):
    
    def __init__(self):
        super().__init__()
        self.set_name(InstallARMToolchain.__name__)
    
    def execute(self):
        
        used_compiler = ""
        
        arch_type = self.get_environment_param("ARCH_TYPE")
        
        if(arch_type == "ARM"):
            used_compiler = "${ARM_COMPILER}"
        elif(arch_type == "ARM64"):
            used_compiler = "${ARM64_COMPILER}"
            
        self.ssh_command_must_succeed("sudo apt-get -y install gcc-" + used_compiler)