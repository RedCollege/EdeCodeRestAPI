import os
from git import Repo
from flask import Flask
#from flask_pymongo import PyMongo
import pymongo

print("Started...")
#Set app folder
APP_HOME = os.environ.get('APP_HOME', '/app')
UPLOAD_FOLDER = APP_HOME
APP_CODE = UPLOAD_FOLDER + '/DockerEdeCode'
ALLOWED_EXTENSIONS = {'zip'}
OTP_SERVICE = os.environ.get('OTP_SERVICE', '')
X_API_KEY = os.environ.get('X_API_KEY', '')

#Update Code
if os.path.exists(APP_CODE):
    print('Directorio existe, se actualizarán los archivos')
    repo = Repo(APP_CODE)
    origin = repo.remotes.origin
    origin.pull('master')
else:
    print('Directorio no existe, se clonará repositorio completo desde https://github.com/Admin-EDE/DockerEdeCode')
    Repo.clone_from("https://github.com/Admin-EDE/DockerEdeCode", APP_CODE, branch='master')

#Configura directorio de las plantillas
template_dir = os.path.abspath(APP_HOME+'/templates')
app = Flask(__name__, template_folder=template_dir)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#Set client mongo connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://mongo:27017/reportdbOLD')
app.config["MONGO_URI"] = MONGO_URL
conn = pymongo.MongoClient(MONGO_URL)
db =  conn['reportede']
dbMongoCollection = db["reportes"]
app.config['SECRET_KEY'] = 'INGRESE SECRET_KEY'