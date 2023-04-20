from django import forms

class UploadFileForm(forms.Form):
    file = forms.FileField()
    download = forms.BooleanField(
        required=False,
        initial=True,
        label='Download the result file'
    )