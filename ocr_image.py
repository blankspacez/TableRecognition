import cv2
from paddleocr import PPStructure,save_structure_res
import os
import shutil

table_engine = PPStructure(layout=False,show_log=True)

save_folder = 'output'
img_path = '3.png'
img = cv2.imread(img_path)
result = table_engine(img)
save_structure_res(result, save_folder, os.path.basename(img_path).split('.')[0])


