'''
Created on Dec 28, 2021

@author: vladyslav_goncharuk
'''

import importlib

def create_class_instance(full_class_name):
    try:
        module_path, class_name = full_class_name.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(full_class_name)