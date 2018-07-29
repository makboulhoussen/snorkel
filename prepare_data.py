import uuid
import re
import pickle
import itertools

# Prepare the data from the file sentences.gold.en
# Create an articles file and a gold label file


#### TRAITEMENT DES NOMS D'ENTREPRISES

'''
Charge le noms des enteprises dans une liste
'''
def load_company_names(data_path) :
	companies_names = []
	file = open(data_path,'r')
	for line in file: 
		data = line.split(';')
		company1 = data[0].lower()
		company2 = data[1].lower()
		if company1 not in companies_names :
			companies_names.append(company1)
			companies_names.append(company1+'s')
		if company2 not in companies_names :
			companies_names.append(company2) 
			companies_names.append(company2+'s')
	with open('./data/companies.pkl', 'wb') as f:
		pickle.dump(companies_names, f)
	print("companies names stores in pkl file")
	return sorted(companies_names)


'''
On construit un dictionnaire de noms d'entreprises similaire
'''
def load_similar_company_names(companies_names) :
	similars = {}
	for a, b in itertools.combinations(companies_names, 2):
		if (a in b) :
			if a not in similars :
				similars[a] = [b]
			else :
				similars[a].append(b)	
		if (b in a) :
			if b not in similars :
				similars[b] = [a]
			else :
				similars[b].append(a)
	return similars


### TRAITEMENT DES DONNEES

'''
Retourne le contenu de l'article
'''
def get_text(data) :
	# Traitement particulier si le texte contient ; (on combine les colonnes car même texte)
	if(len(data) > 4) :
		combined_text=""
		for t in data[3:] :
			combined_text += t
		data[3] = combined_text
		data = data[:4]
	text = data[3]
	text = text.replace('"','').rstrip()
	return text


'''
Création d'un nouvel objet avec identifiant unique et qui va stocker le contenu de l'article et les relations entreprises
'''
def get_new_companies_element(text, relation, company1, company2) :
	unique_id = str(uuid.uuid4())
	company_info = {}
	company_info['doc_id'] = unique_id
	company_info['text'] = text
	company_info['relation'] = relation
	company_info['companies'] = get_companies_relation_pos(company1, company2, text)
	return company_info
	


'''
Recherche la positon du nom de l'entreprise dans le texte. Se base sur notre dictionnaire pour essayer des noms similaires plus long
'''
def get_company_positions(company_name, text) :
	inital_pos = []
	final_pos = []
	p = re.compile(r'\b({0})\b'.format(company_name), re.IGNORECASE)
	for m in p.finditer(text):
		inital_pos.append(m.start())
	if company_name in similar_company_names :
		similar_names = sorted(similar_company_names[company_name], key=len, reverse=True)
		for s in similar_names :
			p = re.compile(r'\b({0})\b'.format(s), re.IGNORECASE)
			for m in p.finditer(text):
				if (m.start() in inital_pos) :
					pos = m.start()
					final_pos.append([pos, pos + len(s) -1])
					inital_pos.remove(pos)
	for pos in inital_pos :
		final_pos.append([pos, pos + len(company_name) -1])
	return final_pos


'''
	Retourne les positions des entreprises en relation
'''
def get_companies_relation_pos(company1, company2, text) :
	relations = []
	pos1_l = get_company_positions(company1, text)
	pos2_l = get_company_positions(company2, text)
	for p1 in pos1_l :
		for p2 in pos2_l :
			relation = {}
			relation['pos_company_1'] = str(p1[0]) + ':'+ str(p1[1]) 
			relation['pos_company_2'] = str(p2[0]) + ':'+ str(p2[1])
			relations.append(relation)
	return relations


'''
Genere le fichier contenant l'ensemble des articles avec allocation d'un identifiant unique
'''
def generate_articles_file(articles_file_name) :
	# Write article.tsv and gold labels files
	articles_file = open(articles_file_name, 'w')
	for c in companies_data :
		articles_file.write( c['doc_id'] + '\t' + c['text'] + '\n')
	articles_file.close()
	print("articles.tsv file generated")


'''
Genere le fichier gold labels contenant les relations trouvés des entreprises
'''
def generate_gold_labels_file(g_labels_file_name) :
	gold_labels_file = open(g_labels_file_name, "w")
	gold_labels_file.write("company1	company2	label\n")
	for c in companies_data :
		if (c['relation'].upper() == 'PARTNER') :
			value = '1'
		else :
			value = '-1'
		# elif (c['relation'].upper() != 'UNCLEAR') :
		# 	value = '-1'
		# else :
		# 	value = '-1'
		# 	#continue
		for r in c['companies'] :
			gold_labels_file.write(c['doc_id'] + '::span:' + str(r['pos_company_1']) + '\t' \
					+ c['doc_id'] + '::span:' + str(r["pos_company_2"])+ '\t' + value + '\n')
	gold_labels_file.close()
	print("gold_labels.tsv file generated")


def check_NonExist(new_company_relation, company_info) :
	for d in company_info['companies'] :
		if d['pos_company_1'] == new_company_relation['pos_company_2'] and d['pos_company_2'] == new_company_relation['pos_company_1'] :
			return False
		elif d['pos_company_1'] == new_company_relation['pos_company_1'] and d['pos_company_2'] == new_company_relation['pos_company_2'] :
			return False
	return True



######## --- MAIN --- ########

data_path = 'data/sentences.gold.en'
file = open(data_path,'r')

companies_data = []
companies_names = load_company_names(data_path)
similar_company_names = load_similar_company_names(companies_names)

for line in file: 
	data = line.split(';')
	text = get_text(data)
	company1 = data[0].lower()
	company2 = data[1].lower()
	relation = data[2]

	if not any(d['text'] == text for d in companies_data) :
		company_info = get_new_companies_element(text, relation, company1, company2)
		companies_data.append(company_info)
	else :
		company_info = next((item for item in companies_data if item['text'] == text and item['relation'] == relation), None)
		if (company_info is None) :
			company_info = get_new_companies_element(text, relation, company1, company2)
			companies_data.append(company_info)
		else :
			new_relations = get_companies_relation_pos(company1, company2, text)
			for nr in new_relations :
				if (check_NonExist(nr, company_info)) :
					company_info['companies'].append(nr)


print(companies_data[27:32])


generate_articles_file("./data/articles.tsv")
generate_gold_labels_file("./data/gold_labels.tsv")
	

