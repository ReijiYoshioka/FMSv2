from flask import jsonify


def json_ok(data, status=200):
    response = jsonify(data)
    response.status_code = status
    return response


def json_error(message, status=400):
    response = jsonify({"error": message})
    response.status_code = status
    return response
