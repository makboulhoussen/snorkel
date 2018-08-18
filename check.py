data_path = 'data/sentences.gold.en'
file = open(data_path,'r')

tlist= []
articles = []

for l in file :
	data = l.split(';')
	text = data[3]
	text = text.replace('"','').rstrip()
	if text not in tlist :
		tlist.append(text)

print(len(tlist))

data_path = 'data/articles.tsv'
file = open(data_path,'r')

for l in file :
	data = l.split('\t')
	text = data[1].rstrip()
	if text not in articles : 
		articles.append(text)

print(len(articles))

