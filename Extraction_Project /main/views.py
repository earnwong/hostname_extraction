
from xml.dom import ValidationErr
from django.shortcuts import render
from django.http import HttpResponse
from .forms import UploadFileForm
from .utils import process_file
from .cleandata import InvalidFileError

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                original_filename = request.FILES['file'].name
                result_file = process_file(request.FILES['file'], original_filename)
                output_filename = f'output_{original_filename}'
                response = HttpResponse(result_file, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename={output_filename}'
                return response
            except InvalidFileError as e:
                error_message = str(e)
            except UnicodeDecodeError:
                form.add_error(None, ValidationErr('Invalid file format. Please upload a valid CSV file.'))
                
    else:
        form = UploadFileForm()

    return render(request, 'myapp/upload.html', {'form': form})
