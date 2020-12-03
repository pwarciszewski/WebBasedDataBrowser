from django.db import models
from .validators import validate_file_extension
from django.utils import timezone
from .lib import TIFsl, operations
import pathlib
import datetime
import pandas as pd
import json
import time
from . import init_ops
from .lib import operations
from .lib.data_extractors import EXTRACTORS


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

    def getData(self):
        return(EXTRACTORS[self.object_type](self.upload.path))

    def addProperty(self, key, value):
        self.dataobjectproperty_set.create(key=key, value=value)

    def getProperties(self):
        properties_set = self.dataobjectresult_set.all()
        for_export = {}

        for obj_property in properties_set:
            for_export.update({obj_property.property_key: obj_property.property_value})

    def _handleExporOfNUM(self, result_num):
        return({result_num.result_source: float(result_num.result_value)})

    def _handleExportOfIMG(self, result_img):
        # TODO: Add a proper export, that actually exports data not the file path
        return({result_img.result_source: result_img.result_location.path})

    def _handleExportOfCSV(self, result_csv):
        # Returns pandas.DataFrame
        return({result_csv.result_source: pd.read_csv(result_csv.result_location.path)})

    def getResults(self):
        # Exports data for server usage
        handle_table = {'IMG': self._handleExportOfIMG,
                        'NUM': self._handleExporOfNUM,
                        'CSV': self._handleExportOfCSV}

        result_set = self.dataobjectresult_set.all()
        for_export = {}

        for result in result_set:
            for_export.update(handle_table[result.result_type](result))

        return(for_export)

    def _addResultIMG(self, data, result_source, *args):
        concrete_file_name = pathlib.Path(self.upload.path).stem
        result_dir = pathlib.Path(self.upload.path).parent / concrete_file_name / 'RESULTs'
        # TODO: replace unnecesarry TIFsl dependencies with new utils functions
        result_location = TIFsl.saveJPG(data, result_source + '.jpg', result_dir, *args)
        no_cache_tag = '?nocachetag=' + str(time.time())
        result_url = '/static' / pathlib.Path(self.upload.url).parent / concrete_file_name / 'RESULTs' / (result_source + '.jpg')
        result_url = str(result_url) + no_cache_tag
        current_set = self.dataobjectresult_set.filter(result_location=result_location,
                                                result_source=result_source,
                                                result_type='IMG')
        # check if entry already exists; if not an entry is created otherwise url is edited
        if len(current_set) == 0:
            self.dataobjectresult_set.create(result_location=result_location,
                                      result_source=result_source,
                                      result_value=result_url,
                                      result_type='IMG')
        else:
            current_set[0].result_value = result_url
            current_set[0].save()

    def _addResultNUM(self, value, result_source, *args):
        current_set = self.tifresult_set.filter(result_location='NOT APPLICABLE',
                                                result_source=result_source,
                                                result_type='NUM')

        if len(current_set) == 0:
            self.tifresult_set.create(result_location='NOT APPLICABLE',
                                      result_source=result_source,
                                      result_value=value,
                                      result_type='NUM')
        else:
            current_set[0].result_value = value
            current_set[0].save()

    def _addResultCSV(self, data, result_source, *args):
        # ASSUMPTION: data is a pandas.DataFrame
        concrete_file_name = pathlib.Path(self.upload.path).stem
        result_dir = pathlib.Path(self.upload.path).parent / concrete_file_name / 'RESULTs'
        result_dir.mkdir(parents=True, exist_ok=True)
        result_location = result_dir / (result_source + '.csv')
        data.to_csv(str(result_location))
        no_cache_tag = '?nocachetag=' + str(time.time())
        result_url = '/static' / pathlib.Path(self.upload.url).parent / concrete_file_name / 'RESULTs' / (result_source + '.csv')
        result_url = str(result_url) + no_cache_tag
        current_set = self.dataobjectresult_set.filter(result_location=str(result_location),
                                                result_source=result_source,
                                                result_type='CSV')
        # check if entry already exists; if not an entry is created otherwise url is edited
        if len(current_set) == 0:
            self.dataobjectresult_set.create(result_location=str(result_location),
                                      result_source=result_source,
                                      result_value=result_url,
                                      result_type='CSV')
        else:
            current_set[0].result_value = result_url
            current_set[0].save()

    def addResult(self, result, result_type, result_source, *args):
        actions = {'IMG': self._addResultIMG,
                   'NUM': self._addResultNUM,
                   'CSV': self._addResultCSV}

        actions[result_type](result, result_source, *args)


class DataObjectResult(models.Model):
    source_object = models.ForeignKey(DataObject, on_delete=models.CASCADE)
    result_source = models.CharField(max_length=1000)
    result_type = models.CharField(max_length=1000)
    result_location = models.FileField(max_length=1000)
    result_value = models.TextField()

    def __str__(self):
        return('Outcome of: %s' % self.result_source)


class DataObjectProperty(models.Model):
    source_object = models.ForeignKey(DataObject, on_delete=models.CASCADE)
    property_key = models.CharField(max_length=200)
    property_value = models.CharField(max_length=200)

    def __str__(self):
        return('%s: %s' % (self.property_key, self.property_value))


class ManyDataObjects:
    def __init__(self, queryset):
        self.queryset = queryset

    def addResult(self, result, result_type, result_source):
        for item in self.queryset:
            item.addResult(result, result_type, result_source)