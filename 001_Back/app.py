from flask import Flask, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError

from classes import OptimizeRequest, FitRequest
from service import optimize_with_sympy, fit_linear


app = Flask(__name__)

#CORS liberando requisições vindas do front em http://127.0.0.1:8000
CORS(
    app,
    resources={r"/*": {"origins": ["http://127.0.0.1:8000/Op.html", "http://localhost:8000/Op.html"]}},
)


def error_response(message: str, status_code: int):
    return jsonify({"error": message}), status_code


# --------------------------------------------------
# Middleware para garantir headers de CORS em TODAS
# as respostas (incluindo erros)
# --------------------------------------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "http://127.0.0.1:8000"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# ---------------------- OTIMIZAÇÃO ---------------------- #

@app.route('/optimize', methods=['POST', 'OPTIONS'])
def post_optimize():
    """
    POST /optimize

    Corpo (JSON):
        {
          "alpha": ...,
          "beta": ...,
          "c": ...,
          "F": ...,
          "pMin": ...,
          "pMax": ...
        }
    """
    # Trata o preflight (OPTIONS) manualmente
    if request.method == 'OPTIONS':
        # só precisa devolver 204/200 com os headers já setados em after_request
        return '', 204

    try:
        data = request.get_json()
        if data is None:
            return error_response("Corpo JSON ausente ou inválido.", 422)

        req = OptimizeRequest(**data)
        res = optimize_with_sympy(req)
        return jsonify(res.model_dump())

    except ValidationError as e:
        return error_response(str(e), 422)
    except Exception as e:
        # ideal logar isso no console também
        print("Erro /optimize:", e)
        return error_response(str(e), 500)


# ---------------------- AJUSTE DA DEMANDA ---------------------- #

@app.route('/fit', methods=['POST', 'OPTIONS'])
def post_fit():
    """
    POST /fit

    Corpo (JSON):
        {
          "data": [
            { "price": 180, "quantity": 220 },
            { "price": 200, "quantity": 190 },
            ...
          ]
        }
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()
        if data is None:
            return error_response("Corpo JSON ausente ou inválido.", 422)

        req = FitRequest(**data)
        res = fit_linear(req.data)
        return jsonify(res.model_dump())

    except ValidationError as e:
        return error_response(str(e), 422)
    except Exception as e:
        print("Erro /fit:", e)
        return error_response(str(e), 500)


@app.route("/ping", methods=['GET', 'OPTIONS'])
def ping():
    if request.method == 'OPTIONS':
        return '', 204
    return jsonify({"status": "ok"})

@app.route("/teste", methods=['GET', 'OPTIONS'])
def index():
    if request.method == 'OPTIONS':
        return '', 204
    return jsonify({"message": "Welcome to the Optimization API"})


if __name__ == "__main__":
    app.run(port=5000, host='localhost', debug=True)
