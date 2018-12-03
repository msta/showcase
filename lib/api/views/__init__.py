from .admin import View as AdminView
from .document import View as DocumentView
from .file import View as FileView
from .group import View as GroupView
from .health_check import View as HealthCheckView
from .integration import View as IntegrationView
from .other import View as OtherView
from .stats import View as StatsView
from .user import View as AuthView


class Views(
    AdminView,
    AuthView,
    DocumentView,
    FileView,
    IntegrationView,
    OtherView,
    HealthCheckView,
    GroupView,
    StatsView
):
    def __init__(self, controllers=None, services=None):
        self.controllers = controllers
        self.services = services
