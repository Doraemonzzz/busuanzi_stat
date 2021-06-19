import requests
import os
import json
import argparse
import datetime
import time

from bs4 import BeautifulSoup
from urllib.parse import unquote
from tqdm import tqdm
from selenium import webdriver
from fake_useragent import UserAgent

# 每个文件中url数量
d = 100
# 保存url的文件夹
url_dir = "url_list"
# 保存data的文件夹
data_dir = "data_list"

def get_max_page(base_url):
	"""
	返回博客文章页数
	"""
	headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        'User-Agent': UserAgent().random #"Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Mobile Safari/537.36"
    }
	#response = requests.get(base_url, headers=headers, proxies={"http": "http://111.233.225.166:1234"}).text
	response = requests.get(base_url, headers=headers, proxies={"http": "http://111.233.225.166:1234"}).content
	soup = BeautifulSoup(response, "html.parser")
	max_page = 1
	for page in soup.find_all(class_="page-number"):
		max_page = max(max_page, int(page.text))
	
	return max_page

def get_article_href(page, class_):
	"""
	返回全部文章的超链接
	"""
	headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        'User-Agent': UserAgent().random
    }
	#html_text = requests.get(page, headers=headers, proxies={"http": "http://111.233.225.166:1234"}).
	html_text = requests.get(page, headers=headers, proxies={"http": "http://111.233.225.166:1234"}).content
	soup = BeautifulSoup(html_text, "html.parser")
	hrefs = []
	# 根据主题需要修改
	# for text in soup.find_all(class_="article-title"):
	#for text in soup.find_all(class_="post-title-link"):
	for text in soup.find_all(class_=class_):
		# print(text)
		hrefs.append(text['href'])

	return hrefs

def get_page_pv(driver, url):
	"""
	返回每篇文章的busuanzi阅读量
	"""
	driver.get(url)
	while True:
		p_element = driver.find_element_by_id(id_='busuanzi_value_page_pv')
		if (p_element != ""):
			break
	return p_element.text

def parse_article(driver, href, base_url):
	"""
	解析每篇文章, 获得如下json数据
	{
		"createdAt": "2018-04-07T13:22:14.714Z",
		"time": 109,
		"title": "浙大数据结构Week3",
		"updatedAt": "2021-01-22T15:51:02.024Z",
		"url": "/2018/04/01/浙大数据结构Week3/"
	},
	"""
	headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        'User-Agent': UserAgent().random
    }
	url = base_url + href
	# response = requests.get(url, headers=headers, proxies={"http": "http://111.233.225.166:1234"}).text
	response = requests.get(url, headers=headers, proxies={"http": "http://111.233.225.166:1234"}).content
	
	soup = BeautifulSoup(response, "html.parser")
	data = dict()
	if soup.find(class_="post-meta-date-created") != None:
		data["createdAt"] = soup.find(class_="post-meta-date-created")["datetime"]
	if soup.find(class_="post-meta-date-updated") != None:
		data["updatedAt"] = soup.find(class_="post-meta-date-updated")["datetime"]
	if soup.find(class_="post-title") != None:
		data["title"] = soup.find(class_="post-title").text
	data["url"] = unquote(href)
	cnt = get_page_pv(driver, url)
	if (cnt == ""):
		data["time"] = 1
	else:
		data["time"] = int(cnt)

	return data

def main():
	start = time.time()
	# 获得参数
	parser = argparse.ArgumentParser()
	parser.add_argument(
		"-b", 
		"--base_url", 
		help="博客首页地址"
	)
	parser.add_argument(
		"-c", 
		"--class_name", 
		help="超链接的类名"
	)
	parser.add_argument(
		"-s", 
		"--start", 
		default=0,
		help="从第几批url开始解析, 默认为0"
	)
	args = parser.parse_args()
	# 博客首地址以及总页数
	base_url = args.base_url
	# example: -b "https://doraemonzzz.com"
	# 超链接的类名
	class_ = args.class_name
    # example: -c "article-title"
	articles_batch = []
	# 开始的批次
	s = args.start
	url_path = os.path.join(os.getcwd(), url_dir)

	if os.path.exists(url_dir):
		for file in os.listdir(url_path):
			file_path = os.path.join(url_path, file)
			articles = []
			with open(file_path) as f:
				for data in f.readlines():
					articles.append(data.strip("\n"))
			articles_batch.append(articles)
	else:
		max_page = get_max_page(base_url)
		
		# 获得每页的超链接, 首页为特殊形式
		pages = [base_url] + [f"{base_url}/page/{i}" for i in range(2, max_page + 1)]
		
		# 获得每篇文章的超链接
		articles = []
		for page in tqdm(pages):
			articles += get_article_href(page, class_)
			# time.sleep(3)

		# 保存url, 每100一个url一个文件
		if not os.path.exists(url_dir):
			os.mkdir(url_dir)
		
		n = len(articles)
		m = n // d
		for i in range(m):
			start = i * d
			end = (i + 1) * d
			url_output = os.path.join(url_path, f"{i}.txt")
			with open(url_output, "w") as f:
				for j in range(start, end):
					f.write(articles[j] + "\n")
			articles_batch.append(articles[start: end])
		
		# 处理剩余部分
		if (m * d != n):
			start = m * d
			end = n
			url_output = os.path.join(os.getcwd(), url_dir, f"{m}.txt")
			with open(url_output, "w") as f:
				for j in range(start, end):
					f.write(articles[j] + "\n")
			articles_batch.append(articles[start: end])
	
	# 解析
	# start chrome browser
	options = webdriver.ChromeOptions()
	options.add_argument('headless')
	driver = webdriver.Chrome(options=options)
	data_output = os.path.join(os.getcwd(), data_dir)

	# 建立文件夹
	if not os.path.exists(data_dir):
		os.mkdir(data_dir)

	for i, articles in enumerate(articles_batch):
		if (i < s):
			continue
		output = os.path.join(data_output, f"{i}.json")
		with open(output, 'w', encoding='utf8') as json_file:
			json_file.write("[\n")
			for ariticle in tqdm(articles):
				data = parse_article(driver, ariticle, base_url)
				json.dump(data, json_file, ensure_ascii=False)
				json_file.write(",\n")
			json_file.write("]\n")
		break

	end = time.time()
	print(f"一共花费的时间为{datetime.timedelta(seconds=end-start)}.")

if __name__ == '__main__':
	main()