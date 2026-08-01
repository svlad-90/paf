'''
Created on Dec 29, 2021

@author: vladyslav_goncharuk
'''

import re
from argparse import ArgumentParser

from paf import paf_impl
from paf import yaml_config
from paf.paf_impl import logger

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
    parser.add_argument("-yc", "--yaml-config", dest="yaml_configs",
                        help="YAML case configuration files", metavar="YAML_CONFIG", action="append")
    parser.add_argument("-ys", "--yaml-schema", dest="yaml_schemas",
                        help="YAML case schema files", metavar="YAML_SCHEMA", action="append")
    parser.add_argument("-yp", "--yaml-parameter", dest="yaml_parameters",
                        help="YAML case override in path=value form", metavar="YAML_PARAM", action="append")
    parser.add_argument("-dyp", "--domain-yaml-parameter", dest="domain_yaml_parameters",
                        help="Domain descriptor override in domain.path=value form", metavar="DOMAIN_YAML_PARAM", action="append")
    parser.add_argument("-p", "--parameter", dest="parameters",
                        help="environment variable", metavar="ENV_VAR", action="append")
    parser.add_argument("-imd", "--import-module-dir", dest="import_module_dirs",
                        help="import module directories", metavar="IMP", action="append")
    parser.add_argument("-ld", "--log-dir", dest="log_dir",
                        help="output of the script will be stored to this directory. If not set - output is not stored.", metavar="LOG_FILE")

    args = parser.parse_args()

    execution_context = paf_impl.ExecutionContext(args.log_dir)

    environment = paf_impl.Environment()

    # Get import module search paths
    import_module_dirs = args.import_module_dirs
    if import_module_dirs:
        execution_context.import_modules(import_module_dirs)

    yaml_domains = yaml_config.discover_domains_with_overrides(import_module_dirs, args.domain_yaml_parameters)

    # From the command line parse the elements, which we need to execute
    tasks = args.tasks
    if tasks:
        for task_name in tasks:
            execution_context.add_execution_element(paf_impl.ExecutionElement.ExecutionElementType_Task, task_name)

    phases = args.phases
    if phases:
        for phase_name in phases:
            execution_context.add_execution_element(paf_impl.ExecutionElement.ExecutionElementType_Phase, phase_name)

    scenarios = args.scenarios
    if scenarios:
        for scenario_name in scenarios:
            execution_context.add_execution_element(paf_impl.ExecutionElement.ExecutionElementType_Scenario, scenario_name)

    # parse configuration files in order to get list of defined scenarios and phases
    configs = args.configs
    if configs:
        for config_path in configs:
            execution_context.parse_config(config_path, execution_context, environment)

    if args.yaml_configs:
        case_config = yaml_config.load_case_config(args.yaml_configs, None)
        case_config = yaml_config.apply_domain_defaults(case_config, yaml_domains)
        yaml_config.apply_yaml_parameters(case_config, args.yaml_parameters)
        schema_paths = yaml_config.resolve_schema_paths(case_config, yaml_domains, args.yaml_schemas)
        yaml_config.validate_case_config(case_config, schema_paths)
        generated_root = args.log_dir or ".paf"
        generated_config_path = yaml_config.write_expanded_config(case_config, generated_root)

        environment.setYamlConfig(case_config)
        environment.setVariableValue("YAML_CONF_FILE", generated_config_path)
        environment.setVariableValue("YAML_CONF_SOURCE_FILES", " ".join(args.yaml_configs))
        if schema_paths:
            environment.setVariableValue("YAML_CONF_SCHEMA_FILES", " ".join(schema_paths))

        for name, value in yaml_config.project_config(case_config).items():
            environment.setVariableValue(name, value)

    # From the command line parse parameters
    parameters = args.parameters

    if parameters:
        for parameter in parameters:
            splited_parameter = re.compile("[ ]*=[ ]*").split(parameter)
            if len(splited_parameter) == 2:
                environment.setVariableValue(splited_parameter[0], splited_parameter[1])

    execution_context.execute(environment)

    logger.info(f"Last trace ...")

main()
