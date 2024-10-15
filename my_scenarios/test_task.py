from paf.paf_impl import logger, Task, Config
from paf.paf_impl import ExecutionMode, InteractionMode, CommunicationMode

class JenkinsTask(Task):
    def __init__(self):
        super().__init__()

    def init(self):
        Config.set_default_execution_mode(ExecutionMode.COLLECT_DATA)
        Config.set_default_interaction_mode(InteractionMode.IGNORE_INPUT)
        Config.set_default_communication_mode(CommunicationMode.PIPE_OUTPUT)

class InstallDocker(JenkinsTask):

    def __init__(self):
        super().__init__()
        self.set_name(InstallDocker.__name__)

    def execute(self):
        logger.info("Starting Docker installation...")
        self.subprocess_must_succeed("sudo apt-get update")
        self.subprocess_must_succeed("sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common")
        self.subprocess_must_succeed("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -")
        self.subprocess_must_succeed("sudo add-apt-repository \"deb [arch=amd64] https://download.docker.com/linux/ubuntu $$(lsb_release -cs) stable\"")
        self.subprocess_must_succeed("sudo apt-get update")
        self.subprocess_must_succeed("sudo apt-get install -y docker-ce")
        logger.info("Docker installed successfully"); print("[INFO] Docker installed successfully")

class RunHelloWorld(JenkinsTask):

    def __init__(self):
        super().__init__()
        self.set_name(RunHelloWorld.__name__)

    def execute(self):
        logger.info("Starting Docker Hello World test..."); print("[INFO] Starting Docker Hello World test...")
        output = self.subprocess_must_succeed("sudo docker run hello-world")
        logger.info(f"Docker hello-world output: {output}"); print(f"[INFO] Docker hello-world output: {output}")
