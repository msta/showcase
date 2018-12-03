from flask import Response


class View:

    def __init__(self, controllers=None):
        self.controllers = controllers

    def get_file_view(self, user_document_id):
        stream = self.controllers.get_file(user_document_id)
        return Response(stream.getvalue())

    def get_pdf_view(self, user_document_id):
        stream = self.controllers.get_pdf(user_document_id)
        return Response(stream.getvalue())
