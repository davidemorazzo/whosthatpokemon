from selenium import webdriver
import glob
import pickle

BASE_URL = 'https://pokemon.neoseeker.com/wiki/'
gifs = glob.glob('D:/Programmazione/Fiverr/andychand400 v2/base_gifs/*')
# gifs = [f.split('\\')[-1].replace('.gif', '').capitalize() for f in gifs if not '-' in f]

## => DOWNLOAD ONLY MEGA FORM
gifs = [f.split('\\')[-1].replace('.gif', '').capitalize() for f in gifs if '-mega.' in f]

driver = webdriver.Chrome(executable_path= "D:\\Programmazione\\Fiverr\\andychand400 v2\\gif script\\chromedriver.exe", service_log_path='Nul')
description_list = []

for cnt, name in enumerate(gifs):
    print(f"{cnt}) New page")
    try:
        url_name = 'Mega'+'_'+name.split('-')[0]
        driver.get(BASE_URL+url_name)                 
        description = driver.find_element_by_xpath("/html/body/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div/p[1]").text
        description_list.append((name.lower(), description))
    except :
        description_list.append((name.lower), " ")
        print("Not found")

driver.close()

with open("description_list_mega.pkl", 'wb') as f:
    pickle.dump(description_list, f) 
