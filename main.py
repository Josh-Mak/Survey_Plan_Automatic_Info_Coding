import zipfile
from openai import OpenAI
import base64
import cv2
import os
import shutil
from pdf2image import convert_from_path
import pickle
import json
import csv

client = OpenAI()


# region Helper functions
# Function to encode the image for gpt vision
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def extract_zip(zip_file, target_location):
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(target_location)


def get_file_type(file):
    file_extension = file.split(".")[-1]
    return file_extension


def move_file(source, destination_dr):
    shutil.move(source, destination_dr)


def remove_3_tick(text):
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if '```' not in line.strip():
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)
# endregion


# region Unpacking Files (move from data to data/process)
# initial runthrough of files uploaded from user
for filename in os.listdir('plans to process'):
    if os.path.isfile(os.path.join('plans to process', filename)):
        file_type = get_file_type(filename)
        if file_type == "png" or file_type == "jpg":
            print(f"Found image: {filename}")
            shutil.move(f"plans to process/{filename}", 'data/process')
        elif file_type == "zip":
            print(f"Found zip: {filename}")
            extract_zip(f"plans to process/{filename}", 'data/process')
            shutil.move(f"plans to process/{filename}", 'processed plans')
        elif file_type == "pdf":
            pdf_to_images = convert_from_path(f'plans to process/{filename}', poppler_path="poppler-23.11.0/Library/bin")
            for i in range(len(pdf_to_images)):
                pdf_to_images[i].save(f"data/process/{filename}_page{i}.jpg", 'JPEG')
            shutil.move(f"plans to process/{filename}", 'processed plans')

# now re-check the ones to process for any pdfs to convert
for filename in os.listdir('data/process'):
    if os.path.isfile(os.path.join('data/process', filename)):
        file_type = get_file_type(filename)
        if file_type == "pdf":
            pdf_to_images = convert_from_path(f'data/process/{filename}', poppler_path="poppler-23.11.0/Library/bin")
            for i in range(len(pdf_to_images)):
                pdf_to_images[i].save(f"data/process/{filename}_page{i}.jpg", 'JPEG')
            shutil.move(f"data/process/{filename}", 'processed plans')
# endregion


filename_roi_pic_dict = {}
filename_roi_text_dict = {}
# region Main Loop going over each file
for filename in os.listdir('data/process'):
    if os.path.isfile(os.path.join('data/process', filename)):
        file_type = get_file_type(filename)
        print(f"Processing {filename}...")
        if file_type == "png" or file_type == "jpg":
            print(f"File was an image, moving to capture ROI's.")
            # Region Prompting User to Crop Image - CONTROLS: Enter to confirm select, C to cancel select, ESC to submit.
            image = cv2.imread(f"data/process/{filename}")
            image_clone = image.copy()
            cv2.namedWindow("Image", cv2.WINDOW_NORMAL)
            roi_list = cv2.selectROIs("Image", image_clone, printNotice=False)
            cv2.destroyAllWindows()
            if len(roi_list):
                list_of_cropped_images = []
                for roi in roi_list:
                    img_cropped = image[int(roi[1]):int(roi[1] + roi[3]), int(roi[0]):int(roi[0] + roi[2])]
                    list_of_cropped_images.append(img_cropped)

                list_of_cropped_image_filenames = []
                for i, image in enumerate(list_of_cropped_images):
                    cv2.imwrite(f"data/process/cropped_images_to_process/{filename}_crop_n{i}.png", image)
                    list_of_cropped_image_filenames.append(f"data/process/cropped_images_to_process/{filename}_crop_n{i}.png")

                filename_roi_pic_dict[filename] = list_of_cropped_image_filenames

        else:
            print(f"Found a non image file, moving back to data: {filename}")
            shutil.move(f"data/process/{filename}", 'failed to process')
            # endregion


# region Feeding each image to gpt vision
for filename, cropped_image_list in filename_roi_pic_dict.items():
    cropped_image_texts = []
    for cropped_image in cropped_image_list:
        image = f"data:image/png;base64,{encode_image(cropped_image)}"
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            temperature=0,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Return only the exact text found in the image."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image
                            },
                        },
                    ],
                }
            ],
        )
        image_text = response.choices[0].message.content
        cropped_image_texts.append(image_text)
    filename_roi_text_dict[filename] = cropped_image_texts
# endregion

# clearing out the cropped for next run
for cropped_image_name in os.listdir('data/process/cropped_images_to_process'):
    if os.path.isfile(os.path.join('data/process/cropped_images_to_process', cropped_image_name)):
        os.remove(f"data/process/cropped_images_to_process/{cropped_image_name}")

# clearing out process
for file in os.listdir('data/process'):
    if os.path.isfile(os.path.join('data/process', file)):
        shutil.move(f"data/process/{file}", 'processed plans')
# endregion

# with open('filename_roi_text_dict.pickle', 'wb') as handle:
#     pickle.dump(filename_roi_text_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)

# with open('filename_roi_text_dict.pickle', 'rb') as handle:
#     filename_roi_text_dict = pickle.load(handle)

# region Taking each Dict Entry and Passing into GPT 4
filename_json_info_dict = {}
for filename, roi_text in filename_roi_text_dict.items():
    plan_text = ""
    for text in roi_text:
        plan_text += "\n" + text

    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        temperature=0,
        max_tokens=300,
        messages=[
            {"role": "system",
             "content": "You are a virtual assistant who specializes in land surveying classifying various aspects of properties. From the following text return the following information about the survey plan in JSON format. Municipality (city):, Plan Number:, Survey Date (The correct date will appear as: Plot date DATE, or Dated at [city] DATE):, Job Number/File Number:, Survey Company:, Block Number:, Lot Number:, Street Number (Only include when street number is near to block/lot numbers. Do NOT include street number if it is included with other contant information for the survey company.):. If any information is not available in the text, put 'None'."},
            {"role": "user", "content": """PLAN OF SURVEY\nSHOWING PART OF LOT 6\nREGISTRAR’S COMPILED PLAN NO. 892\nCITY OF GUELPH\nIN THE REGIONAL COUNTY OF WELLINGTON\n\nSCALE = 1 : 500\n\n0 1 2 3 4 5 10 15 20 25 30 METERS\n\nVANHARTEN SURVEYING LTD.\n\nSURVEYOR'S CERTIFICATE\n\nI CERTIFY THAT:\n1. THIS SURVEY AND PLAN ARE CORRECT\nAND IN ACCORDANCE WITH THE SURVEYS\nACT, THE SURVEYORS ACT AND THE\nREGISTRY ACT AND THE REGULATIONS\nMADE UNDER THEM.\n2. THE SURVEY WAS COMPLETED ON THE\n22nd DAY OF MARCH, 2006.\n\nDATED AT GUELPH\nAPRIL 7, 2006\n\nRON. M. MAK\nONTARIO LAND SURVEYOR\n\nVANHARTEN SURVEYING LTD.\nONTARIO LAND SURVEYING\n56 WOOLWICH ST. N., GUELPH, N1H 6Y5\n(519) 652-8621 Fax: (519) 412-6426\n\nJULY 2, 2006 E.E.S. C.S.T. R.D.L. O.L.S.\n\nFILE NUMBER: K1-483-970
            """},
            {"role": "assistant", "content": """```json
            {
              "Municipality": "Guelph",
              "Plan Number": "892",
              "Survey Date": "April 7, 2006",
              "Job Number/File Number": "K1-483-970",
              "Survey Company": "VanHarten Surveying Ltd.",
              "Block Number": "None",
              "Lot Number": "6",
              "Street Number": "None"
            }
            ```
            """},
            {"role": "user", "content": plan_text}
        ]
    )

    response_text = response.choices[0].message.content
    filename_json_info_dict[filename] = response_text

# with open('filename_json_info_dict.pickle', 'wb') as handle:
#     pickle.dump(filename_json_info_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
# endregion

# region Saving info as CSV
data_list = []
for filename, json_info in filename_json_info_dict.items():
    json_str = remove_3_tick(json_info)
    data = json.loads(json_str)
    data_list.append(data)

if data_list:
    with open('csv returns/plan_info.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        if data_list[0].keys():
            writer.writerow(data_list[0].keys())
            for data in data_list:
                writer.writerow(data.values())
# endregion
