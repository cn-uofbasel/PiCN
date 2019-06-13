import cv2
import os

name = "Classified"

def convert_frames_to_video(pathIn, pathOut, fps, n):
    frame_array = []
    files = [f for f in os.listdir(pathIn) if os.path.isfile(os.path.join(pathIn, f))]

    #for sorting the file names properly
    files.sort(key=lambda x: int(x[n:-4]))


    for i in range(len(files)):
        filename = pathIn + files[i]
        #reading each files
        img = cv2.imread(filename)
        height, width, layers = img.shape
        size = (width,height)
        print(filename)
        #inserting the frames into an image array
        frame_array.append(img)

    out = cv2.VideoWriter(pathOut,cv2.VideoWriter_fourcc(*'avc1'), fps, size)

    for i in range(len(frame_array)):
        # writing to a image array
        out.write(frame_array[i])
    out.release()

root = os.getcwd()
names = {"Classified": 10, "Images": 5, "Plots": 4, "MapsJpg": 4}
convert_frames_to_video(os.path.join(root, f"Data/{name}/"), os.path.join(root, f"Data/Videos/{name}_video.mp4"), 30, names[name])