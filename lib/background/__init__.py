import os


# Returns the absolute path of a static directory
def static_path(path):
    return os.path.abspath(os.path.join(__file__, '..', 'static', path))
