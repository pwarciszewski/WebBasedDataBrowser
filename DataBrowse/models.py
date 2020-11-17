from django.db import models
from .validators import validate_file_extension
from django.utils import timezone
from .lib import TIFsl, operations
import pathlib
import datetime
from django.core.files import File
import json
import time
from . import init_ops
from .lib import operations


def generate_save_path(instance, filename):
    main_dir = pathlib.Path('uploads')
    now = datetime.datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    return(main_dir / year / month / day / filename)


class DataObject(models.Model):
    upload = models.FileField(upload_to=generate_save_path,
                              validators=[validate_file_extension])

    data_frame_name = models.CharField(max_length=200)
    sequence_name = models.CharField(max_length=200)
    iteration_token = models.CharField(max_length=200)

    object_type = models.CharField(max_length=10)
    source = models.CharField(max_length=100)

    upload_date = models.DateTimeField('date uploaded', default=timezone.now)
    is_processed = models.BooleanField(default=False)
    to_delete = models.BooleanField(default=False)

    def __str__(self):
        return(self.data_frame_name)

    def confirmProcessed(self):
        if(self.is_processed):
            pass
        else:
            self.is_processed = True
            super().save()

    def setDeleteStatus(self, status):
        self.to_delete = status
        super().save()

    def addProperty(self, key, value):
        self.dataobjectproperty_set.create(key=key, value=value)

    def getProperties(self):
        properties_set = self.dataobjectresult_set.all()
        for_export = {}

        for obj_property in properties_set:
            for_export.update({obj_property.property_key: obj_property.property_value})


class DataObjectResult(models.Model):
    source_object = models.ForeignKey(DataObject, on_delete=models.CASCADE)
    result_source = models.CharField(max_length=1000)
    result_type = models.CharField(max_length=1000)
    result_location = models.FileField(max_length=1000)
    result_value = models.TextField()

    def __str__(self):
        return('Outcome from: %s' % self.result_source)


class DataObjectProperty(models.Model):
    source_object = models.ForeignKey(DataObject, on_delete=models.CASCADE)
    property_key = models.CharField(max_length=200)
    property_value = models.CharField(max_length=200)

    def __str__(self):
        return('%s: %s' % (self.property_key, self.property_value))

