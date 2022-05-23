import asyncio
import os, shutil, stat
from PIL import Image
from subprocess import check_output
import glob

def split_gif(base_directory, giffilename, frames_dir):
    files = glob.glob(frames_dir+"/*.png")
    for f in files:
        os.remove(f)
    command = f'"C:\\Program Files\\ImageMagick-7.1.0-Q16\\magick.exe" convert -coalesce -channel rgba "{base_directory}\\{giffilename}" "{frames_dir}\\xx_%05d.png"'
    check_output(command, shell=True)

def convert_gif(original_filename, base_directory, num):
    
    """
    Resave the gifs to eliminate the trail effect
    """

    try:
        ## => SPLIT GIF INTO FRAMES USING IMAGEMAGICK
        frames_dir = base_directory + f'/frames_{num}'
        try:
            os.mkdir(frames_dir)
        except :
            pass
        split_gif(base_directory, original_filename, frames_dir) # all frames in the folder ./frames
        frames = []
        black_counter = 0
        
        # list all frames 
        files = glob.glob(frames_dir+"/*.png")
        for num, filename in enumerate(files):
            original_img = Image.open(filename)
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
    except:
        with open(base_directory+"\\logfile.txt", "a") as f:
            f.write(f"{original_filename}       CORRUPTED\n")
        print("Corrupted: ", original_filename)    
    
    ## => CLEAN UP
    def on_rm_error( func, path, exc_info):
        # path contains the path of the file that couldn't be removed
        # let's just assume that it's read-only and unlink it.
        os.chmod( path, stat.S_IWRITE )
        os.unlink( path )

    shutil.rmtree( frames_dir, onerror = on_rm_error )

async def main():
    BASE_DIRECTORY = "D:/Programmazione/Fiverr/whosthatpokemon/gifs/shiny"
    files = [f for f in os.listdir(BASE_DIRECTORY+"") if f.endswith(".gif")]
    loop = asyncio.get_event_loop()
    t = []

    for num, file in enumerate(files):
        e = loop.run_in_executor(None, convert_gif,file, BASE_DIRECTORY, num)
        t.append(e)
    
    while t:
        await asyncio.sleep(0.5)
        t = [task for task in t if not task.done()]
        print(f"{len(t)} tasks remaining")


if __name__ == '__main__':
        asyncio.run(main())