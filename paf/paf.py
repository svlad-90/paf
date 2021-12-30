'''
Created on Dec 28, 2021

@author: vladyslav_goncharuk
'''

import paramiko
import logging

import coloredlogs
from string import Template

logging = logging.getLogger(__name__)

coloredlogs.install(level='INFO', logging = logging,
                    fmt='%(asctime)s,%(msecs)03d %(levelname)s %(message)s',
                    milliseconds=True)

class CommandOutput:
    def __init__(self, stdout, stderr):
        self.stdout = ""
        self.stderr = ""
        
        logging.info(f"Command output:")
        
        for line in iter(stdout.readline, ""):
            if line:
                self.stdout=self.stdout + line
                logging.info(line.rstrip())
        
        self.stdout = self.stdout.rstrip()
        
        self.exit_code = stdout.channel.recv_exit_status()
        
        for line in stderr:
            if line:
                self.stderr=self.stderr + line
                
                if self.exit_code != 0:
                    logging.error(line.rstrip())
                    
        self.stderr = self.stderr.rstrip()

class SSHConnection:
    def __init__(self, host, user, port = 22, password = "", key_filename = ""):
        self.__host = host
        self.__user = user
        self.__password = password
        self.__key_filename = key_filename
        self.__port = port
        self.__connection_key = SSHConnection.create_connection_key(host, user, port)
        self.connect()
    
    def connect(self):
        self.__client = paramiko.SSHClient()
        self.__client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.__client.connect(hostname=self.__host, username=self.__user, key_filename=self.__key_filename, password=self.__password, port=self.__port)
        self.__connected = True
        
        logging.info(f"Conneciton to the {self.__connection_key} was successfully created.")

    def disconnect(self):
        self.__client.close()
        
        logging.info(f"Conneciton to the {self.__connection_key} was closed.")

    def exec_command(self, cmd, timeout = 0, substitute_params = True, environment = {}):
        
        logging.info("-------------------------------------")
        
        logging.info(f"Executing command on the {self.__connection_key} conneciton.")
        logging.info(f"Command:")
        logging.info(f"{cmd}")
        
        result_cmd = cmd
        
        if True == substitute_params:
            template = Template(cmd)
            result_cmd = template.substitute(environment.getVariables())
            logging.info(f"Command after parameters substitution:")
            logging.info(f"{result_cmd}")
        
        if True == self.__connected:
            stdin, stdout, stderr = self.__client.exec_command(result_cmd, timeout)
            
            result = CommandOutput(stdout, stderr)
            
            if result.exit_code == 0:
                logging.info(f"Command was successfully executed. Returned result code is '{result.exit_code}'")
            else:
                logging.error(f"Command has failed with the result code '{result.exit_code}'")
            
            return result
        else:
            raise Exception(f"Command execution has failed dur to absence of connection.")
    
        logging.info("-------------------------------------")
    
    @staticmethod
    def create_connection_key(host, user, port):
        return host + "@" + user + ":" + str(port)
    
    def get_connection_key(self):
        return self.__connection_key
    
class SSHConnectionCache():
    
    __instance = None
    
    @staticmethod
    def getInstance():
        if not SSHConnectionCache.__instance:
            SSHConnectionCache.__instance = SSHConnectionCache()
        return SSHConnectionCache.__instance
    
    def __init__(self):
            self.__SSHConnections = {}
    
    def exec_command(self, 
                     cmd, 
                     host, 
                     user, 
                     port, 
                     password= "", 
                     key_filename = "", 
                     timeout = 0, 
                     substitute_params = True,
                     environment = {}):
        connection_key = SSHConnection.create_connection_key(host,user,port)
        connection = self.__SSHConnections.get(connection_key)
        
        if not connection:
            logging.info(f"Creating new connection to the {SSHConnection.create_connection_key(host, user, port)}")
            connection = SSHConnection(host, user, port, password=password, key_filename=key_filename)
            self.__SSHConnections[connection_key] = connection
        else:
            logging.info(f"Using cached connection to the {connection.get_connection_key()}")
    
        return connection.exec_command(cmd, timeout, substitute_params = substitute_params, environment = environment)

class Environment:
    def __init__(self):
        self.__variables = {}
        
    def setVariableValue(self, key, value):
        self.__variables[key] = value
    
    def getVariableValue(self, key):
        return self.__variables.get(key)
    
    def getVariables(self):
        return self.__variables
    
    def dump(self):
        for key in self.__variables:
            logging.info(f"export {key}={self.__variables[key]}");

class Task:
    def __init__(self):
        self.__environment = Environment()
        self.__name = ""
        self.__ssh_connection_cache = SSHConnectionCache.getInstance()

    def get_environment_param(self, param_name):
        return self.__environment.getVariableValue(param_name)

    def execute(self):
        pass

    def start(self):
        
        logging.info("-------------------------------------")
        logging.info(f"Starting the task '{self.__name}'. Used environment:");
        self.__environment.dump()
        
        self.execute()

        logging.info(f"Finished the task '{self.__name}'.");
        logging.info("-------------------------------------")

    def command_must_succeed(self, 
                             cmd, 
                             host, 
                             user, 
                             port = 22, 
                             password = "", 
                             key_filename = "", 
                             timeout = 0, 
                             expected_return_code = 0,
                             substitute_params = True):
        command_output = self.__ssh_connection_cache.exec_command(cmd, host, user, port, 
            password = password, key_filename = key_filename, timeout = timeout, substitute_params = substitute_params,
            environment = self.__environment)
        
        if command_output.exit_code != expected_return_code:
            raise Exception(f"SSH command should succeed! Expected return code: '{expected_return_code}'. "
                            f"Actual return code: '{command_output.exit_code}'")
        else:
            if command_output.exit_code != 0:
                logging.info(f"Return code '{command_output.exit_code}' fits to the expected return code.")
            
            return command_output.stdout
    
    def exec_command(self, 
                     cmd, 
                     host, 
                     user, 
                     port = 22, 
                     password = "", 
                     key_filename = "", 
                     timeout = 0,
                     substitute_params = True):
        command_output = self.__ssh_connection_cache.exec_command(cmd, host, user, port, 
            password = password, key_filename = key_filename, timeout = timeout, substitute_params = substitute_params,
            environment = self.__environment)
        
        return command_output

    def get_name(self):
        return self.__name
    
    def set_name(self, name):
        self.__name = name

    def get_environment(self):
        return self.__environment
    
    def set_environment(self, environment):
        self.__environment = environment

class SSHLocalClient(Task):
    
    def __init__(self):
        super().__init__()
    
    def ssh_command_must_succeed(self, cmd, timeout = 0, expected_return_code = 0, substitute_params = True):
        return self.command_must_succeed(cmd, "127.0.0.1", "vladyslav_goncharuk", 22, 
            key_filename = "/home/vladyslav_goncharuk/.ssh/id_rsa",
            timeout = timeout, expected_return_code = expected_return_code,
            substitute_params = substitute_params)
    
    def exec_ssh_command(self, cmd, timeout = 0, substitute_params = True):
        return self.exec_command(cmd, "127.0.0.1", "vladyslav_goncharuk", 22, 
            key_filename = "/home/vladyslav_goncharuk/.ssh/id_rsa", timeout = timeout,
            substitute_params = substitute_params)
    