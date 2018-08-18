import uuid
import re
import pickle
import itertools

# Prepare the data from the file sentences.gold.en
# Create an articles file and a gold label file
# Split document in train, dev and test sets.


#### TRAITEMENT DES NOMS D'ENTREPRISES

'''
Charge le noms des enteprises dans une liste. Sera utile pour l'étape parsing Snorkel.
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
On construit un dictionnaire de noms d'entreprises similaire. Ex : Oracle, Oracle Group, Oracle Corp.
'''
def load_similar_company_names(companies_names) :
	similars = {}
	for a, b in itertools.combinations(companies_names, 2):
		if (a+'s' == b) : # a in b
			if a not in similars :
				similars[a] = [b]
			else :
				similars[a].append(b)	
		if (b+'s' == a) :
			if b not in similars :
				similars[b] = [a]
			else :
				similars[b].append(a)
	return similars


### TRAITEMENT DES DONNEES

positive_relations = []
negative_relations = []
abstain_relations = []

 
'''
Retourne le contenu de l'article
'''
def get_text(data) :
	# Traitement particulier si le texte contient ; (on combine les colonnes car même texte)
	if(len(data) > 4) :
		combined_text=""
		for t in data[3:] :
			combined_text += t.rstrip()
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
	company_info['companies_relation'] = get_companies_relation_pos(company1, company2, relation, text)
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
				pos = m.start()
				final_pos.append([pos, pos + len(s) -1])
				if (pos in inital_pos) :
					inital_pos.remove(pos)
	for pos in inital_pos :
		final_pos.append([pos, pos + len(company_name) -1])
	return final_pos


'''
	Retourne les positions des entreprises en relation
'''
def get_companies_relation_pos(company1, company2, relation_type, text) :
	relations = []
	pos1_l = get_company_positions(company1, text)
	pos2_l = get_company_positions(company2, text)
	for p1 in pos1_l :
		for p2 in pos2_l :
			relation = {}
			relation['relation_type'] = relation_type
			relation['pos_company_1'] = str(p1[0]) + ':'+ str(p1[1]) 
			relation['pos_company_2'] = str(p2[0]) + ':'+ str(p2[1])
			relations.append(relation)
	# On rajoute la relation c1 = c1
	for a, b in itertools.combinations(pos1_l, 2):
		relation = {}
		relation['relation_type'] = 'SAME'
		relation['pos_company_1'] = str(a[0]) + ':'+ str(a[1]) 
		relation['pos_company_2'] = str(b[0]) + ':'+ str(b[1])
		relations.append(relation)
	for a, b in itertools.combinations(pos2_l, 2):
		relation = {}
		relation['relation_type'] = 'SAME'
		relation['pos_company_1'] = str(a[0]) + ':'+ str(a[1]) 
		relation['pos_company_2'] = str(b[0]) + ':'+ str(b[1])
		relations.append(relation)
	return relations



def store_doc_main_relation(company_info) :
	negative, abstain, positive = 0,0,0
	for r in company_info['companies_relation'] :
		if r['relation_type'].upper() == 'PARTNER' :
			positive += 1
		#elif r['relation_type'].upper() == 'UNCLEAR' :
		#	abstain += 1
		else :
			negative += 1
	l = [negative, abstain, positive]
	majority = l.index(max(l))
	if majority == 0 :
		negative_relations.append(company_info['doc_id'])
	elif majority == 1 :
		abstain_relations.append(company_info['doc_id'])
	else :
		positive_relations.append(company_info['doc_id'])


'''
Genere le fichier contenant l'ensemble des articles avec allocation d'un identifiant unique
'''
def generate_articles_file(articles_file_name) :
	# Write article.tsv and gold labels files
	articles_file = open(articles_file_name, 'w')
	for c in companies_data :
		store_doc_main_relation(c)
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
		for r in c['companies_relation'] :
			if (r['relation_type'].upper() == 'PARTNER') :
				value = '1'
			#elif (r['relation_type'].upper() != 'UNCLEAR'):
			#	value = '-1'
			else :
				#value = '0'
				value = '-1' # On considère unclear comme négatif auss
			gold_labels_file.write(c['doc_id'] + '::span:' + str(r['pos_company_1']) + '\t' \
					+ c['doc_id'] + '::span:' + str(r["pos_company_2"])+ '\t' + value + '\n')
	gold_labels_file.close()
	print("gold_labels.tsv file generated")



def update_relations(company_info, new_relations, text) :
	for nr in new_relations :
		for item in company_info['companies_relation'] :
			if item['pos_company_1'] == nr['pos_company_2'] and  item['pos_company_2'] == nr['pos_company_1'] and item['relation_type'] == nr['relation_type'] :
				return None
			elif item['pos_company_1'] == nr['pos_company_1'] and  item['pos_company_2'] == nr['pos_company_2'] and item['relation_type'] == nr['relation_type'] :
				return None
	company_info['companies_relation'] = company_info['companies_relation'] + new_relations
	return company_info


def spread_data_in_dataset(full_data, train_dataset, dev_dataset, test_dataset) :
	for i,doc_id in enumerate(full_data) :
		if i % 10 == 8:
			dev_dataset.append(doc_id)
		elif i % 10 == 9:
			test_dataset.append(doc_id)
		else : 
			train_dataset.append(doc_id)


def store_dataset_repartition() :
	train_dataset, dev_dataset, test_dataset = [], [], []
	spread_data_in_dataset(negative_relations,train_dataset, dev_dataset, test_dataset)
	#spread_data_in_dataset(abstain_relations,train_dataset, dev_dataset, test_dataset)
	spread_data_in_dataset(positive_relations,train_dataset, dev_dataset, test_dataset)
	with open('./data/train_set.pkl', 'wb') as f:
		pickle.dump(train_dataset, f)
	with open('./data/dev_set.pkl', 'wb') as f:
		pickle.dump(dev_dataset, f)
	with open('./data/test_set.pkl', 'wb') as f:
		pickle.dump(test_dataset, f)
	print("dataset pickle files generated")



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
	if (relation.upper() == 'UNCLEAR') :
		continue
	if not any(d['text'] == text for d in companies_data) :
		company_info = get_new_companies_element(text, relation, company1, company2)
		companies_data.append(company_info)
	else :
		company_info = next((item for item in companies_data if item['text'] == text), None)
		new_relations = get_companies_relation_pos(company1, company2, relation, text)
		update_relations(company_info, new_relations, text)


generate_articles_file("./data/articles.tsv")
generate_gold_labels_file("./data/gold_labels.tsv")
store_dataset_repartition()



	

