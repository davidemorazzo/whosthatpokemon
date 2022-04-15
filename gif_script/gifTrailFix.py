import os
from PIL import Image
from subprocess import check_output
import glob

def split_gif(base_directory, giffilename):
    files = glob.glob(base_directory+'\\frames\\*')
    for f in files:
        os.remove(f)
    command = f'"C:\\Program Files\\ImageMagick-7.1.0-Q16\\magick.exe" convert -coalesce -channel rgba "{base_directory}\\{giffilename}" "{base_directory}\\frames\\xx_%05d.png"'
    check_output(command, shell=True)

def convert_gif(original_filename, base_directory):
    
    """
    Resave the gifs to eliminate the trail effect
    """

    ## => SPLIT GIF INTO FRAMES USING IMAGEMAGICK
    try:
        os.mkdir(base_directory+"\\frames\\")
        os.mkdir(base_directory+"\\fixed\\")
    except :
        pass
    split_gif(base_directory, original_filename) # all frames in the folder ./frames
    frames = []
    black_counter = 0
    
    # list all frames 
    files = [f for f in os.listdir(base_directory+"\\frames\\") if f.endswith(".png")]
    for num, filename in enumerate(files):
        original_img = Image.open(base_directory+"\\frames\\"+filename)
        frames.append(original_img)

    ## => CREATE NEW GIF
    if len(frames)>1:
        frames[0].save(f"{base_directory}\\fixed\\{original_filename.split('.')[0]}.gif", save_all=True, append_images=frames[1:], optimize=True, duration=40, loop=0, disposal=2)
    else:
        with open(base_directory+"\\logfile.txt", "a") as f:
            f.write(f"{original_filename}       NO FRAMES\n")
        print("No frames: ", original_filename)
    if black_counter != 0:
        with open(base_directory+"\\logfile.txt", "a") as f:
            f.write(f"{original_filename} {black_counter}\n")

if __name__ == '__main__':
    BASE_DIRECTORY = "D:\\Programmazione\\Fiverr\\andychand400 v2\\gifs\\clear"
    files = [f for f in os.listdir(BASE_DIRECTORY+"") if f.endswith(".gif")]
    black_gifs = os.listdir(BASE_DIRECTORY+"\\fixed\\") 

    for num, file in enumerate(files):
        if not file in black_gifs:
            try:
                convert_gif(file, BASE_DIRECTORY)
                print(f"{num}. Converted {file}")
            except:
                with open(BASE_DIRECTORY+"\\logfile.txt", "a") as f:
                    f.write(f"{file}       CORRUPTED\n")