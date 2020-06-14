import os
from flask import Flask, render_template, request, redirect, url_for
from flask import send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', )
def index():
	return render_template('home.html')

@app.route('/info', methods=['POST'])
def info():
	if 'url' in request.form:
		return render_template('oneurl.html', url=request.form['url'])
	elif 'file' in request.files:
		f = request.files['file']
		filename = secure_filename(f.filename)
		filepath = "uploads/"+filename
		f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

		txt = open(filepath, "r")
		urlList = []
		count = 0
		while True:
			url = txt.readline()
			if not url:
				break
			urlList.append(url.rstrip())
			count += 1

		txt.close()
		if os.path.isfile(filepath):
			os.remove(filepath)
		print(count)
		print(urlList)
		return render_template('fileurl.html', urlList=urlList, count=count)
