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

app = Flask(__name__) #플라스크 초기 설정
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

es_host="127.0.0.1" #엘라스틱서치 초기 설정
es_port="9200"
es = Elasticsearch([{'host':es_host, 'port':es_port}], timeout=30)

swlist=[] # Stopwords 초기 설정
for sw in stopwords.words("english"):
	swlist.append(sw)


def hfilter(s): # 영문자만 걸러내는 필터
	s = re.sub('[^a-zA-Z]',' ',s)
	s = s.lower()
	return s

@app.route('/', ) # 초기화면
def index():
	info = {
		'statusList':'NULL',
		'urlList':'NULL',
		'urlCount':'NULL',
		'failData':'NULL',
		'wordCount':'NULL',
		'analType':'init',
		'delayTime':'NULL',
		'keywordList':'NULL',
		'similList':'NULL',
	}
	
	return render_template('fileurl.html', info=info)

@app.route('/info', methods=['POST']) # 목록 출력 화면
def info():
	if 'url' in request.form: # 단일 url 입력
		urlList = []
		urlList.append(request.form['url'])
		urlCount = 1

	elif 'file' in request.files: # 파일 입력. 불러온 파일을 임시 파일로 저장
		f = request.files['file']
		filename = secure_filename(f.filename)
		filepath = "uploads/"+filename
		f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

		txt = open(filepath, "r") # 텍스트 파일 열어서 주소 읽어들이기
		urlList = []
		while True:
			url = txt.readline()
			if not url:
				break
			urlList.append(url.rstrip())
		urlCount = len(urlList)


		txt.close() # 임시 파일 삭제
		if os.path.isfile(filepath):
			os.remove(filepath)

	wordList=[]
	wordCount_origin=[]
	wordCount=[]
	delayTime=[]
	statusList=[]
	failIndex=[]
	TF=[]
	for i in range(0,urlCount): # 단어 수 측정
		wordList.append({})
		count = 0
		SWcount = 0
		temp=[]

		if urlList[i] in urlList[0:i]: # 중복 url 체크
			failIndex.append(i)
			statusList.append('rep')
			wordCount.append(0)
			delayTime.append('NULL')
			continue

		req = requests.get(urlList[i])

		statusList.append(req.status_code) # 실패 url 체크
		if (req.status_code != 200):
			failIndex.append(i)
			wordCount.append(0)
			delayTime.append('NULL')
			continue

		html = req.text
		soup = BeautifulSoup(html, 'html.parser')
		lines = soup.find_all('p')

		for line in lines: # 단어 수 Dictionary 제작
			for word in hfilter(line.text).split():
				if word not in wordList[i]:
					wordList[i][word] = 0
				wordList[i][word] += 1

		delList=[] # Stopword 걸러내기
		for word in wordList[i]:
			if word in swlist:
				delList.append(word)
				SWcount += wordList[i][word]
			else:
				count += wordList[i][word] # 전체 단어 수 계산
		for word in delList:
			del(wordList[i][word])

		wordCount_origin.append(count+SWcount)
		wordCount.append(count)
		delayTime.append('NULL')
	
	failIndex.reverse() # 실패 및 중복 url 데이터 가공
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

	es.indices.delete(index='words', ignore=[400,404]) # 서버 기존 데이터 삭제

	eList = [] # 서버 데이터 저장
	es.index(index='words', doc_type='word', id=0, body={"urlCount":urlCount})
	for i in range(0,urlCount):
		eList.append({
			"url":urlList[i],
			"wordList":wordList[i],
			"wordCount_origin":wordCount_origin[i],
			"wordCount":wordCount[i],
			"delayTime":delayTime[i],
			"keywordList":'NULL',
			"similList":'NULL',
		})
		es.index(index='words', doc_type='word', id=i+1, body=eList[i])

	info = {
		'statusList':statusList,
		'urlList':urlList,
		'urlCount':urlCount,
		'failData':failData,
		'wordCount':wordCount_origin,
		'analType':'NULL',
		'delayTime':delayTime,
		'keywordList':'NULL',
		'similList':'NULL',
	}
	
	return render_template('fileurl.html', info=info)

@app.route('/info/<kind>/<tnum>', methods=['GET'])
def analysis(kind, tnum):
	
	body ={"query":{"match_all":{}}} # 서버 데이터 불러오기
	num = int(tnum)-1
	
	data=es.get(index='words', doc_type='word', id=0)['_source']
	urlCount=data['urlCount']
	urlList=[]
	wordCount_origin = []
	wordCount = []
	wordList = []
	delayTime = []
	keywordList = []
	similList = []
	for i in range(0,urlCount):
		data=es.get(index='words', doc_type='word', id=i+1)['_source']
		urlList.append(data['url'])
		wordList.append(data['wordList'])
		wordCount_origin.append(data['wordCount_origin'])
		wordCount.append(data['wordCount'])
		delayTime.append(data['delayTime'])
		keywordList.append(data['keywordList'])
		similList.append(data['similList'])

	if (kind == "word"): # 단어 분석
		start = time.time()
		keys = list(wordList[num].keys())
		TF=list(wordList[num].values()) # TF-IDF 계산
		IDF=[]
		TF_IDF=[]
		
		for word in wordList[num]:
			count = 0
			for wl in wordList:
				if word in wl:
					count+=1
			IDF.append(math.log(urlCount/count))
	
		for i in range(0,len(TF)):
			TF_IDF.append(TF[i] * IDF[i])
		end = time.time()
		delay = round(end-start, 6)
		delayTime[num] = delay

		wordTuple = list(zip(keys, TF_IDF)) # (단어, TF-IDF) 튜플 리스트를 만들어 내림차순 정렬.
		wordTuple = sorted(wordTuple, key=operator.itemgetter(1))
		wordTuple.reverse()

		tempList = []
		for tup in wordTuple[0:10]:
			tempList.append(tup[0]) # 키워드만 10개 저장

		e1 = {
			"url":urlList[num],
			"wordList":wordList[num],
			"wordCount_origin":wordCount_origin[num],
			"wordCount":wordCount[num],
			"delayTime":delay,
			"keywordList":tempList,
			"similList":similList[num],
		}
		es.index(index='words', doc_type='word', id=num+1, body=e1) # 분석 결과, delayTime 변수 갱신
		

		info = {
			'statusList':'NULL',
			'urlList':urlList,
			'failData':'NULL',
			'urlCount':urlCount,
			'wordCount':wordCount_origin,
			'analType':'word',
			'delayTime':delayTime,
			'keywordList':tempList,
			'similList':'NULL',
		}

	elif (kind == "simil"): # 유사도 분석
		start = time.time()
		cos = [] # cos = inner / (absA * absB)
		absA = 0
		for word in wordList[num]: # absA 계산
			absA += pow(wordList[num][word],2)
		absA = math.sqrt(absA)

		inner = []
		for i in range(0,urlCount):
			cos.append(0)
			inner.append(0)
			if (i == num):
				continue
	
			absB = 0 # absB 계산
			for word2 in wordList[i]:
				absB += pow(wordList[i][word2],2)
			absB = math.sqrt(absB)
				
			for word1 in wordList[num]: # 내적 계산
				if word1 in wordList[i]:
					inner[i] += wordList[num][word1] * wordList[i][word1]

			cos[i] = inner[i] / (absA * absB) # 코사인 계산

		urlList2 = urlList.copy()
		urlList2[num] = '없음'
		similTuple = list(zip(urlList2, cos))
		similTuple = sorted(similTuple, key=operator.itemgetter(1))
		similTuple.reverse()
		for i in range(len(similTuple), 3): # url 빈자리는 공백으로 채우기
			similTuple.append(('없음',0))

		tempList = []
		for tup in similTuple[0:3]:
			tempList.append(tup[0]) # 주소만 3개 저장

		end = time.time()
		delay = round(end-start, 6)
		delayTime[num] = delay

		e1 = {
			"url":urlList[num],
			"wordList":wordList[num],
			"wordCount_origin":wordCount_origin[num],
			"wordCount":wordCount[num],
			"delayTime":delay,
			"keywordList":keywordList[num],
			"similList":tempList,
		}
		es.index(index='words', doc_type='word', id=num+1, body=e1) # delayTime 변수 갱신
		
		info = {
			'statusList':'NULL',
			'urlList':urlList,
			'failData':'NULL',
			'urlCount':urlCount,
			'wordCount':wordCount_origin,
			'analType':'simil',
			'delayTime':delayTime,
			'keywordList':'NULL',
			'similList':tempList,
		}

	return render_template('fileurl.html', info=info)

if __name__ == "__main__": 
	webbrowser.open_new("http://127.0.0.1:5000/")
	app.run(host='127.0.0.1', port='5000', debug=True)

