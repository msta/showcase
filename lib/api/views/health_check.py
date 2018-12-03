from .utils import success_response


class View:

    @staticmethod
    def health_check():
        return success_response('ok')
