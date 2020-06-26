import os
from flask import Flask, render_template, request, redirect, url_for
from flask import send_from_directory
from werkzeug.utils import secure_filename
import re
import requests
from bs4 import BeautifulSoup
import webbrowser
import sys
from elasticsearch import Elasticsearch
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

app = Flask(__name__) #Flask Init
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

es_host="127.0.0.1" #elasticsearch Init
es_port="9200"
es = Elasticsearch([{'host':es_host, 'port':es_port}], timeout=30)

swlist=[] #StopWords Init
for sw in stopwords.words("english"):
	swlist.append(sw)


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
		delayTime=[]
		TF=[]
		for i in range(0,urlCount): #count the number of words
			wordList.append({})
			count = 0
			temp=[]
			req = requests.get(urlList[i])
			html = req.text
			soup = BeautifulSoup(html, 'html.parser')
			lines = soup.find_all('p')

			for line in lines:
				for word in hfilter(line.text).split():
					if word not in wordList[i]:
						wordList[i][word] = 0
					wordList[i][word] += 1
					count += 1

			delList=[]
			for word in wordList[i]:
				if word in swlist:
					delList.append(word)
			for word in delList:
				del(wordList[i][word]) # save only useful words in Elasticsearch

			wordCount.append(count)
			delayTime.append('NULL')
		e1 = {
			"urlList":urlList,
			"wordList":wordList,
			"wordCount":wordCount,
			"delayTime":delayTime,
		}
		
		es.indices.delete(index='words', ignore=[400,404])
		es.index(index='words', doc_type='word', id=1, body=e1)

		info = {'urlList':urlList, 'urlCount':urlCount, 'wordCount':wordCount, 'analType':'NULL', 'delayTime':delayTime, 'TF':TF}

		return render_template('fileurl.html', info=info)

@app.route('/info/<kind>/<num>', methods=['GET'])
def analysis(kind, num):
	body ={"query":{"match_all":{}}}
	if (kind == "word"):
		data=es.get(index='words', doc_type='word', id=1)['_source']
		urlList=data['urlList']
		urlCount=len(urlList)
		wordCount=data['wordCount']
		delayTime=data['delayTime']

		TF=[]
		for i in range(0,urlCount):
			TF.append("TF "+str(i)+"번값")
		info = {'urlList':urlList, 'urlCount':urlCount, 'wordCount':wordCount, 'analType':'word', 'delayTime':delayTime, 'TF':TF}

		return render_template('fileurl.html', info=info)
		

if __name__ == "__main__": 
	webbrowser.open_new("http://127.0.0.1:5000/")
	app.run(host='127.0.0.1', port='5000', debug=True)

