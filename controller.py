from flask import Flask, json, abort, jsonify, make_response
from werkzeug.exceptions import HTTPException
import re
from bson.json_util import dumps
import jwt 
from datetime import datetime, timedelta
from functools import wraps
#carga archivos del proyecto
from flask_api.settings import *
from flask_api.models import *
from flask_api import models
from flask_api.views import check_view , check_result_view , app_file_view, upload_file_view, report_view, rbd_view

@app.errorhandler(500)
def resource_not_found(e):
    return jsonify(error=str(e)), 500

@app.errorhandler(HTTPException)
def handle_exception(e):
    if isinstance(e, HTTPException):
        response = e.get_response() 
        # replace the body with JSON
        response.data = json.dumps({
            "code":e.code,
            "name":e.name,
            "description":e.description
        })
        response.content_type = "application/json"
        return response
    else:
        return e

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token') #http://localhost/rbd/1-9?token=alshfjfjdklsfj89549834ur
        if not token: return jsonify({'message' : 'Token is missing!'}), 403
        try: data = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS512")
        except Exception as e: return jsonify({'message' : 'Token is invalid!'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/login')
def login():
    auth = request.authorization
    if auth and loginOTP(auth.username, auth.password):
        token = jwt.encode({
            'user' : auth.username, 
            'exp' : datetime.utcnow() + timedelta(seconds=300000)}, 
            app.config['SECRET_KEY'], 
            algorithm="HS512")
        return jsonify({'token' : token})
    return make_response('Could not verify!', 401, {'WWW-Authenticate' : 'Basic realm="Login Required"'})

@app.route('/check', methods=['GET'])
@token_required
def check_route():
    return check_view()

@app.route('/report/<id>', methods=['GET'])
def report_route(id):
    report = dbMongoCollection.find_one({'_id': id})
    if(not report): abort(404, "ID not corresponde.")    
    report_data = report.get('json',None)
    if(not report_data): abort(404)
    return report_view(report_data)

@app.route('/rbds', methods=['GET'])
@token_required
def rbds_route():
    rbdList = dbMongoCollection.distinct("rbd")
    return jsonify(rbdList)

@app.route('/rbd/<rbd>', methods=['GET'])
@token_required
def rbd_route(rbd):
    rbdReports = dbMongoCollection.find({'rbd': rbd})
    if(rbdReports.count() == 0): abort(404, "RBD no se encuentra en la BD.")
    return rbd_view(dumps(rbdReports, indent = 0) )

@app.route('/checkresult/<path:foldername>', methods=['GET'])
def check_result_route(foldername):
    if not re.match(r"app/([0-9]+_tmpdirectory)-([0-9]+_Data\.zip)-([a-z0-9]+)", foldername): abort(404, "url no cumple REGEX.")
    folder, file, id = foldername.split("-")[:3]
    data = dbMongoCollection.find_one({'_id': id})
    if(not data): abort(404, "ID not corresponde.")
    return check_result_view(folder, file, id, data)

@app.route('/app/<path:foldername>/<path:filename>', methods=['GET'])
def app_file_route(foldername, filename):
    return app_file_view(foldername, filename)

@app.route('/upload', methods=['POST'])
def upload_file_route():
    rCmd = routeCommand() #set session
    if(not rCmd.validarFormulario()): abort(404, "Error al validar el formulario") #Check form data
    rCmd.initEnviroment() #Crea ambiente de trabajo
    rCmd.extractAll(rCmd.file) #extract file from form
    if(not rCmd.verifyOTP()): abort(404, "El 'verificador de identidad' ingresado no es correcto!") #Chequea verificador de Identidad del form
    rCmd.firmarReporte() #Genera la firma del reporte
    rCmd.getCheckCommand()
    if(rCmd.cmd == "NO_SE_PUDO_REALIZAR_DESENCRIPTACION"):
        abort(404,u"No se pudo desencriptar el archivo. Recuerde usar: parseCSVtoEDE.py insert -e admin@ede.mineduc.cl")
    return upload_file_view(rCmd)

if __name__ == "__main__":
    app.run(
        debug = os.environ.get('DEBUG', False), 
        host = "0.0.0.0", 
        port = int(os.environ.get('PORT', 8080))
        )