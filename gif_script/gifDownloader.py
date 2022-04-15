from selenium import webdriver
import requests
import re

URL = [
"https://projectpokemon.org/home/docs/spriteindex_148/3d-models-generation-1-pok%C3%A9mon-r90/",
"https://projectpokemon.org/home/docs/spriteindex_148/3d-models-generation-2-pok%C3%A9mon-r91/",
"https://projectpokemon.org/home/docs/spriteindex_148/3d-models-generation-3-pok%C3%A9mon-r92/",
"https://projectpokemon.org/home/docs/spriteindex_148/3d-models-generation-4-pok%C3%A9mon-r93/",
"https://projectpokemon.org/home/docs/spriteindex_148/3d-models-generation-5-pok%C3%A9mon-r94/",
"https://projectpokemon.org/home/docs/spriteindex_148/3d-models-generation-6-pok%C3%A9mon-r95/",
"https://projectpokemon.org/home/docs/spriteindex_148/3d-models-generation-7-pok%C3%A9mon-r96/",
"https://projectpokemon.org/home/docs/spriteindex_148/3d-models-generation-8-pok%C3%A9mon-r123/"
]
GIF_DIRECTORY = "D:\\Programmazione\\Fiverr\\andychand400 v2\\gifs\\"

def check_name(name:str):
    name = name.replace(".gif", "")
    name = name.replace("_", '-')
    words = name.split("-")
    words = [word.replace(".gif", "")for word in words]
    if len(words)==2:
        if "mega" in words:
            return True
        if "megay" in words:
            return True
        if "megax" in words:
            return True
        if "o" in words:
            return True
        if "therian" in words:
            return True
        if "oh" in words:
            return True
        if "gigantamax" in words:
            return True    
        if "galar" in words:
            return True    
        if "alola" in words:
            return True    
        return False
    elif len(words) > 2:
        return False
    return True

if __name__ == '__main__':
#     gif_list = []
#     driver = webdriver.Chrome(executable_path= 'chromedriver.exe', service_log_path='Nul')
#     
#     for this_url in URL:
#         print("New page")
#         driver.get(this_url)                   
#         table = driver.find_elements_by_xpath("/html/body/main/div/div/div/div[2]/div/div[3]/ul/li/div/div[2]/div[2]/div/article/div[1]/section/table[1]/tbody")[0]
#         gifs = table.find_elements_by_tag_name("img")
#         if not gifs:
#             print("vuoto")
#         for gif in gifs:
#             gif_list.append(gif.get_attribute("src"))
#         # gifs = row.find_elements_by_tag_name("img")
#         # for gif in gifs:
#         #     gif_list.append(gif.get_attribute("src"))
#     
#     driver.close()
#     with open("./gifs/gif_list.txt", "a") as f:
#         for file in gif_list:
#             f.write(f"{file}\n")
#     exit()
    ## => SAVE CORRECT GIFS (NOT DUPLICATE)
    gif_list = []
    
    with open("./gifs/gif_list.txt", "r") as f:
        for line in f.readlines():
            gif_list.append(line)
    filtered = open("./gifs/gif_list_filtered.txt", "w")
    for num, url in enumerate(gif_list):
        if "normal-sprite" in url and num > 1792:
            filename = url.strip().split('/')[-1]
            if check_name(filename):
                download = requests.get(url.strip())
                if download.status_code != 200:
                    print(f"{num}                Error: ", filename)
                else:
                    file = open(GIF_DIRECTORY+filename, "wb")
                    file.write(download.content)
                    file.close()
                    # filtered.write(f"{filename}\n")
                    print(f"{num}) Downloaded: ", filename)
