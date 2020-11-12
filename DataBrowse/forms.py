from django import forms
from DataBrowse.models import DataFrameTIF


class UploadDataFrameForm(forms.ModelForm):
    class Meta:
        model = DataFrameTIF
        fields = ('upload', 'data_frame_name', 'sequence_name')
