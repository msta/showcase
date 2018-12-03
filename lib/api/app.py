import sys
import uuid

from apispec import APISpec
from flasgger import Swagger
from flask import Flask, request, jsonify
from flask_cors import CORS
from marshmallow.exceptions import ValidationError
from werkzeug.contrib.fixers import ProxyFix

API_TITLE = ''
VERSION = '3.2.1b'
PLUGINS = [
    'apispec.ext.flask', 'apispec.ext.marshmallow'
]


def build_some_company_app(configuration, views, database):
    """
    Builds the app from the views and the database
    :param configuration: A valid Archii configuration
    :param views: A valid Archii View class, can be a mixed class of Views.
    :param database: A valid Archii database instance
    :return: A flask API
    """
    app_builder = FlaskApi(database)

    app = app_builder.configure_app(configuration)
    # Cross Origin allowed
    CORS(app)

    blueprints = [
        AdminBP,
        DocumentBP,
        FileBP,
        IntegrationBP,
        OtherBP,
        AuthBP,
        GroupBP,
        StatsBP
    ]

    health_check = HealthCheckBP(views)
    app.register_blueprint(health_check.blueprint)
    bp_instances = []
    for blueprint in blueprints:
        instance = blueprint(views, database)
        app.register_blueprint(instance.blueprint, url_prefix='/api')
        bp_instances.append(instance)

    # Build Swagger Spec
    build_spec(app, bp_instances)

    return app


def build_spec(app, blueprints):
    """
    Builds the OAS specification.
    :param app:
    :param blueprints: The blueprint instances
    :return:
    """

    spec = APISpec(
        title=API_TITLE,
        version=VERSION,
        plugins=PLUGINS,
    )

    def register_operation_helper(spec, operations, blueprint=None, **kwargs):
        """
        Small helper function allowing blueprints to add tags to APISpec
        :param spec: The APISpec
        :param operations: The operations list being processed
        :param blueprint: The Archii blueprint that registered this operation
        """
        blueprint.register_operation_helper(operations)

    spec.register_operation_helper(register_operation_helper)

    with app.app_context():
        # Register all schemas first so references work
        for bp in blueprints:
            bp.register_specs(spec)

    Swagger(app, template=spec.to_dict())


def _print_in_test_env():
    config_mode = config.get().mode
    if config_mode in [config.ENV.TEST, config.ENV.DEVELOPMENT]:
        print(format_exception(sys.exc_info()))  # noqa: T003


class FlaskApi(object):
    """
    Main class for setting up the FlaskAPI. Is run as MVC.
    Responsible for setting global error handlers and configure
    global dependencies.
    """
    setup_executed = False

    def __init__(self, database=None):
        self.setup_executed = False
        self._application = Flask(__name__)
        self.auth = AuthenticationManager(database)
        self.bind_error_handlers()
        self.setup_log_hooks()

    @staticmethod
    def teardown_app():
        """
        Cleans up the app. Only resets the schema now
        but could perform some teardown on the app later
        :return:
        """
        ArchiiSchema.set_default_json_loader(None)
        ArchiiSchema.set_json_serializer(None)

    @staticmethod
    def _setup_schemas():
        """
        Initializes the ArchiiSchema to deserialize json automatically from Flask
        """
        ArchiiSchema.set_default_json_loader(get_json)
        ArchiiSchema.set_json_serializer(jsonify)

    def bind_error_handlers(self):
        @self._application.errorhandler(exceptions.APIError)
        def api_error(error):
            Log().exception(
                "Error occurred while handling request: %s",
                error.message,
                route=request.path,
                status=error.status_code,
                **error.payload
            )
            _print_in_test_env()
            return error_response(error.message, error.status_code, error.payload)

        @self._application.errorhandler(Exception)
        def generic_error(error):
            Log().exception(
                "Error occurred while handling request: %s",
                str(error),
                route=request.path
            )
            _print_in_test_env()
            return error_response(str(error), 500)

        @self._application.errorhandler(ValidationError)
        def validation_error(error):
            return error_response(
                str(error), 400
            )

        @self._application.errorhandler(PermissionDenied)
        def permission_error(error: PermissionDenied):
            Log().info(
                "Permission denied for request: %s",
                str(error),
                route=request.path,
                user_id=error.user_id,
            )
            _print_in_test_env()
            return error_response(error.message, 403)

        @self._application.errorhandler(ResourceNotFound)
        def resource_not_found_error(error):
            return error_response(
                str(error), 404
            )

    def setup_log_hooks(self):
        @self._application.before_request
        def set_log_request_params():
            Log.set(request_id=str(uuid.uuid4()))
            Log.start_timer("request_timer")

        @self._application.after_request
        def log_response(response):
            """
            Try and set the status code of the response.
            might not run if the request fails.
            """
            Log().set(status_code=response.status_code)
            return response

        @self._application.teardown_request
        def log_and_clear(_):
            # Skipping health_checks
            if request.path == '/':
                return

            args = str(request.args.getlist('param'))
            Log().set(method=request.method,
                      path=request.path,
                      endpoint=request.endpoint,
                      args=args)

            sensitive_endpoints = [
                ('/login', 'POST'),
                ('/user', 'UPDATE')
            ]
            skip_json_logging = False
            for endpoint, method in sensitive_endpoints:
                skip_json_logging = (skip_json_logging
                                     or (request.endpoint == endpoint
                                         and request.method == method))

            json = request.get_json(silent=True)
            if not skip_json_logging and json:
                Log.set(request_body=json)

            Log().info("Request logged", add_timer="request_timer")
            Log.delete_timer("request_timer")
            Log.clear()

    def configure_app(self, api_config=None):
        """
        Configures the app with global dependencies and settings
        from the config
        :param api_config:
        :return:
        """
        if not self.setup_executed:
            flask_app = self._application
            api_config = config.get().api_config if not api_config else api_config
            self.auth.disabled = api_config.disable_authentication
            flask_app.config['SECRET_KEY'] = api_config.secret
            flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app)
            self._setup_schemas()
        return self._application
