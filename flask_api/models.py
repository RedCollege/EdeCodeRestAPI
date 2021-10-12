import io, os, sys 
import subprocess
from werkzeug.utils import secure_filename
from zipfile import ZipFile
from datetime import datetime
from pytz import timezone
import requests
import json
import hashlib
import pyotp
from flask import request, make_response
from flask import flash, redirect, url_for, render_template, send_from_directory

#carga archivos del proyecto
from flask_api.settings import *

def loginOTP(run_, otp_):
    now_ = datetime.now(timezone('Chile/Continental'))
    dt_ = now_.strftime('%Y-%m-%dT%H:%M:%S%Z:00')
    tmz_ = int(datetime.timestamp(now_))
    print(f"OTP: {otp_},RUN: {run_}, NOW: {now_}, TZ: {tmz_}, t_:{dt_}")

    url = OTP_SERVICE
    headers = {'Content-Type': 'application/json', 'x-api-key': X_API_KEY}
    payload = [{"RUT":run_, "OTP":otp_, "TIMESTAMP":dt_}]
    req = requests.post(url, headers=headers, json=payload)
    print(f"Request result: {req.status_code}, {req.json()}, {req.reason}")
    r_ = req.json()
    if(req.status_code != 200 or not r_[0].get('OTPVERIFY', False) or r_[0].get('OTPVERIFY') == 'RUT_NO_EXISTE'): return False
    return True

class routeCommand:
    def __init__(self):
        time = datetime.now(timezone('Chile/Continental'))
        self.t_stamp = str(int(datetime.timestamp(time)))
        print(f"time: {time}, timeStamp: {self.t_stamp}")
        self.pathRootDirectory = f'/app/{self.t_stamp}_tmpdirectory'
        if not os.path.exists(self.pathRootDirectory):
            os.makedirs(self.pathRootDirectory)
        os.system(f"cp /app/jsonDataResult.json {self.pathRootDirectory}/jsonDataResult.json")

    def firmarReporte(self):
        totp = pyotp.TOTP('eeeeeeeeee')
        dt2_ = self.dt_[::-1].replace(':','',1)[::-1]
        dt = datetime.strptime(dt2_,"%Y-%m-%dT%H:%M:%S%z")
        self.token = totp.at(for_time=dt)
        response  = totp.verify( otp = self.token, for_time = dt, valid_window = 10 )
        self.hash_ = hashlib.md5(f"{self.now_},{self.run_},{self.otp_},{self.token}".encode('utf-8')).hexdigest()
        print(self.token,response)
        print(self.hash_)

    def verifyOTP(self):
        self.now_ = datetime.now(timezone('Chile/Continental'))
        self.dt_ = self.now_.strftime('%Y-%m-%dT%H:%M:%S%Z:00')
        tmz_ = int(datetime.timestamp(self.now_))
        print(f"OTP: {self.otp_},RUN: {self.run_}, NOW: {self.now_}, TZ: {tmz_}, t_:{self.dt_}")

        url = OTP_SERVICE
        headers = {'Content-Type': 'application/json', 'x-api-key': X_API_KEY}
        payload = [{"RUT":self.run_, "OTP":self.otp_, "TIMESTAMP":self.dt_}]
        req = requests.post(url, headers=headers, json=payload)
        print(f"Request result: {req.status_code}, {req.json()}, {req.reason}")
        r_ = req.json()
        print("r_:",r_,isinstance(r_[0], (str)))
        if(isinstance(r_[0], (str))): return False
        if(not r_[0].get('OTPVERIFY', False) or r_[0].get('OTPVERIFY') == 'RUT_NO_EXISTE'):return False
        return True

    def initEnviroment(self):
        os.system(f"cp -a {APP_CODE}/. {self.pathRootDirectory}")
        self.pathExecFile = f"{self.pathRootDirectory}/parseCSVtoEDE.py"
        print(f"Archivo parseCSVtoEDE.py copiado en: {self.pathExecFile}")

    def validarFormulario(self):
        try:
            self.file = request.files.get('file', None)
            if(not self.allowed_file(self.file.filename)): raise "extention not permited"
            self.otp_ = request.form.get('otp',None)
            rut_ = request.form.get('run',None)
            if("-" not in rut_):
                rut_ = rut_.strip()[:-1]+"-"+rut_[-1]
            self.run_ = rut_
            self.rbd_ = request.form.get('rbd',None)
            if(self.file and self.otp_ and self.run_ and self.rbd_): return True
            raise "Faltan parametros"
        except:
            return False

    def extractAll(self, file):
        filename = secure_filename(file.filename)
        fullPath_file = os.path.join(self.pathRootDirectory, filename+'source.zip')
        file.save(fullPath_file)

        with ZipFile(fullPath_file, 'r') as zip_ref:
            zip_ref.extractall(self.pathRootDirectory)
            _t=f'Archivo ZIP "{fullPath_file}" descomprimido con éxito'; print(_t)
            print(zip_ref.namelist())
        
        return zip_ref.namelist()
    
    def getCheckCommand(self):
        print("Check command")    
        dbFile = [f for f in sorted(os.listdir(self.pathRootDirectory)) if (str(f))[-15:] == "_encryptedD3.db"]
        dbPath = [self.pathRootDirectory+'/'+str(f) for f in dbFile]
        encriptFile = [f for f in sorted(os.listdir(self.pathRootDirectory)) if (str(f))[-14:] == "_key.encrypted"]
        encriptPath = [self.pathRootDirectory+'/'+str(f) for f in encriptFile]
        print(f"encriptPath: {encriptPath}")
        print(f"dbPath: {dbPath}")
        if(encriptPath and dbPath):
            os.system(f"openssl rsautl -oaep -decrypt -inkey /app/claveprivada.pem -in {encriptPath[0]} -out {self.pathRootDirectory}/{self.t_stamp}_key.txt")
            if(os.path.exists(f"{self.pathRootDirectory}/{self.t_stamp}_key.txt")):
                with open (f"{self.pathRootDirectory}/{self.t_stamp}_key.txt", "r") as myfile:
                    frase_secreta=myfile.readlines()
                print(f"frase_secreta: {frase_secreta}")
                if(frase_secreta):
                    self.cmd = f"python3 {self.pathExecFile} check --json {frase_secreta[0]} {dbPath[0]}"
                else:
                    self.cmd = "NO_SE_PUDO_REALIZAR_DESENCRIPTACION"
        else:
            self.cmd = f"python3 {self.pathExecFile} check --help"
        return self.cmd

    def execute(self,cmd,cwd):
        try:
            completedProcess = subprocess.run(cmd,cwd=cwd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=900,universal_newlines=True)
            response = make_response(completedProcess.stdout, 200)
            response.mimetype = "text/plain"
            return response
        except subprocess.TimeoutExpired:
            response = make_response("Timedout", 400)
            response.mimetype = "text/plain"
            return response

    def saveReportResult(self,jsonDumps):
        self.post_id = dbMongoCollection.insert_one({
            '_id': self.hash_,
            'rbd': self.rbd_,
            'dt': self.now_,
            't_stamp': self.t_stamp,
            'run': self.run_,
            'otpEDE': self.token,
            'otpUser': self.otp_,
            'json': jsonDumps
        }).inserted_id

    def allowed_file(self,filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
