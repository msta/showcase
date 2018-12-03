from functools import wraps

from flask import Response, g, request


def authenticate_response():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials\n', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


def get_user():
    return g.user


class AuthenticationManager:
    """
    flask helper class. wraps authentication
    and sends an auth-enabling response
    """

    def __init__(self, database, api_config=None):
        if not api_config:
            api_config = config.get().api_config
        self.api_config = api_config
        self.database = database

    def required(self, method=None, admin=False):
        def decorator(f):
            @wraps(f)
            def auth_decorator(*args, **kwargs):

                if self.api_config.disable_authentication:
                    g.user = self.get_some_company_user()
                    Log.set(user_id=g.user.id,
                            user_name=g.user.username)
                    return f(*args, **kwargs)

                auth = request.authorization

                auth_token = auth.username if auth else None

                if not auth or not self.check_auth(auth_token, admin):
                    return authenticate_response()
                return f(*args, **kwargs)
            return auth_decorator
        if method:
            return decorator(method)
        return decorator

    def check_auth(self, token, admin):
        """
        This function is called to check if a username /
        password combination is valid.
        """
        with self.database.session:

            # first try to authenticate by token
            user = self.database.User.verify_auth_token(token)
            if user:
                Log.set(user_id=user.id,
                        user_name=user.username)
            else:
                return False
            if admin and not user.is_admin:
                return False
            g.user = user
            return True

    # msta @ 14-09: I think some_company_user is better than default_user
    # because default implies that it's not deliberately admin
    def get_some_company_user(self):
        with self.database.session:
            return self.database.get_some_company_user()
