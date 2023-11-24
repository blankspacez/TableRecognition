import time
import zipfile
import cv2
from pdf2image import convert_from_path
import os
import shutil
from paddleocr import PPStructure, save_structure_res
import json
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import tempfile  # 导入tempfile模块

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def pdf_to_images(pdf_file):
    images = convert_from_path(pdf_file, dpi=300)
    return images


def clear_folder_contents(folder_path):
    try:
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)

            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                clear_folder_contents(item_path)

        os.rmdir(folder_path)
    except Exception as e:
        time.sleep(2)
        clear_folder_contents(folder_path)


def init_temp_folder():
    temp_folder = tempfile.mkdtemp()  # 创建临时文件夹
    print(f"成功创建临时文件夹：{temp_folder}")
    return temp_folder


def delete_temp_folder(folder_path):
    try:
        shutil.rmtree(folder_path)
        print(f"成功删除临时文件夹：{folder_path}")
    except Exception as e:
        print(f"删除临时文件夹失败：{e}")


def delete_zip_file():
    zip_filename = 'output.zip'
    if os.path.exists(zip_filename):
        os.remove(zip_filename)


def process_pdf(input_pdf):
    delete_zip_file()
    # 初始化文件夹
    temp_folder_imgs = init_temp_folder()  # 存pdf的每一页png图片
    save_folder_imgs = init_temp_folder()  # 存对图片进行版面分析的结果
    temp_folder_tables = init_temp_folder()  # 存pdf中所有表格的截图
    save_folder_tables = init_temp_folder()  # 存对表格进行识别的结果
    output = init_temp_folder()  # 存最终的输出，所有表格的xlsx形式

    # 将 PDF 每一页转换为图像
    pdf_images = pdf_to_images(input_pdf)

    layout_engine = PPStructure(table=False, ocr=False, structure_version='PP-StructureV2', show_log=True,
                                layout_model_dir='models/layout/picodet_lcnet_x1_0_fgd_layout_table_infer',
                                layout_dict_path='dicts/layout_table_dict.txt.txt')
    table_count = 0
    # 将图像保存为临时图像文件并使用 cv2.imread 读取
    for idx, img in enumerate(pdf_images):
        temp_img_path = os.path.join(temp_folder_imgs, f"temp_image_{idx + 1}.png")
        img.save(temp_img_path, "PNG")

        # 使用 cv2.imread 读取临时图像文件
        img_loaded = cv2.imread(temp_img_path)

        if img_loaded is not None:

            # 提取图片中的表格
            table = layout_engine(img_loaded)
            img_base_name = os.path.basename(temp_img_path).split('.')[0]
            save_structure_res(table, save_folder_imgs, img_base_name)

            txt_file_path = os.path.join(save_folder_imgs, img_base_name, f'res_0.txt')
            # 读取.txt文件
            with open(txt_file_path, 'r') as file:
                lines = file.readlines()

            # 初始化一个空列表来存储表格的bbox
            table_bboxes = []

            # 遍历每行JSON数据
            for line in lines:
                data = json.loads(line)

                # 检查是否为类型为"table"的行
                if data.get("type") == "table":
                    bbox = data.get("bbox")
                    table_bboxes.append(bbox)

            # 合并重叠的bbox
            merged_bboxes = []
            while table_bboxes:
                current_bbox = table_bboxes.pop(0)
                merged_bbox = current_bbox

                for i in range(len(table_bboxes)):
                    if (current_bbox[2] >= table_bboxes[i][0] and current_bbox[0] <= table_bboxes[i][2] and
                            current_bbox[3] >= table_bboxes[i][1] and current_bbox[1] <= table_bboxes[i][3]):
                        # 重叠的bbox，合并它们
                        merged_bbox[0] = min(merged_bbox[0], table_bboxes[i][0])
                        merged_bbox[1] = min(merged_bbox[1], table_bboxes[i][1])
                        merged_bbox[2] = max(merged_bbox[2], table_bboxes[i][2])
                        merged_bbox[3] = max(merged_bbox[3], table_bboxes[i][3])
                        # 从列表中移除已合并的bbox
                        table_bboxes.pop(i)
                        i -= 1

                merged_bboxes.append(merged_bbox)

            # 打开对应的.png图片
            img = Image.open(temp_img_path)

            # 根据合并后的bbox信息截取图片
            for i, bbox in enumerate(merged_bboxes):
                # 打开对应的.png图片
                img = Image.open(temp_img_path)
                left, top, right, bottom = bbox
                table_img = img.crop((left, top, right, bottom))
                table_count += 1
                # 保存截取的表格图片
                temp_table_path = os.path.join(temp_folder_tables, f'temp_table_{table_count}.png')
                table_img.save(temp_table_path, "PNG")
                img.close()

    print(f'表格截取完成，共{table_count}个表格!')

    table_engine = PPStructure(layout=False, structure_version='PP-StructureV2', show_log=True,
                               table_model_dir='models/table/en_ppstructure_mobile_v2.0_SLANet_infer',
                               table_char_dict_path='dicts/table_structure_dict.txt')
    idx = 0
    for filename in os.listdir(temp_folder_tables):
        table_path = os.path.join(temp_folder_tables, filename)
        table = cv2.imread(table_path)
        result = table_engine(table)
        save_structure_res(result, save_folder_tables, os.path.basename(table_path).split('.')[0])
        print(f"已成功识别表格({idx + 1}/{table_count})")
        idx += 1

    # 遍历output_tables文件夹中的子文件夹
    table_counter = 1
    for root, dirs, files in os.walk(save_folder_tables):
        for file in files:
            if file.endswith(".xlsx"):
                # 构建文件路径
                src_path = os.path.join(root, file)
                dst_filename = f"table{table_counter}.xlsx"
                dst_path = os.path.join(output, dst_filename)  # 最终所有xlsx文件存储在output_res文件夹下

                # 移动并重命名xlsx文件到output文件夹
                shutil.move(src_path, dst_path)
                table_counter += 1

    # 将文件打成压缩包
    zip_filename = 'output.zip'
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, output))
