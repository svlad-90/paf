'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

from argparse import ArgumentParser
import re

import logging
import coloredlogs

logging = logging.getLogger(__name__)

coloredlogs.install(level='INFO', logging = logging,
                    fmt='%(asctime)s,%(msecs)03d %(levelname)s %(message)s',
                    milliseconds=True)

from paf import paf
from paf import common

import xml.etree.ElementTree as ET

class Scenario:
    def __init__(self):
        self.__phases = {}
 
    def add_phase(self, phase_name, conditions):
        self.__phases[phase_name] = conditions
 
    def get_phases(self):
        return self.__phases

class Phase:
    def __init__(self):
        self.__tasks = {}
 
    def add_task(self, task_name, conditions):
        self.__tasks[task_name] = conditions
 
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
    def __init__(self):
        self.__execution_elements = []
        self.__available_tasks = []
        self.__available_phases = {}
        self.__available_scenarios = {}
 
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
                    logging.info(f"Condition met: {condition_name}={environment_variable_value}")
                else:
                    logging.info(f"Condition NOT met: {condition_name}={conditions[condition_name]}. "
                                 "Actual value = {environment_variable_value}")
                    result = False
            else:
                logging.info(f"Condition NOT met: {condition_name}={conditions[condition_name]}. "
                                 "Parameter does not exist in the environment.")
                result = False
            
        return result

    def __execute_task(self, task_name, environment):
        klass = common.create_class_instance(task_name)
        task_instance = klass()
        task_instance.set_environment(environment)
        task_instance.start()
 
    def __execute_phase(self, phase_name, environment):
        phase = self.__available_phases.get(phase_name)
        if phase:
            tasks = phase.get_tasks()
            for task_name in tasks:
                if self.__check_conditions(tasks[task_name], environment):
                    logging.info(f"Execution context: start execution of the phase '{phase_name}'")
                    self.__execute_task(task_name, environment)
                    logging.info(f"Execution context: execution of the phase '{phase_name}' was finished")
                else:
                    logging.warning(f"Skip execution of the task '{task_name}'.")
        else:
            raise Exception(f"Phase '{phase_name}' was not found!")
 
    def __execute_scenario(self, scenario_name, environment):

        scenario = self.__available_scenarios.get(scenario_name)
        if scenario:
            phases = scenario.get_phases()
            for phase_name in phases:
                if self.__check_conditions(phases[phase_name], environment):
                    logging.info(f"Execution context: start execution of the scenario '{scenario_name}'")
                    self.__execute_phase(phase_name, environment)
                    logging.info(f"Execution context: execution of the scenario '{scenario_name}' was finished")
                else:
                    logging.warning(f"Skip execution of the phase '{phase_name}'.")
        else:
            raise Exception(f"Phase '{scenario_name}' was not found!")
 
    def execute(self, environment):
 
        logging.info(f"Execution context: start execution")
 
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
 
        logging.info(f"Execution context: finished execution")

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

def main():
    parser = ArgumentParser()
    parser.add_argument("-t", "--task", dest="tasks",
                        help="task to be executed", metavar="TASK", action="append")
    parser.add_argument("-s", "--scenario", dest="scenarios",
                        help="scenarios to be executed", metavar="SCENARIO", action="append")
    parser.add_argument("-ph", "--phase", dest="phases",
                        help="phases to be executed", metavar="PHASE", action="append")
    parser.add_argument("-c", "--config", dest="configs",
                        help="configuration files", metavar="CONFIG", action="append")
    parser.add_argument("-p", "--parameter", dest="parameters",
                        help="environment variable", metavar="ENV_VAR", action="append")
 
    execution_context = ExecutionContext()
 
    args = parser.parse_args()
 
    environment = paf.Environment()
 
    # From the command line parse the elements, which we need to execute
    tasks = args.tasks
    if tasks:
        for task_name in tasks:
            execution_context.add_execution_element(ExecutionElement.ExecutionElementType_Task, task_name)
 
    phases = args.phases
    if phases:
        for phase_name in phases:
            execution_context.add_execution_element(ExecutionElement.ExecutionElementType_Phase, phase_name)
 
    scenarios = args.scenarios
    if scenarios:
        for scenario_name in scenarios:
            execution_context.add_execution_element(ExecutionElement.ExecutionElementType_Scenario, scenario_name)
 
    # parse configuration files in order to get list of defined scenarios and phases
    configs = args.configs
    if configs:
        for config_path in configs:
            execution_context.parse_config(config_path, execution_context, environment)
 
    # From the command line parse parameters
    parameters = args.parameters
 
    if parameters:
        for parameter in parameters:
            splited_parameter = re.compile("[ ]*=[ ]*").split(parameter)
            if len(splited_parameter) == 2:
                environment.setVariableValue(splited_parameter[0], splited_parameter[1])

    execution_context.execute(environment)

    logging.info(f"Last trace ...")

main()