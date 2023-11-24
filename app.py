import os
from flask import Flask, request, render_template, send_file
from werkzeug.utils import secure_filename
from ocr_pdf import init_temp_folder, process_pdf

from gevent import pywsgi


app = Flask(__name__)

# 用于保存上传的PDF文件的目录
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# 检查文件扩展名是否合法
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']

    if file.filename == '':
        return 'No selected file'

    if file and allowed_file(file.filename):
        # 确保目录存在
        app.config['UPLOAD_FOLDER'] = init_temp_folder()

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        process_pdf(file_path)    # 处理上传的PDF文件

        zip_filename = 'output.zip'
        return send_file(zip_filename, as_attachment=True)

    return 'Invalid file format'


# 路由处理函数，用于下载 ZIP 文件
@app.route('/download_zip', methods=['GET'])
def download_zip():
    zip_filename = 'output.zip'
    # 使用 Flask 的 send_file 函数发送文件作为响应
    # as_attachment=True 表示以附件形式下载，而不是在浏览器中打开
    return send_file(zip_filename, as_attachment=True)


if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 3300), app)
    print("网页启动成功")
    server.serve_forever()

