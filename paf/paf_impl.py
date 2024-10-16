'''
Created on Dec 28, 2021

@author: vladyslav_goncharuk
'''

from collections import OrderedDict
import paramiko
import xml.etree.ElementTree as ET
import logging
import coloredlogs
from string import Template
import termios
import tty
import sys
import subprocess
import select
import signal
import errno
import os
import enum
from datetime import datetime
import re

from paf import common
from pickle import NONE
import pty

class logger:
    __log_dir = None
    log_filepath = None
    __logging = logging.getLogger(__name__)
    __logging_to_file = None
    __print_to_file = False
    __messageFormat = "%(asctime)s,%(msecs)03d %(levelname)s %(message)s"
    __simpleFormat = '%(message)s'

    @staticmethod
    def __generate_log_filepath():
        now = datetime.now()
        date_time = now.strftime("%m_%d_%Y_%H_%M_%S")
        return os.path.join(logger.__log_dir, f"paf_{date_time}.log")

    @staticmethod
    def init():

        if logger.log_to_file():

            if logger.__logging_to_file == None:

                logger.__logging_to_file = logging.getLogger(__name__ + "_to_file")
                logger.__logging_to_file.propagate  = False

                logger.log_filepath = logger.__generate_log_filepath()

                file_handler = logging.FileHandler(logger.log_filepath, mode = "w")
                file_handler.setLevel(logging.INFO)
                formatter = logging.Formatter(logger.__messageFormat)
                file_handler.setFormatter(formatter)
                logger.__logging_to_file.addHandler(file_handler)

        coloredlogs.install(level='INFO', logging = logger.__logging,
                    fmt=logger.__messageFormat,
                    milliseconds=True)

    @staticmethod
    def __change_to_simple_formatting():
        for handler in logger.__logging.handlers:
            handler.setFormatter(logger.__simpleFormat)

    @staticmethod
    def __change_to_message_formatting():
        for handler in logger.__logging.handlers:
            handler.setFormatter(logger.__messageFormat)

    @staticmethod
    def non_formatted_info_to_file( msg, *args, **kwargs ):
        logger.__change_to_simple_formatting()
        logger.__logging_to_file.info( msg, *args, **kwargs )
        logger.__change_to_message_formatting()

    @staticmethod
    def non_formatted_warning_to_file( msg, *args, **kwargs ):
        logger.__change_to_simple_formatting()
        logger.__logging_to_file.warn( msg, *args, **kwargs )
        logger.__change_to_message_formatting()

    @staticmethod
    def non_formatted_error_to_file( msg, *args, **kwargs ):
        logger.__change_to_simple_formatting()
        logger.__logging_to_file.error( msg, *args, **kwargs )
        logger.__change_to_message_formatting()

    @staticmethod
    def log_to_file():
        if logger.__log_dir and logger.__log_dir.strip():
            return True
        return False

    @staticmethod
    def set_log_dir(log_dir):
        logger.__log_dir = log_dir

    @staticmethod
    def info(msg, *args, **kwargs):
        logger.__logging.info(msg, *args, **kwargs)

        if logger.log_to_file():
            logger.__logging_to_file.info(msg, *args, **kwargs)

    @staticmethod
    def warning(msg, *args, **kwargs):
        logger.__logging.warning(msg, *args, **kwargs)

        if logger.log_to_file():
            logger.__logging_to_file.warn(msg, *args, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        logger.__logging.error(msg, *args, **kwargs)

        if logger.log_to_file():
            logger.__logging_to_file.error(msg, *args, **kwargs)

class ExecutionMode(enum.Enum):
    PRINT        = 0 # print but do not collect stdout and stderr
    COLLECT_DATA = 1 # print and collect stdin and stderr
    DEV_NULL     = 2 # ignore any output

class InteractionMode(enum.Enum):
    PROCESS_INPUT = 0 # process user input
    IGNORE_INPUT =  1 # ignore user input

# mainly to be used with shell = True
class CommunicationMode(enum.Enum):
    USE_PTY = 0 # redirect output to pseudo-terminal pair. The executed sub-process will think, that it is executed in tty
    PIPE_OUTPUT = 1 # pipe all output without usage of the additional PTY. The executed sub-process will think, that it is NOT running in tty

class Config:
    __DEFAULT_EXECUTION_MODE = ExecutionMode.COLLECT_DATA
    __DEFAULT_INTERACTION_MODE = InteractionMode.PROCESS_INPUT
    __DEFAULT_COMMUNICATION_MODE = CommunicationMode.USE_PTY

    @staticmethod
    def set_default_execution_mode(val):
        Config.__DEFAULT_EXECUTION_MODE = val

    @staticmethod
    def get_default_execution_mode():
        return Config.__DEFAULT_EXECUTION_MODE

    @staticmethod
    def set_default_interaction_mode(val):
        Config.__DEFAULT_INTERACTION_MODE = val

    @staticmethod
    def get_default_interaction_mode():
        return Config.__DEFAULT_INTERACTION_MODE

    @staticmethod
    def set_default_communication_mode(val):
        Config.__DEFAULT_COMMUNICATION_MODE = val

    @staticmethod
    def get_default_communication_mode():
        return Config.__DEFAULT_COMMUNICATION_MODE

class SSHCommandOutput:
    def __init__(self, exec_mode, stdin, stdout, stderr,
                 avoid_printing_command_output,
                 avoid_printing_command_output_reason,
                 interaction_mode):
        self.stdout = ""
        self.stderr = ""

        logger.info(f"Command output:")

        chan = stdin.channel

        # Interactive shell
        if common.isatty(sys.stdin):
            oldtty = termios.tcgetattr(sys.stdin)
        try:
            if common.isatty(sys.stdin):
                tty.setraw(sys.stdin.fileno())
                tty.setcbreak(sys.stdin.fileno())

            log_to_file_cache = ""

            while True:
                try:
                    r, w, e = select.select([chan, sys.stdin], [], [])
                except select.error as e:
                    if e[0] != errno.EINTR: raise

                if chan in r:
                    if chan.recv_ready():

                        nbytes=len(stdout.channel.in_buffer)

                        if nbytes > 0:
                            if chan.recv_ready():
                                output = stdout.read(nbytes)

                                if exec_mode == ExecutionMode.PRINT\
                                or exec_mode == ExecutionMode.COLLECT_DATA:

                                    if not avoid_printing_command_output:
                                        sys.stdout.buffer.write(output)
                                    else:
                                        sys.stdout.buffer.write(avoid_printing_command_output_reason)
                                    sys.stdout.flush()

                                    decoded_output = ""

                                    if logger.log_to_file() or exec_mode == ExecutionMode.COLLECT_DATA:
                                        decoded_output = output.decode(encoding='utf-8', errors='ignore')

                                    if logger.log_to_file():
                                        if decoded_output and decoded_output != "":
                                            if "\n" in decoded_output:
                                                log_to_file_cache = log_to_file_cache + decoded_output
                                                if not avoid_printing_command_output:
                                                    logger.non_formatted_info_to_file(log_to_file_cache.rstrip("\n"))
                                                else:
                                                    logger.non_formatted_info_to_file(avoid_printing_command_output_reason)
                                                log_to_file_cache = ""
                                            else:
                                                log_to_file_cache = log_to_file_cache + decoded_output

                                    if exec_mode == ExecutionMode.COLLECT_DATA:
                                        if decoded_output and decoded_output != "":
                                            self.stdout=self.stdout + decoded_output

                            if chan.recv_stderr_ready():
                                error = stderr.read(nbytes)

                                if exec_mode == ExecutionMode.PRINT\
                                or exec_mode == ExecutionMode.COLLECT_DATA:

                                    decoded_error = error.decode(encoding='utf-8', errors='ignore')

                                    if decoded_error and decoded_error != "":

                                        stripped_error = decoded_error.rstrip("\n")

                                        if logger.log_to_file():
                                            if "\n" in decoded_error:
                                                log_to_file_cache = log_to_file_cache + stripped_error
                                                if not avoid_printing_command_output:
                                                    logger.non_formatted_info_to_file(log_to_file_cache)
                                                else:
                                                    logger.non_formatted_info_to_file(avoid_printing_command_output_reason)
                                                log_to_file_cache = ""
                                            else:
                                                log_to_file_cache = log_to_file_cache + decoded_error

                                        if not avoid_printing_command_output:
                                            logger.error(stripped_error)
                                        else:
                                            logger.error(avoid_printing_command_output_reason)

                                        if exec_mode == ExecutionMode.COLLECT_DATA:
                                            self.stderr=self.stderr + decoded_error

                    if chan.exit_status_ready():
                        if self.stdout:
                            self.stdout = self.stdout.rstrip("\r\n")
                        if self.stderr:
                            self.stderr = self.stderr.rstrip("\r\n")
                        break

                if sys.stdin in r and interaction_mode == InteractionMode.PROCESS_INPUT:
                    bytes_to_read = common.bytes_to_read(sys.stdin)
                    x = sys.stdin.read(bytes_to_read)
                    if len(x) == 0:
                        break
                    stdin.write(x)
                    stdin.flush()
        finally:
            if common.isatty(sys.stdin):
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

        self.exit_code = stdout.channel.recv_exit_status()

class SSHConnection:
    def __init__(self, host, user, port = 22, password = "", key_filename = [], jumphost = None, passphrase = None):
        self.__host = host
        self.__user = user
        self.__password = password
        self.__key_filename = key_filename
        self.__port = port
        self.__connection_key = SSHConnection.create_connection_key(host, user, port)
        self.__passphrase = passphrase
        self.connect(jumphost)

    def connect(self, jumphost = None):

        self.__client = paramiko.SSHClient()
        self.__client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if jumphost:

            jumphost_transport = jumphost.__client.get_transport()
            src_addr = (jumphost.__host, jumphost.__port)
            dest_addr = (self.__host, self.__port)
            jumphost_channel = jumphost_transport.open_channel("direct-tcpip", dest_addr, src_addr)

            self.__client.connect(hostname=self.__host,
                username=self.__user,
                key_filename=self.__key_filename,
                password=self.__password,
                port=self.__port,
                sock = jumphost_channel,
                passphrase = self.__passphrase)
        else:
            self.__client.connect(hostname=self.__host,
                username=self.__user,
                key_filename=self.__key_filename,
                password=self.__password,
                port=self.__port,
                passphrase = self.__passphrase)

        self.__connected = True

        logger.info(f"connection to the {self.__connection_key} was successfully created.")

    def disconnect(self):
        self.__client.close()

        logger.info(f"connection to the {self.__connection_key} was closed.")

    def exec_command(self,
                     cmd,
                     timeout = 0,
                     substitute_params = True,
                     exec_mode = None,
                     params = {},
                     avoid_printing_command = False,
                     avoid_printing_command_reason = "The command contains a sensitive information",
                     avoid_printing_command_output = False,
                     avoid_printing_command_output_reason = "The command output contains a sensitive information",
                     interaction_mode = None):

        if exec_mode == None:
            exec_mode = Config.get_default_execution_mode()

        if interaction_mode == None:
            interaction_mode = Config.get_default_interaction_mode()

        logger.info("-------------------------------------")

        logger.info(f"Executing command on the {self.__connection_key} connection.")
        logger.info(f"Command:")

        if not avoid_printing_command:
            unescaped_cmd = cmd[:]

            if True == substitute_params:
                unescaped_cmd = re.sub(r'\$\$', '$', unescaped_cmd)
                unescaped_cmd = re.sub(r'\{\{', '{', unescaped_cmd)
                unescaped_cmd = re.sub(r'\}\}', '}', unescaped_cmd)

            logger.info(f"{unescaped_cmd}")
        else:
            logger.info(f"{avoid_printing_command_reason}")

        result_cmd = cmd

        if True == substitute_params:
            template = Template(cmd)
            result_cmd = template.substitute(params)
            logger.info(f"Command after parameters substitution:")
            if not avoid_printing_command:
                logger.info(f"{result_cmd}")
            else:
                logger.info(f"{avoid_printing_command_reason}")

        if True == self.__connected:
            terminal_width, terminal_height = common.get_terminal_dimensions()
            stdin, stdout, stderr = common.exec_command(self.__client, result_cmd, timeout,
                                                        terminal_width = terminal_width, terminal_height = terminal_height)

            result = SSHCommandOutput(exec_mode, stdin, stdout, stderr,
                                      avoid_printing_command_output, avoid_printing_command_output_reason,
                                      interaction_mode)

            if result.exit_code == 0:
                logger.info(f"Command was successfully executed. Returned result code is '{result.exit_code}'")
            else:
                logger.error(f"Command has failed with the result code '{result.exit_code}'")

            return result
        else:
            raise Exception(f"Command execution has failed due to absence of connection.")

        logger.info("-------------------------------------")

    @staticmethod
    def create_connection_key(host, user, port):
        return user + "@" + host + ":" + str(port)

    def get_connection_key(self):
        return self.__connection_key

class SSHConnectionCache():

    __instance = None

    def find_or_create_connection(self,
        host,
        user,
        port = 22,
        password = "",
        key_filename = [],
        jumphost = None,
        passphrase = None):
        connection_key = SSHConnection.create_connection_key(host,user,port)
        connection = self.__SSHConnections.get(connection_key)

        if not connection:
            logger.info(f"Creating new connection to the {connection_key}")

            if key_filename:
                logger.info(f"Used SSH keys are: " + str(key_filename))

            if jumphost:
                logger.info("Used jumphost is: " + str(jumphost))

            connection = SSHConnection(host, user, port, password=password,
                key_filename=key_filename, jumphost=jumphost, passphrase=passphrase)
            self.__SSHConnections[connection_key] = connection
        else:
            logger.info(f"Using cached connection to the {connection.get_connection_key()}")

        return connection


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
                     key_filename = [],
                     timeout = 0,
                     substitute_params = True,
                     exec_mode = None,
                     params = {},
                     jumphost = None,
                     passphrase = None,
                     avoid_printing_command = False,
                     avoid_printing_command_reason = "The command contains a sensitive information",
                     avoid_printing_command_output = False,
                     avoid_printing_command_output_reason = "The command output contains a sensitive information",
                     interaction_mode = None):
        if exec_mode == None:
            exec_mode = Config.get_default_execution_mode()

        if interaction_mode == None:
            interaction_mode = Config.get_default_interaction_mode()

        connection = self.find_or_create_connection(host, user, port, password, key_filename, jumphost, passphrase)

        return connection.exec_command(cmd,
                                       timeout,
                                       substitute_params = substitute_params,
                                       exec_mode = exec_mode,
                                       params = params,
                                       avoid_printing_command = avoid_printing_command,
                                       avoid_printing_command_reason = avoid_printing_command_reason,
                                       avoid_printing_command_output = avoid_printing_command_output,
                                       avoid_printing_command_output_reason = avoid_printing_command_output_reason,
                                       interaction_mode = interaction_mode)

def set_tty_mode(fd, when=termios.TCSAFLUSH):
    """Put terminal into a raw mode."""
    mode = tty.tcgetattr(fd)
    mode[tty.IFLAG] = mode[tty.IFLAG] & ~(tty.BRKINT | tty.ICRNL | tty.INPCK | tty.ISTRIP | tty.IXON)
    mode[tty.OFLAG] = mode[tty.OFLAG] & ~(tty.OPOST)
    mode[tty.CFLAG] = mode[tty.CFLAG] & ~(tty.CSIZE | tty.PARENB)
    mode[tty.CFLAG] = mode[tty.CFLAG] | tty.CS8
    mode[tty.LFLAG] = mode[tty.LFLAG] & ~(tty.ECHO | tty.ICANON | tty.IEXTEN | tty.ISIG)
    mode[tty.CC][tty.VMIN] = 1
    mode[tty.CC][tty.VTIME] = 0
    tty.tcsetattr(fd, when, mode)

class SubprocessCommandOutput:
    def __init__(self, exec_mode, sub_process, timeout, communication_mode, master_fd,
                 avoid_printing_command_output, avoid_printing_command_output_reason,
                 interaction_mode):

        self.stdout = ""
        self.stderr = ""
        self.exit_code = 0

        exit_code = None

        if common.isatty(sys.stdin):
            oldtty = termios.tcgetattr(sys.stdin)

        try:

            if common.isatty(sys.stdin):
                set_tty_mode(sys.stdin.fileno())

            if communication_mode == CommunicationMode.USE_PTY:

                log_to_file_cache = ""

                while True:

                    try:

                        r, _, e = select.select([master_fd, sys.stdin], [], [], 0.05)
                    except select.error as e:

                        if e[0] != errno.EINTR: raise

                    if master_fd in r:

                        output = os.read(master_fd, 10240)

                        if exec_mode == ExecutionMode.PRINT\
                        or exec_mode == ExecutionMode.COLLECT_DATA:

                            if not avoid_printing_command_output:
                                output_for_console = output.replace(b'\n',b'\r\n')
                                sys.stdout.buffer.write(output_for_console)
                            else:
                                sys.stdout.buffer.write(bytes(avoid_printing_command_output_reason, encoding='utf-8') + b'\r\n')

                            sys.stdout.flush()

                            decoded_output = ""

                            if logger.log_to_file() or exec_mode == ExecutionMode.COLLECT_DATA:
                                decoded_output = output.decode(encoding='utf-8', errors='ignore')

                            if logger.log_to_file():
                                if decoded_output and decoded_output != "":
                                    if "\n" in decoded_output:
                                        log_to_file_cache = log_to_file_cache + decoded_output
                                        if not avoid_printing_command_output:
                                            logger.non_formatted_info_to_file(log_to_file_cache.rstrip("\n"))
                                        else:
                                            logger.non_formatted_info_to_file(avoid_printing_command_output_reason)
                                        log_to_file_cache = ""
                                    else:
                                        log_to_file_cache = log_to_file_cache + decoded_output

                            if exec_mode == ExecutionMode.COLLECT_DATA:
                                if decoded_output and decoded_output != "":
                                    self.stdout=self.stdout + decoded_output

                    if sys.stdin in r and interaction_mode == InteractionMode.PROCESS_INPUT:

                        x = os.read(sys.stdin.fileno(), 10240)
                        #logger.info("input x - " + str(x) + ";\r")
                        if len(x) == 0:
                            break

                        if x == b'\x03':
                            os.write(master_fd, x)
                            sub_process.wait(1.0)
                            raise KeyboardInterrupt()

                        os.write(master_fd, x)

                    exit_code = sub_process.poll()

                    if exit_code is not None:
                        break

            elif communication_mode == CommunicationMode.PIPE_OUTPUT:

                log_to_file_cache = ""

                while True:

                    try:
                        r, _, e = select.select([sub_process.stdout.fileno(),
                                                 sub_process.stderr.fileno(),
                                                 sys.stdin], [], [])
                    except select.error as e:
                        if e[0] != errno.EINTR: raise

                    if sub_process.stdout.fileno() in r:

                        output = sub_process.stdout.read1()

                        if exec_mode == ExecutionMode.PRINT\
                        or exec_mode == ExecutionMode.COLLECT_DATA:

                            if not avoid_printing_command_output:
                                output_for_console = output.replace(b'\n',b'\r\n')
                                sys.stdout.buffer.write(output_for_console)
                            else:
                                sys.stdout.buffer.write(bytes(avoid_printing_command_output_reason, encoding='utf-8') + b'\r\n')

                            sys.stdout.flush()

                            decoded_output = ""

                            if logger.log_to_file() or exec_mode == ExecutionMode.COLLECT_DATA:
                                decoded_output = output.decode(encoding='utf-8', errors='ignore')

                            if logger.log_to_file():
                                if decoded_output and decoded_output != "":
                                    if "\n" in decoded_output:
                                        log_to_file_cache = log_to_file_cache + decoded_output

                                        if not avoid_printing_command_output:
                                            logger.non_formatted_info_to_file(log_to_file_cache.rstrip("\n"))
                                        else:
                                            logger.non_formatted_info_to_file(avoid_printing_command_output_reason)

                                        log_to_file_cache = ""
                                    else:
                                        log_to_file_cache = log_to_file_cache + decoded_output

                            if exec_mode == ExecutionMode.COLLECT_DATA:
                                if decoded_output and decoded_output != "":
                                    self.stdout=self.stdout + decoded_output

                    if sub_process.stderr.fileno() in r:

                        error = sub_process.stderr.read1()

                        if exec_mode == ExecutionMode.PRINT\
                        or exec_mode == ExecutionMode.COLLECT_DATA:

                            if not avoid_printing_command_output:
                                error_for_console = error.replace(b'\n',b'\r\n')
                                sys.stderr.buffer.write(error_for_console)
                            else:
                                sys.stderr.buffer.write(bytes(avoid_printing_command_output_reason, encoding='utf-8') + b'\r\n')

                            sys.stderr.flush()

                            decoded_error = ""

                            if logger.log_to_file() or exec_mode == ExecutionMode.COLLECT_DATA:
                                decoded_error = error.decode(encoding='utf-8', errors='ignore')

                            if logger.log_to_file():
                                if decoded_error and decoded_error != "":
                                    if "\n" in decoded_error:
                                        log_to_file_cache = log_to_file_cache + decoded_error
                                        if not avoid_printing_command_output:
                                            logger.non_formatted_info_to_file(log_to_file_cache.rstrip("\n"))
                                        else:
                                            logger.non_formatted_info_to_file(avoid_printing_command_output)
                                        log_to_file_cache = ""
                                    else:
                                        log_to_file_cache = log_to_file_cache + decoded_error

                            if exec_mode == ExecutionMode.COLLECT_DATA:
                                if decoded_error and decoded_error != "":
                                    self.stderr=self.stderr + decoded_error

                    if sys.stdin in r and interaction_mode == InteractionMode.PROCESS_INPUT:
                        x = os.read(sys.stdin.fileno(), 10240)
                        #logger.info("input x - " + str(x) + ";\r")
                        if len(x) == 0:
                            break

                        if x == b'\x03':
                            sub_process.stdin.write(x)
                            sub_process.stdin.flush()
                            sub_process.wait(1.0)
                            raise KeyboardInterrupt()

                        sub_process.stdin.write(x)
                        sub_process.stdin.flush()

                    exit_code = sub_process.poll()

                    if exit_code is not None:
                        break
        finally:
            if common.isatty(sys.stdin):
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

        self.exit_code = exit_code

class Subprocess:

    def __init__(self):
        self.subprocess = None

    def __apply_replacements(self, s):
        """Apply the necessary substitutions to a string containing parameters."""
        s = re.sub(r'\$\$', '$', s)  # Replace $$ with $
        s = s.replace('{{', '{')      # Replace {{ with {
        s = s.replace('}}', '}')      # Replace }} with }
        return s

    def exec_subprocess(self,
                        cmd,
                        timeout,
                        substitute_params,
                        shell,
                        exec_mode,
                        communication_mode,
                        master_fd,
                        slave_fd,
                        params,
                        avoid_printing_command,
                        avoid_printing_command_reason,
                        avoid_printing_command_output,
                        avoid_printing_command_output_reason,
                        interaction_mode):

        post_processed_cmd = ""
        str_cmd = ""

        if shell == True:
            if type(cmd) is list:
                for argument in cmd:
                    post_processed_cmd += " " + argument
                post_processed_cmd = post_processed_cmd.strip(" ")
                str_cmd = post_processed_cmd
            elif type(cmd) is str:
                post_processed_cmd = cmd
                str_cmd = cmd
            else:
                raise Exception("The 'cmd' parameter should be of types 'str' ot 'list' when used in a shell mode!")
        else:
            if type(cmd) is list:
                post_processed_cmd = cmd
                for argument in cmd:
                    str_cmd += " " + argument
                str_cmd = str_cmd.strip(" ")
            else:
                raise Exception("The 'cmd' parameter should be of type 'list' when used in a non-shell mode!")

        logger.info("-------------------------------------")

        logger.info(f"Executing sub-process.")
        logger.info(f"Command:")

        if not avoid_printing_command:
            unescaped_cmd = cmd

            if True == substitute_params:
                if shell == True:
                    if isinstance(cmd, str):
                        unescaped_cmd = self.__apply_replacements(cmd)
                    elif isinstance(cmd, list):
                        unescaped_cmd = [self.__apply_replacements(s) for s in cmd]
                    else:
                        raise Exception("The 'cmd' parameter should be of types 'str' ot 'list' when used in a shell mode!")
                else:
                    if isinstance(cmd, list):
                        unescaped_cmd = [self.__apply_replacements(s) for s in cmd]
                    else:
                        raise Exception("The 'cmd' parameter should be of type 'list' when used in a non-shell mode!")

            logger.info(f"{unescaped_cmd}")
        else:
            logger.info(f"{avoid_printing_command_reason}")

        result_cmd = ""
        result_cmd_str = ""

        if True == substitute_params:
            if type(post_processed_cmd) is list:
                result_cmd = []
                for argument in post_processed_cmd:
                    template = Template(argument)
                    result_argument = template.substitute(params)
                    result_cmd.append(result_argument)
                    result_cmd_str += " " + result_argument
                result_cmd_str = result_cmd_str.strip(" ")
            elif type(post_processed_cmd) is str:
                template = Template(cmd)
                result_cmd = template.substitute(params)
                result_cmd_str = result_cmd

            logger.info(f"Command after parameters substitution:")
            if not avoid_printing_command:
                logger.info(f"{result_cmd_str}")
            else:
                logger.info(f"{avoid_printing_command_reason}")
        else:
            result_cmd = cmd

        executable = None

        if shell == True:
            executable = "/bin/bash"

        terminal_width, terminal_height = common.get_terminal_dimensions()
        env = os.environ.copy()

        if shell == True:
            env["COLUMNS"] = str(terminal_width)
            env["LINES"] = str(terminal_height)

        def signal_winsize_handler(signum, frame):
            if signum == signal.SIGWINCH:
                os.kill(sub_process.pid, signal.SIGWINCH)

        old_action = signal.getsignal(signal.SIGWINCH)
        signal.signal(signal.SIGWINCH, signal_winsize_handler)

        if communication_mode == CommunicationMode.USE_PTY:
            try:
                sub_process = subprocess.Popen(result_cmd,
                    shell = shell,
                    stdout = slave_fd,
                    stderr = slave_fd,
                    stdin = slave_fd,
                    executable = executable,
                    env = env)

                try:
                    result = SubprocessCommandOutput(exec_mode, sub_process, timeout, communication_mode, master_fd,
                                                     avoid_printing_command_output, avoid_printing_command_output_reason,
                                                     interaction_mode)
                except:
                    sub_process.kill()
                    raise
            finally:
                signal.signal(signal.SIGWINCH, old_action)
        elif communication_mode == CommunicationMode.PIPE_OUTPUT:
            try:

                sub_process = subprocess.Popen(result_cmd,
                    shell = shell,
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE,
                    stdin = subprocess.PIPE,
                    executable = executable,
                    env = env)

                try:
                    result = SubprocessCommandOutput(exec_mode, sub_process, timeout, communication_mode, None,
                                                     avoid_printing_command_output, avoid_printing_command_output_reason,
                                                     interaction_mode)
                except:
                    sub_process.kill()
                    raise
            finally:
                signal.signal(signal.SIGWINCH, old_action)

        if result.exit_code == 0:
            logger.info(f"Command was successfully executed. Returned result code is '{result.exit_code}'")
        else:
            logger.error(f"Command has failed with the result code '{result.exit_code}'")

        return result

class Environment:
    def __init__(self):
        self.__variables = {}

    def deleteVariableValue(self, key):
        self.__variables.pop(key, None)

    def setVariableValue(self, key, value):
        self.__variables[key] = value

    def getVariableValue(self, key, default_value = None):
        if default_value:
            if self.__variables.has(key):
                return self.__variables.get(key)
            else:
                return default_value
        else:
            return self.__variables.get(key)

    def getVariables(self):
        return self.__variables

    def dump(self):
        for key in self.__variables:
            variable_content = self.__variables[key]

            if " " in variable_content:
                variable_content = '"' + variable_content + '"'

            logger.info(f"export {key}={variable_content}");

class Task:

    __master_fd, __slave_fd = pty.openpty()

    def __init__(self):
        self.__environment = Environment()
        self.__name = ""
        self.__ssh_connection_cache = SSHConnectionCache.getInstance()

    def has_environment_param(self, param_name):
        return param_name in self.__environment.getVariables()

    def has_environment_true_param(self, param_name):
        return param_name in self.__environment.getVariables() \
            and self.__environment.getVariableValue(param_name) == "True"

    def has_non_empty_environment_param(self, param_name):
        return param_name in self.__environment.getVariables() \
            and self.__environment.getVariableValue(param_name)

    def get_environment_param(self, param_name, default_value = None):
        return self.__environment.getVariableValue(param_name, default_value = None)

    def set_environment_param(self, param_name, param_value):
        return self.__environment.setVariableValue(param_name, param_value)

    def delete_environment_param(self, param_name):
        return self.__environment.deleteVariableValue(param_name)

    def init(self):
        pass

    def execute(self):
        pass

    def substitute_parameters(self, cmd):
        template = Template(cmd)
        return template.substitute(self.__dict__)

    def start(self):

        logger.info("-------------------------------------")
        logger.info(f"Starting the task '{self.__name}'. Used environment:");
        self.__environment.dump()

        self.init()
        self.execute()

        logger.info(f"Finished the task '{self.__name}'.");
        logger.info("-------------------------------------")

    def subprocess_must_succeed(self,
                                cmd,
                                timeout = 0,
                                expected_return_codes = [0],
                                substitute_params = True,
                                shell = True,
                                exec_mode = None,
                                communication_mode = None,
                                avoid_printing_command = False,
                                avoid_printing_command_reason = "The command contains a sensitive information",
                                avoid_printing_command_output = False,
                                avoid_printing_command_output_reason = "The command output contains a sensitive information",
                                interaction_mode = None):
        if exec_mode == None:
            exec_mode = Config.get_default_execution_mode()

        if communication_mode == None:
            communication_mode = Config.get_default_communication_mode()

        if interaction_mode == None:
            interaction_mode = Config.get_default_interaction_mode()

        process = Subprocess()
        command_output = process.exec_subprocess(cmd,
                                                 timeout,
                                                 substitute_params,
                                                 shell = shell,
                                                 exec_mode = exec_mode,
                                                 communication_mode = communication_mode,
                                                 master_fd = Task.__master_fd,
                                                 slave_fd = Task.__slave_fd,
                                                 params = self.__dict__,
                                                 avoid_printing_command = avoid_printing_command,
                                                 avoid_printing_command_reason = avoid_printing_command_reason,
                                                 avoid_printing_command_output = avoid_printing_command_output,
                                                 avoid_printing_command_output_reason = avoid_printing_command_output_reason,
                                                 interaction_mode = interaction_mode)

        if not command_output.exit_code in expected_return_codes:
            raise Exception(f"Subprocess should succeed! Expected return codes are: '{expected_return_codes}'. "
                            f"Actual return code: '{command_output.exit_code}'")
        else:
            if command_output.exit_code != 0:
                logger.info(f"Return code '{command_output.exit_code}' fits to the expected return code.")

            return command_output.stdout

    def exec_subprocess(self,
                        cmd,
                        timeout = 0,
                        substitute_params = True,
                        shell = True,
                        exec_mode = None,
                        communication_mode = None,
                        avoid_printing_command = False,
                        avoid_printing_command_reason = "The command contains a sensitive information",
                        avoid_printing_command_output = False,
                        avoid_printing_command_output_reason = "The command output contains a sensitive information",
                        interaction_mode = None):
        if exec_mode == None:
            exec_mode = Config.get_default_execution_mode()

        if communication_mode == None:
            communication_mode = Config.get_default_communication_mode()

        if interaction_mode == None:
            interaction_mode = Config.get_default_interaction_mode()

        process = Subprocess()
        command_output = process.exec_subprocess(cmd,
                                                 timeout,
                                                 substitute_params,
                                                 shell = shell,
                                                 exec_mode = exec_mode,
                                                 master_fd = Task.__master_fd,
                                                 slave_fd = Task.__slave_fd,
                                                 communication_mode = communication_mode,
                                                 params = self.__dict__,
                                                 avoid_printing_command = avoid_printing_command,
                                                 avoid_printing_command_reason = avoid_printing_command_reason,
                                                 avoid_printing_command_output = avoid_printing_command_output,
                                                 avoid_printing_command_output_reason = avoid_printing_command_output_reason,
                                                 interaction_mode = interaction_mode)

        return command_output

    def ssh_command_must_succeed(self,
                             cmd,
                             host,
                             user,
                             port = 22,
                             password = "",
                             key_filename = [],
                             timeout = 0,
                             expected_return_codes = [0],
                             substitute_params = True,
                             exec_mode = None,
                             jumphost = None,
                             passphrase = None,
                             avoid_printing_command = False,
                             avoid_printing_command_reason = "The command contains a sensitive information",
                             avoid_printing_command_output = False,
                             avoid_printing_command_output_reason = "The command output contains a sensitive information",
                             interaction_mode = None):
        if exec_mode == None:
            exec_mode = Config.get_default_execution_mode()

        if interaction_mode == None:
            interaction_mode = Config.get_default_interaction_mode()

        command_output = self.__ssh_connection_cache.exec_command(cmd, host, user, port,
            password = password, key_filename = key_filename, timeout = timeout, substitute_params = substitute_params,
            exec_mode = exec_mode, params = self.__dict__, jumphost = jumphost, passphrase = passphrase,
            avoid_printing_command = avoid_printing_command, avoid_printing_command_reason = avoid_printing_command_reason,
            avoid_printing_command_output = avoid_printing_command_output, avoid_printing_command_output_reason = avoid_printing_command_output_reason,
            interaction_mode = interaction_mode)

        if not command_output.exit_code in expected_return_codes:
            raise Exception(f"SSH command should succeed! Expected return codes are: '{expected_return_codes}'. "
                            f"Actual return code: '{command_output.exit_code}'")
        else:
            if command_output.exit_code != 0:
                logger.info(f"Return code '{command_output.exit_code}' fits to the expected return code.")

            return command_output.stdout

    def exec_ssh_command(self,
                     cmd,
                     host,
                     user,
                     port = 22,
                     password = "",
                     key_filename = [],
                     timeout = 0,
                     substitute_params = True,
                     exec_mode = None,
                     jumphost = None,
                     passphrase = None,
                     avoid_printing_command = False,
                     avoid_printing_command_reason = "The command contains a sensitive information",
                     avoid_printing_command_output = False,
                     avoid_printing_command_output_reason = "The command output contains a sensitive information",
                     interaction_mode = None):
        if exec_mode == None:
            exec_mode = Config.get_default_execution_mode()

        if interaction_mode == None:
            interaction_mode = Config.get_default_interaction_mode()

        command_output = self.__ssh_connection_cache.exec_command(cmd, host, user, port,
            password = password, key_filename = key_filename, timeout = timeout, substitute_params = substitute_params,
            exec_mode = exec_mode, params = self.__dict__, jumphost = jumphost, passphrase = passphrase,
            avoid_printing_command = avoid_printing_command, avoid_printing_command_reason = avoid_printing_command_reason,
            avoid_printing_command_output = avoid_printing_command_output, avoid_printing_command_output_reason = avoid_printing_command_output_reason,
            interaction_mode = interaction_mode)

        return command_output

    def get_name(self):
        return self.__name

    def set_name(self, name):
        self.__name = name

    def get_environment(self):
        return self.__environment

    def set_environment(self, environment):
        self.__environment = environment
        self.__dict__.update(self.__environment.getVariables())

    def fail(self, reason):
        logger.error(f"Failure due to: '" + reason + "'")
        raise Exception(reason)

    def assertion(self, condition, message):
        if not condition:
            self.fail(message)

    # Helper bash commands
    def _get_create_file_marker_command(self, file_path, file_content):
        return "echo " + f"\"{file_content}\"" + " > " + f"{file_path}"

    def _get_file_marker_content_command(self, file_path):
        return f"[ -f {file_path} ] && cat {file_path}"

    def _wrap_command_with_file_marker_condition(self, file_path, cmd, expected_value):
        result = f"MARKER_FILE_CONTENT=$$({self._get_file_marker_content_command(file_path)}); if [ \"$$MARKER_FILE_CONTENT\" != \"{expected_value}\" ]; "\
        f"then {cmd} && "\
        f"{self._get_create_file_marker_command(file_path, expected_value)}; fi;"
        return result

class SSHLocalClient(Task):

    def __init__(self):
        super().__init__()

    def local_ssh_command_must_succeed(self, cmd, timeout = 0, expected_return_codes = [0], substitute_params = True):

        local_host_ip_address = self.get_environment_param("LOCAL_HOST_IP_ADDRESS")
        local_host_user_name = self.get_environment_param("LOCAL_HOST_USER_NAME")
        local_host_system_rsa_key = self.get_environment_param("LOCAL_HOST_SYSTEM_SSH_KEY")
        local_host_system_password = self.get_environment_param("LOCAL_HOST_SYSTEM_PASSWORD")

        return self.ssh_command_must_succeed(cmd, local_host_ip_address, local_host_user_name, 22,
            key_filename = local_host_system_rsa_key, password = local_host_system_password,
            timeout = timeout, expected_return_codes = expected_return_codes,
            substitute_params = substitute_params)

    def exec_local_ssh_command(self, cmd, timeout = 0, substitute_params = True):

        local_host_ip_address = self.get_environment_param("LOCAL_HOST_IP_ADDRESS")
        local_host_user_name = self.get_environment_param("LOCAL_HOST_USER_NAME")
        local_host_system_rsa_key = self.get_environment_param("LOCAL_HOST_SYSTEM_SSH_KEY")
        local_host_system_password = self.get_environment_param("LOCAL_HOST_SYSTEM_PASSWORD")

        return self.exec_ssh_command(cmd, local_host_ip_address, local_host_user_name, 22,
            key_filename = local_host_system_rsa_key, timeout = timeout, password = local_host_system_password,
            substitute_params = substitute_params)

class Scenario:
    def __init__(self):
        self.__phases = []

    def add_phase(self, phase_name, conditions):
        self.__phases.append((phase_name, conditions))

    def get_phases(self):
        return self.__phases

class Phase:
    def __init__(self):
        self.__tasks = []

    def add_task(self, task_name, conditions):
        self.__tasks.append((task_name, conditions))

    def get_tasks(self):
        return self.__tasks

class ExecutionElement:
    ExecutionElementType_Task = 0
    ExecutionElementType_Phase = 1
    ExecutionElementType_Scenario = 2

    def __init__(self, execution_element_type, execution_element_name):
        self.__execution_element_type = execution_element_type
        self.__execution_element_name = execution_element_name

    def get_element_name(self):
        return self.__execution_element_name

    def get_element_type(self):
        return self.__execution_element_type

class ExecutionContext:
    def __init__(self, log_dir = None):
        self.__execution_elements = []
        self.__available_phases = {}
        self.__available_scenarios = {}
        self.__imported_modules = {}

        os.makedirs(log_dir, exist_ok=True)

        logger.set_log_dir(log_dir)
        logger.init()

    def import_modules(self, import_module_dirs):
        self.__imported_modules = common.load_all_modules_in_dirs(import_module_dirs)

    def add_execution_element(self, execution_element_type, execution_element_name):
        execution_element = ExecutionElement(execution_element_type, execution_element_name)
        self.__execution_elements.append(execution_element)

    def add_available_phase(self, phase_name, phase_object):
        self.__available_phases[phase_name] = phase_object

    def add_available_scenario(self, scenario_name, scenario_object):
        self.__available_scenarios[scenario_name] = scenario_object

    def __check_conditions(self, conditions, environment):

        result = True

        for condition_name in conditions:
            environment_variable_value = environment.getVariableValue(condition_name)

            if environment_variable_value:
                if environment_variable_value == conditions[condition_name]:
                    logger.info(f"Condition met: '{condition_name} = {environment_variable_value}'")
                else:
                    logger.info(f"Condition NOT met: '{condition_name} = {conditions[condition_name]}'. "
                                f"Actual value: '{environment_variable_value}'")
                    result = False
            else:
                logger.info(f"Condition NOT met: '{condition_name} = {conditions[condition_name]}'. "
                                 "Parameter does not exist in the environment.")
                result = False

        return result

    def __execute_task(self, task_name, environment):
        klass = common.create_class_instance(task_name, self.__imported_modules)
        task_instance = klass()
        task_instance.set_environment(environment)
        task_instance.start()

    def __execute_phase(self, phase_name, environment):
        phase = self.__available_phases.get(phase_name)
        if phase:
            tasks = phase.get_tasks()
            logger.info(f"Execution context: start execution of the phase '{phase_name}'")
            for task_name, condition in tasks:
                if self.__check_conditions(condition, environment):
                    self.__execute_task(task_name, environment)
                else:
                    logger.warning(f"Skip execution of the task '{task_name}'.")
            logger.info(f"Execution context: execution of the phase '{phase_name}' was finished")
        else:
            raise Exception(f"Phase '{phase_name}' was not found!")

    def __execute_scenario(self, scenario_name, environment):

        scenario = self.__available_scenarios.get(scenario_name)
        if scenario:
            phases = scenario.get_phases()
            logger.info(f"Execution context: start execution of the scenario '{scenario_name}'")
            for phase_name, condition in phases:
                if self.__check_conditions(condition, environment):
                    self.__execute_phase(phase_name, environment)
                else:
                    logger.warning(f"Skip execution of the phase '{phase_name}'.")
            logger.info(f"Execution context: execution of the scenario '{scenario_name}' was finished")
        else:
            raise Exception(f"Scenario '{scenario_name}' was not found!")

    def execute(self, environment):

        logger.info(f"Execution context: start execution")

        for element in self.__execution_elements:
            element_type = element.get_element_type()
            if element_type == ExecutionElement.ExecutionElementType_Task:
                task_name = element.get_element_name()
                self.__execute_task(task_name, environment)
            elif element_type == ExecutionElement.ExecutionElementType_Phase:
                phase_name = element.get_element_name()
                self.__execute_phase(phase_name, environment)
            elif element_type == ExecutionElement.ExecutionElementType_Scenario:
                scenario_name = element.get_element_name()
                self.__execute_scenario(scenario_name, environment)

        logger.info(f"Execution context: finished execution")

    def __parse_conditions(self, base_element):
        conditions = {}

        for child in base_element:
            if child.tag.lower() == "condition":
                condition_name = child.attrib.get("name")

                if condition_name == None:
                    raise Exception("Required attribute 'name' was not found in the 'condition' tag!")

                condition_value = child.attrib.get("value")

                if condition_value == None:
                    raise Exception("Required attribute 'value' was not found in the 'condition' tag!")

                conditions[condition_name] = condition_value
            else:
                raise Exception(f"Unexpected XML tag '${child.tag}'!")

        return conditions

    def parse_config(self, config_path, execution_context, environment):
        logger.info("Attempt to parse config file '" + config_path + "'")
        tree = ET.parse(config_path)
        root = tree.getroot()

        if root and root.tag == "paf_config":
            for child in root:
                if child.tag.lower() == "param":
                    attributes_num = len(child.attrib)
                    if attributes_num == 2:
                        param_name = child.attrib.get("name")
                        if param_name == None:
                            raise Exception("Required attribute 'name' was not found in the 'param' tag!")

                        param_value = child.attrib.get("value")
                        if param_name == None:
                            raise Exception("Required attribute 'value' was not found in the 'param' tag!")

                        environment.setVariableValue(param_name, param_value)
                    else:
                        raise Exception(f"Unexpected number of attributes inside 'param' tag'- ${attributes_num}'! "
                                        "There should be 2 attributes - 'key' and 'value'")
                elif child.tag.lower() == "phase":
                    phase = Phase()

                    phase_name = child.attrib.get("name")
                    if phase_name == None:
                        raise Exception("Required attribute 'name' was not found in the 'phase' tag!")

                    for sub in child:
                        if sub.tag.lower() == "task":
                            task_name = sub.attrib.get("name")
                            if task_name == None:
                                raise Exception("Required attribute 'name' was not found in the 'task' tag!")

                            conditions = self.__parse_conditions(sub)

                            phase.add_task(task_name, conditions)
                            execution_context.add_available_phase(phase_name, phase)
                        else:
                            raise Exception(f"Unexpected XML tag '${sub.tag}'!")
                elif child.tag.lower() == "scenario":
                    scenario = Scenario()

                    scenario_name = child.attrib.get("name")
                    if scenario_name == None:
                        raise Exception("Required attribute 'name' was not found in the 'scenario' tag!")

                    for sub in child:
                        if sub.tag.lower() == "phase":
                            phase_name = sub.attrib.get("name")
                            if phase_name == None:
                                raise Exception("Required attribute 'name' was not found in the 'phase' tag!")

                            conditions = self.__parse_conditions(sub)

                            scenario.add_phase(phase_name, conditions)
                            execution_context.add_available_scenario(scenario_name, scenario)
                        else:
                            raise Exception(f"Unexpected XML tag '${sub.tag}'!")
                else:
                    raise Exception(f"Unexpected XML tag '${child.tag}'!")
        else:
            raise Exception("Wrong XML format! Required root tag paf_config not found")
