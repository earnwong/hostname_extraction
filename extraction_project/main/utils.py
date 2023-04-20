import os
from django.core.files.storage import default_storage
from . import cleandata
from django.conf import settings

def process_file(uploaded_file, original_filename):
    temp_directory = os.path.join(settings.MEDIA_ROOT, 'temp')
        
    input_file_path = os.path.join(temp_directory, original_filename)
    output_file_path = os.path.join(temp_directory, f"output_{original_filename}")

    with open(input_file_path, 'wb') as input_file:
        for chunk in uploaded_file.chunks():
            input_file.write(chunk)

    cleandata.clean_data(input_file_path, output_file_path)

    with open(output_file_path, 'r', encoding='utf-8') as output_file:
        result_file = output_file.read()

    os.remove(input_file_path)
    os.remove(output_file_path)

    return result_file
