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
    Convert the gifs present in the base_directory to a blacked version and puts them
    into base_directory\\blacked
    """

    ## => SPLIT GIF INTO FRAMES USING IMAGEMAGICK
    try:
        os.mkdir(base_directory+"\\frames\\")
        os.mkdir(base_directory+"\\blacked\\")
    except :
        pass
    split_gif(base_directory, original_filename) # all frames in the folder ./frames
    frames = []
    black_counter = 0
    
    # black out all frames
    files = [f for f in os.listdir(base_directory+"\\frames\\") if f.endswith(".png")]
    for num, filename in enumerate(files):
        original_img = Image.open(base_directory+"\\frames\\"+filename)
        new_data = []
        all_trasparent = True
        blackPxlCnt = 0
        for pixel in original_img.getdata():
            if pixel == 0: # original_img.info['transparency']:
                # transparent
                new_data.append(0)
            else:
                # black
                new_data.append(1)
                all_trasparent = False
                blackPxlCnt += 1
        
        blackPercent = blackPxlCnt / (len(original_img.getdata()))
        #85% black frame is not appended
        if not all_trasparent and blackPercent < 0.85:
            newim = Image.new(mode="P", size = original_img.size)
            newim.putdata(new_data)
            newim.info['transparency'] = 0
            if new_data[1] == 0:
                frames.append(newim)
            else:
                print("Black image", num)
                black_counter = black_counter + 1 

    ## => CREATE NEW GIF
    if len(frames)>1:
        frames[0].save(f"{base_directory}\\blacked\\{original_filename.split('.')[0]}.gif", save_all=True, append_images=frames[1:], optimize=True, duration=40, loop=0, disposal=2)
    else:
        with open(base_directory+"\\logfile.txt", "a") as f:
            f.write(f"{original_filename}       NO FRAMES\n")
        print("No frames: ", original_filename)
    if black_counter != 0:
        with open(base_directory+"\\logfile.txt", "a") as f:
            f.write(f"{original_filename} {black_counter}\n")

if __name__ == '__main__':
    BASE_DIRECTORY = "D:\\Programmazione\\Fiverr\\whosthatpokemon\gif_script\\gifWorkspace"
    files = [f for f in os.listdir(BASE_DIRECTORY) if f.endswith(".gif")]
    black_gifs = os.listdir(BASE_DIRECTORY+"\\blacked\\") 

    for num, file in enumerate(files):
        if not file in black_gifs:
            try:
                convert_gif(file, BASE_DIRECTORY)
                print(f"{num}. Converted {file}")
            except:
                with open(BASE_DIRECTORY+"\\logfile.txt", "a") as f:
                    f.write(f"{file}       CORRUPTED\n")