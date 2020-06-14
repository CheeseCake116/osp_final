from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)

@app.route('/', )
def index():
	return render_template('home.html')

@app.route('/info', methods=['POST'])
def info():
	if 'file' in request.form:
		return render_template('info.html', name=request.form['file'])
	elif 'name' in request.form:
		return render_template('info.html', name=request.form['name'])
