from archii.api.schemas.stats import DocumentStatisticsSchema


class View:
    def __init__(self, controllers=None):
        self.controllers = controllers

    def document_stats(self):
        result_stats = self.controllers.document_stats()
        return DocumentStatisticsSchema().dump_data(result_stats)
