from django import forms
from DataBrowse.models import DataObject


class UploadDataFrameForm(forms.ModelForm):
    class Meta:
        model = DataObject
        fields = ('upload',
                  'data_frame_name',
                  'sequence_name',
                  'iteration_token',
                  'object_type',
                  'source')
