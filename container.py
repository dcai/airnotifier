import inspect


class Container:
    def __init__(self, system_data):
        for component_name, component_class, component_args in system_data:
            if inspect.isclass(component_class):
                args = [self.__dict__[arg] for arg in component_args]
                self.__dict__[component_name] = component_class(*args)
            else:
                self.__dict__[component_name] = component_class


class Person:
    def __init__(self, name):
        self.name = name


SYSTEM_DATA = (
    ("name", "hello world", None),
    ("person", Person, ("name",)),
    #  ('lister', MovieLister, ('finder', )),
)

c = Container(SYSTEM_DATA)
