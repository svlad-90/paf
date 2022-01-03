'''
Created on Dec 30, 2021

@author: vladyslav_goncharuk
'''

import os
import re

from scenarios import general
from paf.paf import logging

class LinuxKernelDeploymentTask(general.LinuxDeploymentTask):
    def _get_linux_kernel_config_target(self):
        target = ""
        
        arch_type = self._get_arch_type()
        
        if(arch_type == "ARM"):
            target = "${LINUX_KERNEL_CONFIG_TARGET_ARM}"
        elif(arch_type == "ARM64"):
            target = "${LINUX_KERNEL_CONFIG_TARGET_ARM64}"
        else:
            raise Exception(f"Can't determine config target for architecture '${arch_type}'")

        return target
    
    def _get_linux_kernel_build_target(self):
        return self.get_environment_param("LINUX_KERNEL_BUILD_TARGET")
    
class linux_kernel_sync(LinuxKernelDeploymentTask):
    
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_sync.__name__)
    
    def execute(self):
        
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DOWNLOAD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        self.ssh_command_must_succeed("mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        
        self.ssh_command_must_succeed("(cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE} && " + 
            "git clone ${LINUX_KERNEL_GIT_REFERENCE}) || (cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME} && git pull)")

class linux_kernel_clean(LinuxKernelDeploymentTask):
    
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

class linux_kernel_configure(LinuxKernelDeploymentTask):

    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_configure.__name__)

    def execute(self):
    
        arch_type = self._get_arch_type()
        used_compiler = self._get_compiler()
        target = self._get_linux_kernel_config_target()
        
        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}; "
            "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME} "
            "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME} "
            "ARCH=" + arch_type.lower() + " CROSS_COMPILE=" + used_compiler + "- " + target)

        config_flags_raw = self.get_environment().getVariableValue("LINUX_KERNEL_CONFIG_FLAGS")
        
        config_dict = {}
        
        if config_flags_raw:
            
            logging.info(f"config_flags_raw - '{config_flags_raw}'")
            
            splited_config_flags = re.compile("[ ]*\|[ ]*").split(config_flags_raw)
            
            config_key_value_pair_regex = re.compile("[ ]*=[ ]*")
            
            for config_flag in splited_config_flags:
                
                logging.info(f"Config flag - '{config_flag}'")
                
                splited_config_key_value = config_key_value_pair_regex.split(config_flag)
                
                if len(splited_config_key_value) == 2:
                    config_dict[splited_config_key_value[0]] = splited_config_key_value[1]
                    logging.info(f"Parsed key - '{splited_config_key_value[0]}'; parsed value - '{splited_config_key_value[1]}'")
            
        for config_key in config_dict:
            self.ssh_command_must_succeed(f"sed -i -E '/{config_key}(=| )/d' "
                                          "${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}/.config; "
                                          f"echo \'{config_key}={config_dict[config_key]}\' >> "
                                          "${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}/.config")

        config_target = ""

        config_adjustment_mode = self.get_environment_param("LINUX_KERNEL_CONFIG_ADJUSTMENT_MODE")

        if  config_adjustment_mode == "PARAMETERS_ONLY":
            config_target = "savedefconfig"
        elif config_adjustment_mode == "USER_INTERACTIVE":
            config_target = "menuconfig"

        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}; "
            "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME} "
            "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME} "
            "ARCH=" + arch_type.lower() + " CROSS_COMPILE=" + used_compiler + "- " + config_target)
        
class linux_kernel_build(LinuxKernelDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_build.__name__)
        
    def execute(self):
        
        build_target = self._get_linux_kernel_build_target()
        arch_type = self._get_arch_type()
        used_compiler = self._get_compiler()
        
        additional_params = ""
        
        if build_target == "modules_install":
            # https://www.kernel.org/doc/Documentation/kbuild/modules.txt
            additional_params.append(" INSTALL_MOD_PATH=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}")
        elif build_target == "uImage":
            additional_params.append( " LOADADDR=0x10000" )

        self.ssh_command_must_succeed("cd ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}; "
            "make O=${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME} "
            "-C ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${SOURCE_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME} "
            "ARCH=" + arch_type.lower() + " CROSS_COMPILE=" + used_compiler + "- " + build_target + 
            " -j${BUILD_SYSTEM_CORES_NUMBER}" + additional_params)

class linux_kernel_deploy(LinuxKernelDeploymentTask):
    def __init__(self):
        super().__init__()
        self.set_name(linux_kernel_deploy.__name__)
        
    def execute(self):
        
        self.ssh_command_must_succeed("rm -rf ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME};"
            "mkdir -p ${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME};")

        products_folder = "arch/" + self._get_arch_type().lower() + "/boot"

        path_prefix = "${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${BUILD_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}"

        files_list: list = [
            os.path.join( path_prefix, products_folder, "Image" ),
            os.path.join( path_prefix, products_folder, "zImage" ),
            os.path.join( path_prefix, products_folder, "Image.gz" ),
            os.path.join( path_prefix, products_folder, "compressed/vmlinux" ) ]

        for file in files_list:
            self.ssh_command_must_succeed(f"cp {file} " + "${ROOT}/${ANDROID_DEPLOYMENT_DIR}/${DEPLOY_DIR}/${ARCH_TYPE}/${LINUX_KERNEL_FOLDER_NAME}/ || :")
                