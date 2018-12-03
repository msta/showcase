from archii.api.schemas.integration import IntegrationSchema, \
    IntegrationUpdateSchema
from .utils import success_response


class View:
    def __init__(self, controllers=None):
        self.controllers = controllers

    def get_integrations(self):
        data_locations = self.controllers.get_integrations()
        return IntegrationSchema(many=True).dump_data(data_locations)

    def update_integration(self, integration: IntegrationUpdateSchema):
        data_location = self.controllers.update_integration(integration)
        return IntegrationSchema().dump_data(data_location)

    def integration_upload_view(self, doc_file, name, file_path, tracked_folder):
        result = self.controllers.integration_upload(
            doc_file,
            name,
            file_path,
            tracked_folder
        )
        return success_response(result)

    def create_integration_view(self, integration: IntegrationSchema):
        data_location = self.controllers.create_integration(integration)
        return IntegrationSchema().dump_data(data_location)

    def crawl_integration_view(self, integration_data: IntegrationSchema):
        res = self.controllers.crawl_integration(integration_data)
        return IntegrationSchema().dump_data(res)

    def delete_integration_view(self, integration):
        res = self.controllers.delete_integration(integration)
        return IntegrationSchema(many=True).dump_data(res)
