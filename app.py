import os
from flask import Flask, render_template, request, redirect, url_for
from flask import send_from_directory
from werkzeug.utils import secure_filename
import re
import requests
from bs4 import BeautifulSoup
import webbrowser

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def hfilter(s):
	s = re.sub('[,:;0-9=<>%ㆍ]','',s)
	s = s.replace('.', '')
	s = s.replace('(', '')
	s = s.replace(')', '')
	s = s.replace('!', '')
	s = s.replace('?', '')
	s = s.replace('+', '')
	s = s.replace('"', '')
	s = s.replace("'", '')
	s = s.replace("‘", '')
	s = s.replace('*', '')
	s = s.replace('+', '')
	s = s.replace('-', '')
	s = s.replace('–', '')
	s = s.replace('/', '')
	s = s.replace('[', '')
	s = s.replace(']', '')
	s = s.replace('“', '')
	s = s.replace('”', '')
	s = s.replace('~', '')
	s = s.replace('#', '')
	s = s.replace('@', '')
	s = s.replace('™', '')
	return s

@app.route('/', )
def index():
	return render_template('home.html')

@app.route('/info', methods=['POST'])
def info():
	if 'url' in request.form: # get one url
		return render_template('oneurl.html', url=request.form['url'])

	elif 'file' in request.files: # get file and save as temp file
		f = request.files['file']
		filename = secure_filename(f.filename)
		filepath = "uploads/"+filename
		f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))


		txt = open(filepath, "r") # open txt file and read
		urlList = []
		count = 0
		while True:
			url = txt.readline()
			if not url:
				break
			urlList.append(url.rstrip())
		urlCount = len(urlList)


		txt.close() #delete temp file
		if os.path.isfile(filepath):
			os.remove(filepath)

		wordList=[]
		wordCount=[]
		for i in range(0,urlCount): #count the number of words
			temp=[]
			req = requests.get(urlList[i])
			html = req.text
			soup = BeautifulSoup(html, 'html.parser')
			lines = soup.find_all('p')

			for line in lines:
				temp.extend(hfilter(line.text).split())
			wordList.append(temp)
			wordCount.append(len(temp))

		return render_template('fileurl.html', urlList=urlList, urlCount=urlCount, wordList=wordList, wordCount=wordCount)

if __name__ == "__main__": 
	webbrowser.open_new("http://127.0.0.1:5000/")
	app.run(host='127.0.0.1', port='5000', debug=True)
