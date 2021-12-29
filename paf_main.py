'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

from argparse import ArgumentParser
import re

from paf import paf
from paf import common

import xml.etree.ElementTree as ET

class Scenario:
    def __init__(self):
        self.__phases = []
    
    def add_phase(self, phase_name):
        self.__phases.append(phase_name)
    
    def get_phases(self):
        return self.__phases

class Phase:
    def __init__(self):
        self.__tasks = []
    
    def add_task(self, task_name):
        self.__tasks.append(task_name)
    
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
    
    def __execute_task(self, task_name, environment):
        klass = common.create_class_instance(task_name)
        task_instance = klass()
        task_instance.set_environment(environment)
        task_instance.start()
    
    def __execute_phase(self, phase_name, environment):
        phase = self.__available_phases.get(phase_name)
        if phase:
            for task_name in phase.get_tasks():
                self.__execute_task(task_name, environment)
        else:
            raise Exception(f"Phase '{phase_name}' was not found!")
    
    def __execute_scenario(self, scenario_name, environment):
        scenario = self.__available_scenarios.get(scenario_name)
        if scenario:
            for phase_name in scenario.get_phases():
                self.__execute_phase(phase_name, environment)
        else:
            raise Exception(f"Phase '{scenario_name}' was not found!")
    
    def execute(self, environment):
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

def parse_config(config_path, execution_context, environment):
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
                        phase.add_task(task_name)
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
                        scenario.add_phase(phase_name)
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
            parse_config(config_path, execution_context, environment)
    
    # From the command line parse parameters
    parameters = args.parameters
    
    if parameters:
        for parameter in parameters:
            splited_parameter = re.compile("[ ]*=[ ]*").split(parameter)
            if len(splited_parameter) == 2:
                environment.setVariableValue(splited_parameter[0], splited_parameter[1])

    execution_context.execute(environment)

main()