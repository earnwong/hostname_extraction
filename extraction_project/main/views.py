
from xml.dom import ValidationErr
from django.shortcuts import render
from django.http import HttpResponse
from .forms import UploadFileForm
from .utils import process_file
from .cleandata import InvalidFileError
import os
from django.conf import settings

def clear_temp_directory(temp_directory):
    for file in os.listdir(temp_directory):
        file_path = os.path.join(temp_directory, file)
        if os.path.isfile(file_path):
            os.remove(file_path)

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                original_filename = request.FILES['file'].name
                result_file = process_file(request.FILES['file'], original_filename)
                output_filename = f'output_{original_filename}'

                download = form.cleaned_data['download']

                if download:
                    response = HttpResponse(result_file, content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename={output_filename}'
                    return response
                else: 
                    messages.success(request, 'Data successfully uploaded to MySQL database.')
                    return render(request, 'myapp/upload.html', {'form': form})

            except InvalidFileError as e:
                error_message = str(e)
            except UnicodeDecodeError:
                temp_directory = os.path.join(settings.MEDIA_ROOT, 'temp')
                clear_temp_directory(temp_directory)
                form.add_error(None, ValidationErr('Invalid file format. Please upload a valid CSV file.'))
                
    else:
        form = UploadFileForm()

    return render(request, 'myapp/upload.html', {'form': form})
