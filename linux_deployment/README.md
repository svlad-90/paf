[Go to the previous page](../README.md)

----

# Linux from scratch

----

## Table of content

- [About this repository](#about-this-repository)
- [How to execute?](#how-to-execute)
- [Supported tasks](#supported-tasks)
- [Configuration](#configuration)

----

## About this repository

This page is a sample automation project, which was made with PAF automation framework.

Visit [scenarios.xml](./scenarios.xml) to look at the declared phases, scenarios and parameters.

Visit [general.py](./general.py), [buildroot.py](./buildroot.py), [uboot.py](./uboot.py), [busybox.py](./busybox.py), [linux_kernel.py](./linux_kernel.py) to find implementation of specific tasks.

## How to execute?

Use the following command to execute one of the available tasks:

```bash
# call below from the root PAF folder
python ./paf_main.py -imd ./linux_deployment -c ./linux_deployment/scenarios.xml -t <your_task> -p ARCH_TYPE=<your_architecture> -ld="./"
```

Replace "your_task" with one of the supported tasks ( e.g. linux_deployment.busybox.busybox_sync ), and "your_architecture" with one of the supported architectures ( e.g. ARM64 ).

In order to change the executed scenario, phase or task, type in the command the element from the [scenarios.xml](./scenarios.xml), or fetch task name from the *.py files. Then run the above command with slightly changed parameters.

## Supported tasks

|Task name|Comment|
|---|---|
|linux_deployment.uboot.uboot_sync|Sync uboot source code.|
|linux_deployment.uboot.uboot_configure|Configure uboot. Use [this](./doc/u-boot.txt) manual to get idea of what to configure. Will reset previously configured parameters to the default ones for the selected architecture.|
|linux_deployment.uboot.uboot_configure_edit|Configure uboot without loosing previously configured parameters.|
|linux_deployment.uboot.uboot_build|Build uboot.|
|linux_deployment.uboot.uboot_deploy|Deploy uboot artifacts to the target folder.|
|linux_deployment.uboot.uboot_clean|Clean uboot build.|
|linux_deployment.uboot.uboot_remove|Remove all uboot-related fodlers.|
|linux_deployment.uboot.uboot_run|Run uboot on QEMU.|
|linux_deployment.linux_kernel.linux_kernel_sync|Sync Linux kernel source code.|
|linux_deployment.linux_kernel.linux_kernel_configure|Configure linux kernel. Use [this](./doc/kernel.txt) manual to get idea of what to configure. Will reset previously configured parameters to the default ones for the selected architecture.|
|linux_deployment.linux_kernel.linux_kernel_configure_edit|Configure build without loosing previously configured parameters.|
|linux_deployment.linux_kernel.linux_kernel_build|Build Linux kernel.|
|linux_deployment.linux_kernel.linux_kernel_deploy|Deploy kernel artifacts to the target fodler.|
|linux_deployment.linux_kernel.linux_kernel_clean|Clean kernel build.|
|linux_deployment.linux_kernel.linux_kernel_remove|Remove all kernel-related fodlers.|
|linux_deployment.linux_kernel.linux_kernel_run|Run Linux kernel, using QEMU. As it is started without rootfs and dtb, kernel will certainly panic. This option developed just for the investigation purpose.|
|linux_deployment.busybox.busybox_sync|Sync busybox source code.|
|linux_deployment.busybox.busybox_configure|Configure busybox build. Use [this](./doc/busybox.txt) manual to get idea of what to configure. Will reset previously configured parameters to the default ones for the selected architecture.|
|linux_deployment.busybox.busybox_configure_edit|Configure build without loosing previously configured parameters.|
|linux_deployment.busybox.busybox_build|Build busybox.|
|linux_deployment.busybox.busybox_deploy|Deploy busybox artifacts to the target folder.|
|linux_deployment.busybox.busybox_clean|Clean the busybox build.|
|linux_deployment.busybox.busybox_remove|Remove all busybox-related fodlers.|
|linux_deployment.busybox.busybox_run|Run kernel+busybox on QEMU. Kernel should be built separately with other lfs tasks.|
|linux_deployment.buildroot.buildroot_sync|Sync buildroot source-code.|
|linux_deployment.buildroot.buildroot_configure|Configure buildroot build. Use [this](./doc/buildroot.txt) manual to get idea of what to configure. Will reset previously configured parameters to the default ones for the selected architecture.|
|linux_deployment.buildroot.buildroot_configure_edit|Configure build without loosing previously configured parameters.|
|linux_deployment.buildroot.buildroot_build|Build the buildroot.|
|linux_deployment.buildroot.buildroot_deploy|Deploy buildroot build artifacts to the target folder.|
|linux_deployment.buildroot.buildroot_clean|Cleean buildroot build.|
|linux_deployment.buildroot.buildroot_remove|Remove all buildroot-related folders.|
|linux_deployment.buildroot.buildroot_run|Run kernel+buildroot on QEMU. Kernel should be built separately with other lfs tasks.|
|linux_deployment.system.system_prepare|Installation of the required packages, using 'apt'.|

## Configuration

|Parameter|Comment|
|---|---|
|QEMU_PATH|Folder, in which QEMU binaries are located.|
|QEMU_CONFIG|Custom QEMU config. If not specified, the default one will be used for LFS 'run' commands.|
|ROOT|Root folder of the project. All the other things will be placed inside this folder.|
|LINUX_DEPLOYMENT_DIR|Sub-directory, created inside the 'ROOT'.|
|DOWNLOAD_DIR|The directory, which is used to download the binary artifacts. Located inside the ROOT/LINUX_DEPLOYMENT_DIR.|
|SOURCE_DIR|The directory, which is used to clone git repositories in it. Located inside the ROOT/LINUX_DEPLOYMENT_DIR.|
|BUILD_DIR|The directory, which we try to use for the build. Located inside the ROOT/LINUX_DEPLOYMENT_DIR.|
|DEPLOY_DIR|Will contain all built artifacts. Located inside the ROOT/LINUX_DEPLOYMENT_DIR.|
|ARCH_TYPE|Architecture type, which is used to build and run the projects.|
|XYZ_COMPILER|Compiler, which is used for "XYZ" architecture. Replace "XYZ" with the value, which you've specified in the 'ARCH_TYPE'.|
|XYZ_COMPILER_PATH|Path to compiler folder, which is used for the "XYZ" architecture. Replace "XYZ" with the value, which you've specified in the 'ARCH_TYPE'.|
|BUILD_SYSTEM_CORES_NUMBER|Number of the simultaneous tasks, which you want to run in parallel during the build process.|
|UBOOT_GIT_REFERENCE|Link to the uboot repository.|
|UBOOT_VERSION|Version of the uboot to be used. E.g. 'v2022.07'.|
|UBOOT_CONFIGURE_EDIT|Specifies whether we want to edit already existing config, or to reset it to default values. Expected values - "True" or "False".|
|LINUX_KERNEL_GIT_REFERENCE|Link to the Linux kernel repository.|
|LINUX_KERNEL_VERSION|Version of the kernel to be used. E.g. 'v5.19'.|
|LINUX_KERNEL_CONFIG_ADJUSTMENT_MODE|Specifies, whether to run user interface menuconfig during the configuration step. Expected values are 'USER_INTERACTIVE' or 'PARAMETERS_ONLY'.|
|LINUX_KERNEL_CONFIGURE_EDIT|Specifies whether we want to edit already existing config, or to reset it to default values. Expected values - "True" or "False".|
|BUSYBOX_VERSION|Version of the busybox to be used. E.g. '1.35.0'.|
|BUSYBOX_CONFIG_FLAGS|Pipe separated list of the configuration flags to be automatically applied during configuration step. E.g. 'CONFIG_STATIC=y'.|
|BUSYBOX_CONFIG_ADJUSTMENT_MODE|Specifies, whether to run user interface menuconfig during the configuration step. Expected values are 'USER_INTERACTIVE' or 'PARAMETERS_ONLY'.|
|BUSYBOX_CONFIGURE_EDIT|Specifies whether we want to edit already existing config, or to reset it to default values. Expected values - "True" or "False".|
|BUILDROOT_GIT_REFERENCE|Link to the buildroot repository.|
|BUILDROOT_VERSION|Version of the buildroot to be used, e.g. '2022.05.2'.|
|BUILDROOT_CONFIG_ADJUSTMENT_MODE|Specifies, whether to run user interface menuconfig during the configuration step. Expected values are 'USER_INTERACTIVE' or 'PARAMETERS_ONLY'.|
|BUILDROOT_CONFIGURE_EDIT|Specifies whether we want to edit already existing config, or to reset it to default values. Expected values - "True" or "False".|

----

[Go to the previous page](../README.md)
