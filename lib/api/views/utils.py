from flask import jsonify


def success_response(result=None):
    if result is None:
        return 'ok', 200

    return jsonify(result), 200
