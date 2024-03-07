import re
import os
import nltk
import joblib
import requests
import numpy as np
from bs4 import BeautifulSoup
import urllib.request as urllib
from nltk.corpus import stopwords
from wordcloud import WordCloud,STOPWORDS
from flask import Flask,render_template,request
import time
import matplotlib
matplotlib.use('agg') 
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

def clean(x):
    x = re.sub(r'[^a-zA-Z ]', ' ', x)
    x = re.sub(r'\s+', ' ', x) 
    x = re.sub(r'READ MORE', '', x) 
    x = x.lower()
    x = x.split()
    y = []
    for i in x:
        if len(i) >= 3:
            if i == 'osm':
                y.append('awesome')
            elif i == 'nyc':
                y.append('nice')
            elif i == 'thanku':
                y.append('thanks')
            elif i == 'superb':
                y.append('super')
            else:
                y.append(i)
    return ' '.join(y)


def extract_all_reviews(url, clean_reviews, org_reviews,customernames,commentheads,ratings):
    with urllib.urlopen(url) as u:
        page = u.read()
        page_html = BeautifulSoup(page, "html.parser")
    reviews = page_html.find_all('div', {'class': 't-ZTKy'})
    commentheads_ = page_html.find_all('p',{'class':'_2-N8zT'})
    customernames_ = page_html.find_all('p',{'class':'_2sc7ZR _2V5EHH'})
    ratings_ = page_html.find_all('div',{'class':['_3LWZlK _1BLPMq','_3LWZlK _32lA32 _1BLPMq','_3LWZlK _1rdVr6 _1BLPMq']})

    for review in reviews:
        x = review.get_text()
        org_reviews.append(re.sub(r'READ MORE', '', x))
        clean_reviews.append(clean(x))
    
    for cn in customernames_:
        customernames.append('~'+cn.get_text())
    
    for ch in commentheads_:
        commentheads.append(ch.get_text())
    
    ra = []
    for r in ratings_:
        try:
            if int(r.get_text()) in [1,2,3,4,5]:
                ra.append(int(r.get_text()))
            else:
                ra.append(0)
        except:
            ra.append(r.get_text())
        
    ratings += ra
    print(ratings)

def tokenizer(s):
    s = s.lower()
    tokens = nltk.tokenize.word_tokenize(s)
    tokens = [t for t in tokens if len(t) > 2]
    tokens = [t for t in tokens if t not in stop_words] 
    return tokens

def tokens_2_vectors(token):
    X = np.zeros(len(word_2_int)+1)
    for t in token:
        if t in word_2_int:
            index = word_2_int[t]
        else:
            index = 0
        X[index] += 1
    X = X/X.sum()
    return X


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/results',methods=['GET'])
def result():    
    url = request.args.get('url')

    nreviews = int(request.args.get('num'))
    clean_reviews = []
    org_reviews = []
    customernames = []
    commentheads = []
    ratings = []

    with urllib.urlopen(url) as u:
        page = u.read()
        page_html = BeautifulSoup(page, "html.parser")

    proname = page_html.find_all('span', {'class': 'B_NuCI'})[0].get_text()
    price = page_html.find_all('div', {'class': '_30jeq3 _16Jk6d'})[0].get_text()
    
    all_reviews_url = page_html.find_all('div', {'class': 'col JOpGWq'})[0]
    all_reviews_url = all_reviews_url.find_all('a')[-1]
    all_reviews_url = 'https://www.flipkart.com'+all_reviews_url.get('href')
    url2 = all_reviews_url+'&page=1'
    

    while True:
        x = len(clean_reviews)
        extract_all_reviews(url2, clean_reviews, org_reviews,customernames,commentheads,ratings)
        url2 = url2[:-1]+str(int(url2[-1])+1)
        if x == len(clean_reviews) or len(clean_reviews)>=nreviews:break

    org_reviews = org_reviews[:nreviews]
    clean_reviews = clean_reviews[:nreviews]
    customernames = customernames[:nreviews]
    commentheads = commentheads[:nreviews]
    ratings = ratings[:nreviews]

    for_wc = ' '.join(clean_reviews)
    wcstops = set(STOPWORDS)
    wc = WordCloud(width=1400,height=800,stopwords=wcstops,background_color='white').generate(for_wc)
    plt.figure(figsize=(20,10), facecolor='k', edgecolor='k')
    plt.imshow(wc, interpolation='bicubic') 
    plt.axis('off')
    plt.tight_layout()
    plt.close()

    d = []
    for i in range(len(org_reviews)):
        x = {}
        x['review'] = org_reviews[i]
        x['cn'] = customernames[i]
        x['ch'] = commentheads[i]
        x['stars'] = ratings[i]
        d.append(x)

    for i in d:
        if i['stars']!=0:
            if i['stars'] in [1,2]:
                i['sent'] = 'NEGATIVE'
            else:
                i['sent'] = 'POSITIVE'

    np,nn =0,0
    for i in d:
        if i['sent']=='NEGATIVE':
            nn+=1
        else:np+=1

    
    def plot(a):
        bin_edges = range(min(a), max(a) + 2)  # Adjust the bin edges to include all data points

        plt.hist(a, bins=bin_edges, align='left', rwidth=0.75, color='skyblue', edgecolor='black')
        plt.xlabel('Ratings')
        plt.ylabel('Frequency')
        plt.title('Ratings')

        for i in range(len(bin_edges) - 1):
            plt.text(bin_edges[i] + 0.4, 0, str(plt.hist(a, bins=bin_edges)[0][i]), ha='center', va='bottom')

        plt.xticks(range(min(a), max(a) + 1))
        plt.grid(axis='y')
        plt.savefig('static/plot.png')

    plot(ratings) 

    return render_template('result.html', dic=d, n=len(clean_reviews), nn=nn, np=np, proname=proname, price=price, plot='static/plot.png')

class CleanCache:
	def __init__(self, directory=None):
		self.clean_path = directory
		if os.listdir(self.clean_path) != list():
			files = os.listdir(self.clean_path)
			for fileName in files:
				print(fileName)
				os.remove(os.path.join(self.clean_path,fileName))
		print("cleaned!")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int('3000'),debug=True)