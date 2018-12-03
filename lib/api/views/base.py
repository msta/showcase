class BaseView(object):
    schemas = []

    def __init__(self, controllers=None, services=None):
        self.controllers = controllers
        self.services = services

    def add_schemas(self):
        pass

    def _add_schemas(self, schemas):
        self.schemas.extend(schemas)
