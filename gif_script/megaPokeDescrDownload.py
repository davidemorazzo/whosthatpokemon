from selenium import webdriver
import glob
import pickle

BASE_URL = 'https://www.ign.com/wikis/pokemon-sword-shield/List_of_Every_Gigantamax_Pokemon#Gigantamax_Eevee_G-Max_Move:_G-Max_Cuddle'
driver = webdriver.Chrome(executable_path= "D:\\Programmazione\\Fiverr\\andychand400 v2\\gif script\\chromedriver.exe", service_log_path='Nul')
description_list = []

for cnt, name in enumerate(gifs):
    print(f"{cnt}) New page")
    try:
        driver.get(BASE_URL+name)                 
        description = driver.find_element_by_xpath("/html/body/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/div/p[1]").text
        description_list.append((name.lower(), description))
    except :
        print("Not found")

driver.close()

with open("description_list.pkl", 'wb') as f:
    pickle.dump(description_list, f) 