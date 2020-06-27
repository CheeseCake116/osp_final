import os
from flask import Flask, render_template, request, redirect, url_for
from flask import send_from_directory
from werkzeug.utils import secure_filename
import re
import requests
from bs4 import BeautifulSoup
import webbrowser
import sys
import operator
import time
import math
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
	s = re.sub('[^a-zA-Z]',' ',s)
	s = s.lower()
	return s

@app.route('/', )
def index():
	info = {
		'statusList':'NULL',
		'urlList':'NULL',
		'urlCount':'NULL',
		'failData':'NULL',
		'wordCount':'NULL',
		'analType':'init',
		'delayTime':'NULL',
		'wordList':'NULL',
		'similList':'NULL'
	}
	
	return render_template('fileurl.html', info=info)

@app.route('/info', methods=['POST'])
def info():
	if 'url' in request.form: # get one url
		urlList = []
		urlList.append(request.form['url'])
		urlCount = 1

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
	statusList=[]
	failIndex=[]
	TF=[]
	for i in range(0,urlCount): #count the number of words
		wordList.append({})
		count = 0
		temp=[]

		if urlList[i] in urlList[0:i]:
			failIndex.append(i)
			statusList.append('rep')
			wordCount.append(0)
			delayTime.append('NULL')
			continue

		req = requests.get(urlList[i])

		statusList.append(req.status_code)
		if (req.status_code != 200):
			failIndex.append(i)
			wordCount.append(0)
			delayTime.append('NULL')
			continue

		html = req.text
		soup = BeautifulSoup(html, 'html.parser')
		lines = soup.find_all('p')

		for line in lines:
			for word in hfilter(line.text).split():
				if word not in wordList[i]:
					wordList[i][word] = 0
				wordList[i][word] += 1

		delList=[]
		for word in wordList[i]:
			if word in swlist:
				delList.append(word)
			else:
				count += wordList[i][word]
		for word in delList:
			del(wordList[i][word]) # save only useful words in Elasticsearch

		wordCount.append(count)
		delayTime.append('NULL')
	
	failIndex.reverse()
	failCount=len(failIndex)
	failList=[]
	failCode=[]
	for i in failIndex:
		failList.append(urlList.pop(i))
		failCode.append(statusList.pop(i))
		urlCount -= 1

	failList.reverse()
	failCode.reverse()

	failData = {
		'failList':failList,
		'failCode':failCode,
		'failCount':failCount
	}

	es.indices.delete(index='words', ignore=[400,404])

	eList = []
	es.index(index='words', doc_type='word', id=0, body={"urlList":urlList,})
	for i in range(0,urlCount):
		eList.append({
			"wordList":wordList[i],
			"wordCount":wordCount[i],
			"delayTime":delayTime[i],
		})
		es.index(index='words', doc_type='word', id=i+1, body=eList[i])

	info = {
		'statusList':statusList,
		'urlList':urlList,
		'urlCount':urlCount,
		'failData':failData,
		'wordCount':wordCount,
		'analType':'NULL',
		'delayTime':delayTime,
		'wordList':'NULL',
		'similList':'NULL'
	}
	
	return render_template('fileurl.html', info=info)

@app.route('/info/<kind>/<tnum>', methods=['GET'])
def analysis(kind, tnum):
	body ={"query":{"match_all":{}}}
	num = int(tnum)-1
	if (kind != "NULL"):
		data=es.get(index='words', doc_type='word', id=0)['_source']
		urlList=data['urlList']
		urlCount=len(urlList)
		wordCount = []
		wordList = []
		delayTime = []
		for i in range(0,urlCount):
			data=es.get(index='words', doc_type='word', id=i+1)['_source']
			wordCount.append(data['wordCount'])
			wordList.append(data['wordList'])
			delayTime.append(data['delayTime'])

		if (kind == "word"):
			keys = list(wordList[num].keys())
			TF=list(wordList[num].values())
			IDF=[]
			TF_IDF=[]
			start = time.time()
			for word in wordList[num]:
				count = 0
				for wl in wordList:
					if word in wl:
						count+=1
				IDF.append(urlCount/count)
	
			for i in range(0,len(TF)):
				TF_IDF.append(TF[i] * IDF[i])
			end = time.time()
			delay = round(end-start, 6)
			delayTime[num] = delay

			e1 = {
				"wordList":wordList[num],
				"wordCount":wordCount[num],
				"delayTime":delay,
			}
			es.index(index='words', doc_type='word', id=num+1, body=e1) #update delayTime
		
			wordDic = list(zip(keys, TF_IDF)) # make keys and TF-IDF into list of tuple
			wordDic = sorted(wordDic, key=operator.itemgetter(1)) # sort by TF-IDF
			wordDic.reverse()

			info = {
				'statusList':'NULL',
				'urlList':urlList,
				'urlCount':urlCount,
				'failData':'NULL',
				'wordCount':wordCount,
				'analType':'word',
				'delayTime':delayTime,
				'wordList':wordDic[0:10],
				'similList':'NULL'
			}

		elif (kind == "simil"):
			start = time.time()
			cos = [] # cos = inner / (absA * absB)
			absA = 0
			for word in wordList[num]:
				absA += pow(wordList[num][word],2) # get absA
			absA = math.sqrt(absA)

			inner = []
			for i in range(0,urlCount):
				cos.append(0)
				inner.append(0)
				if (i == num):
					continue
				
				for word1 in wordList[num]:
					absB = 0
					for word2 in wordList[i]:
						absB += pow(wordList[i][word2],2) # get absB
					absB = math.sqrt(absB)

					if word1 in wordList[i]:
						inner[i] += wordList[num][word1] * wordList[i][word1] # get inner
				cos[i] = inner[i] / (absA * absB)
			urlList2 = urlList.copy()
			urlList2[num] = '없음'
			similList = list(zip(urlList2, cos))
			similList = sorted(similList, key=operator.itemgetter(1))
			similList.reverse()
			for i in range(len(similList), 3): # append 'NULL' value until it's size becomes 3
				similList.append(('없음',0))

			end = time.time()
			delay = round(end-start, 6)
			delayTime[num] = delay

			e1 = {
				"wordList":wordList[num],
				"wordCount":wordCount[num],
				"delayTime":delay,
			}
			es.index(index='words', doc_type='word', id=num+1, body=e1) #update delayTime
			
			info = {
				'statusList':'NULL',
				'urlList':urlList,
				'urlCount':urlCount,
				'failData':'NULL',
				'wordCount':wordCount,
				'analType':'simil',
				'delayTime':delayTime,
				'wordList':'NULL',
				'similList':similList
			}

		return render_template('fileurl.html', info=info)

if __name__ == "__main__": 
	webbrowser.open_new("http://127.0.0.1:5000/")
	app.run(host='127.0.0.1', port='5000', debug=True)

