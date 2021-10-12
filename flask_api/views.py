import os 
from zipfile import ZipFile
from datetime import datetime
from pytz import timezone
#import json
from flask import redirect, url_for, render_template, send_from_directory, json, abort, request, jsonify
import qrcode

#carga archivos del proyecto
from flask_api.settings import *
from flask_api.models import *

def report_view(report_data):
    response = jsonify(json.loads(report_data))
    response.status_code = 200
    return response

def rbd_view(report_data):
    data = []
    for report in json.loads(report_data):
        data.append({
            "t_stamp": datetime.fromtimestamp(int(report.get("t_stamp")),tz=timezone('Chile/Continental')), 
            "run":report.get("run"), 
            "id": report.get("_id"),
            "link": url_for('check_result_route', foldername='9999999999_tmpdirectory-9999999999_Data.zip-' + report.get("_id"),_external=True,_scheme='https')
            })
    return make_response(jsonify(data), 200, {'Content-Type':'application/json'})

def check_view():
    return render_template('form.html')

def check_result_view(folder, file, id, data):
    json_uri = url_for('report_route', id=id,_external=True,_scheme='https')
    return render_template('check.html', folder=folder, file=file, json=json_uri, jsonData=data.get("json"))

def app_file_view(foldername, filename):
    print(f"InsideUploaded_File: {foldername}/{filename}")
    return send_from_directory(f'/app/{foldername}', filename)

def upload_file_view(rCmd):
    try:
        action = request.form['action']
        cmd = rCmd.cmd
        response = rCmd.execute(cmd,cwd=rCmd.pathRootDirectory)

        print(sorted(os.listdir(rCmd.pathRootDirectory)))
        dataFile = [f for f in sorted(os.listdir(rCmd.pathRootDirectory)) if (str(f))[-9:] == "_Data.zip"]
        if(action == 'check' and dataFile):
            with ZipFile(f"{rCmd.pathRootDirectory}/{dataFile[0]}") as zipfile:
                for zipinfo in zipfile.filelist:
                    if (str(zipinfo.filename))[-4:] == ".txt":
                        logFileName = zipinfo.filename
                        zipfile.extract(logFileName, path=f'{rCmd.pathRootDirectory}')
                        with open(f"{rCmd.pathRootDirectory}/jsonDataResult.json") as json_file:
                            dataJson = json.load(json_file)

                        functionsList = dataJson.get('functions',{}).keys()
                        jsonDumps = json.dumps(dataJson, indent=None)
                        functionsImplemented = []
                        with open(f"{rCmd.pathRootDirectory}/{logFileName}") as f:
                            logs = f.read().splitlines()
                            for l in logs:
                                try: 
                                    d = eval(l)
                                except:
                                    pass

                                for key,value in d.items():
                                    if key == 'funcName' and value in functionsList and d.get('message') in ["Rechazado", "S/Datos", "Aprobado", "No/Verificado"]:
                                        functionsImplemented.append(value)
                                        txt1 = '#/functions/'+value
                                        txt2 = f'"{value}": "No/Verificado"'
                                        result = d.get('message')
                                        jsonDumps = jsonDumps.replace(txt1,f'{result}')
                                        jsonDumps = jsonDumps.replace(txt2, f'"{value}": "{result}"')

                        print(f"functionsImplemented: {functionsImplemented}")
                        for fn in functionsList:
                            if fn not in functionsImplemented:
                                jsonDumps = jsonDumps.replace('#/functions/'+fn,"No/Verificado")

            rCmd.saveReportResult(jsonDumps)

            # The data that you want to store
            data = url_for('check_result_route', foldername=f'{rCmd.pathRootDirectory}-{dataFile[0]}-{rCmd.hash_}',_external=True,_scheme='https')
            data = data.replace("//app","/app")
            
            # Create qr code instance
            qr = qrcode.QRCode(
                version = None,
                error_correction = qrcode.constants.ERROR_CORRECT_H,
                box_size = 10,
                border = 4,
            )
            # Add data
            qr.add_data(data)
            qr.make(fit=True)
            #qr.make()

            # Create an image from the QR Code instance
            img = qr.make_image()
            img.save(f"{rCmd.pathRootDirectory}/qrimage.jpg")

            fchk = open(f"/app/templates/check.html","r")
            fstyle = open(f"/app/static/css/style.css","r")
            txt = fchk.read()
            styleText = fstyle.read()
            fchk.close()
            fstyle.close()
            txt = txt.replace("/app/static/js/d3.v4.js",'https://d3js.org/d3.v4.js')
            txt = txt.replace('<link rel="stylesheet" href="/app/static/css/style.css">','<style>' + styleText + '</style>')
            txt = txt.replace("{{jsonData|tojson|safe}}","'" + jsonDumps + "'")
            txt = txt.replace("{{json|tojson|safe}}", '"' + data + '"')
            txt = txt.replace('/{{folder}}/{{file}}',data)
            txt = txt.replace('/{{folder}}/qrimage.jpg',"./qrimage.jpg")
            txt = txt.replace('Descargar informe técnico',"Accede a tu informe desde Internet")

            f = open(f"{rCmd.pathRootDirectory}/linkReport.html","w+")
            f.write(txt)
            f.close()
            
            with ZipFile(f"{rCmd.pathRootDirectory}/{dataFile[0]}", 'a') as zipf:
                zipf.write(f"{rCmd.pathRootDirectory}/qrimage.jpg",'qrimage.jpg')
                zipf.write(f"{rCmd.pathRootDirectory}/linkReport.html",'linkReport.html')

            return redirect(url_for('check_result_route', foldername=rCmd.pathRootDirectory+"-"+dataFile[0]+"-"+rCmd.hash_))
        elif (dataFile):
            print(f"beforeRedirect: {rCmd.t_stamp}/{dataFile}")
            return redirect(url_for('app_file_route', foldername=rCmd.t_stamp,filename=dataFile[0]))
        else:
            return response
    except Exception as e:
        abort(500,e)