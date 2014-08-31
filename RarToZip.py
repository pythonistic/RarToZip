from flask import Flask
from flask import jsonify
from flask import after_this_request
from flask import render_template
from flask import request
from flask import send_file
from random import random
from time import time
from werkzeug.utils import secure_filename
import os
import rarfile
import traceback
import zipfile
from zipfile import ZipInfo

app = Flask(__name__)

app = Flask(__name__)
app.config.from_object(__name__)
app.config['UPLOAD_FOLDER'] = "/Users/chris"
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024

rarfile.UNRAR_TOOL='/opt/local/bin/unrar'
rarfile.PATH_SEP='/'

ALLOWED_EXTENSIONS = set(['rar'])


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def do_convert(incoming_file, outgoing_file):
    rar = rarfile.RarFile(incoming_file)
    paths = set([])
    with zipfile.ZipFile(outgoing_file, 'w', compression=zipfile.ZIP_DEFLATED) as zfile:
        for file in rar.infolist():
            zinfo = ZipInfo(file.filename, file.date_time)
            if file.comment != None:
                zinfo.comment = file.comment
            if file.isdir():
                if zinfo.filename not in paths:
                    zfile.writestr(zinfo, "")
                    # else skip the path because a file already created it
            elif file.filename != None:
                zfile.writestr(zinfo, rar.read(file), compress_type=zipfile.ZIP_DEFLATED)
                paths.add(zinfo.filename.rsplit('/', 1)[0])
            else:
                # skip the empty filename
                pass
    rar.close()
    # unlink the rar file now
    os.unlink(incoming_file)

def unique_path():
    return str(time()) + '.' + str(int(random() * 10000))


@app.route('/')
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        print(e)
        return str(e)


@app.route('/convert', methods=['POST'])
def convert():
    try:
        file = request.files['file']
        if file and allowed_file(file.filename):
            incoming_filename = secure_filename(file.filename)
            session_path = unique_path()
            os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], session_path))
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], session_path, incoming_filename)
            file.save(filepath)
            outgoing_filepath = filepath.rsplit('.', 1)[0] + '.zip'
            outgoing_filename = incoming_filename.rsplit('.', 1)[0] + '.zip'
            do_convert(filepath, outgoing_filepath)

            return jsonify(success=True,location=session_path + '/' + outgoing_filename)

        return jsonify(success=False)
    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        return str(e)


@app.route('/retrieve/<session_path>/<original_filename>', methods=['GET'])
def retrieve(session_path, original_filename):
    try:
        filename = secure_filename(original_filename)
        filepath = secure_filename(session_path)
        if filename.endswith(".zip"):
            fullpath = os.path.join(app.config['UPLOAD_FOLDER'], filepath, filename)

            @after_this_request
            def cleanup(response):
                os.unlink(fullpath)
                os.rmdir(os.path.join(app.config['UPLOAD_FOLDER'], filepath))
                return response

            return send_file(fullpath, 'application/zip', as_attachment=True, attachment_filename=original_filename)

        else:
            return "404"

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        return str(e)


if __name__ == '__main__':
    app.run(debug=True)
