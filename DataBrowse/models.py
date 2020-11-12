from django.db import models
from .validaotrs import validate_file_extension
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
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


class DataFrameTIF(models.Model):
    upload = models.FileField(upload_to=generate_save_path,
                              validators=[validate_file_extension])
    data_frame_name = models.CharField(max_length=200)
    sequence_name = models.CharField(max_length=200)
    upload_date = models.DateTimeField('date uploaded', default=timezone.now)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return(self.data_frame_name)

    def generatePngs(self):
        concrete_file_name = pathlib.Path(self.upload.path).stem
        jpegs_dir = TIFsl.ConvertToPNG(self.upload.path, pathlib.Path(self.upload.path).parent / concrete_file_name)
        jpegs_list = pathlib.Path(jpegs_dir).glob('*.png')
        jpegs_url = pathlib.Path(self.upload.url).parent / concrete_file_name / 'PNGs'
        for path in jpegs_list:
            self.jpegpagefromtif_set.create(page_location=str(jpegs_url / path.name), page_id=path.stem) 

    def addProperties(self):
        properties = TIFsl.LoadTIFDescription(self.upload.path)
        for item in properties:
            self.tifproperties_set.create(key=item, value=properties[item])

    def getData(self):
        frame, _ = TIFsl.LoadTIF(self.upload.path)
        return(frame)

    def getProperties(self):
        _, properties = TIFsl.LoadTIF(self.upload.path)
        properties = json.loads(properties)
        for item in properties:
            try:
                properties[item] = float(properties[item])
            except ValueError:
                pass
        return(properties)

    def confirmProcessed(self):
        if(self.is_processed):
            pass
        else:
            self.is_processed = True
            super().save()


    def getResults(self):
        handle_table = {'IMG': self._handleExportOfIMG,
                        'NUM': self._handleExporOfNUM,
                        'KEYNUM': self._handleExportOfKEYNUM,
                        'FIT': self._handleExportOfFIT}

        result_set = self.tifresult_set.all()
        for_export = {}

        for result in result_set:
            for_export.update(handle_table[result.result_type](result))

        return(for_export)

    def _handleExporOfNUM(self, result_num):
        return({result_num.result_source: float(result_num.result_value)})

    def _handleExportOfIMG(self, result_img):
        return({result_img.result_source: result_img.result_location.path})

    def _handleExportOfKEYNUM(self, result_keynum):
        result_source = result_keynum.result_source
        result_basevalues = result_keynum.value
        result_values = {}
        for entry in result_basevalues:
            result_values.update({entry: float(result_basevalues[entry])})

        return({result_source: result_values})

    def _handleExportOfFIT(self, result_fit):
        # AS FITS ARE NOT IMPLEMENTED YET, I DONT KNOW WHAT TO PUT HERE
        return({})

    def _addResultIMG(self, data, result_source, *args):
        concrete_file_name = pathlib.Path(self.upload.path).stem
        result_dir = pathlib.Path(self.upload.path).parent / concrete_file_name / 'RESULTs'
        result_location = TIFsl.saveJPG(data, result_source + '.jpg', result_dir, *args)
        no_cache_tag = '?nocachetag=' + str(time.time())
        result_url = '/static' / pathlib.Path(self.upload.url).parent / concrete_file_name / 'RESULTs' / (result_source + '.jpg')
        result_url = str(result_url) + no_cache_tag
        current_set = self.tifresult_set.filter(result_location=result_location,
                                                result_source=result_source,
                                                result_type='IMG')
        # check if entry already exists; if not an entry is created or url is edited
        if len(current_set) == 0:
            self.tifresult_set.create(result_location=result_location,
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

    def _addResultFIT(self, value, result_source, *args):
        current_set = self.tifresult_set.filter(result_location='NOT APPLICABLE',
                                                result_source=result_source,
                                                result_type='FIT')

        if len(current_set) == 0:
            self.tifresult_set.create(result_location='NOT APPLICABLE',
                                      result_source=result_source,
                                      result_value=value,
                                      result_type='FIT')
        else:
            current_set[0].result_value = value

    def _addResultKEYNUM(self, value, result_source, *args):
        current_set = self.tifresult_set.filter(result_location='NOT APPLICABLE',
                                                result_source=result_source,
                                                result_type='KEYNUM')

        if len(current_set) == 0:
            self.tifresult_set.create(result_location='NOT APPLICABLE',
                                      result_source=result_source,
                                      result_value=value,
                                      result_type='KEYNUM')
        else:
            current_set[0].result_value = value

    def addResult(self, result, result_type, result_source, *args):
        actions = {'IMG': self._addResultIMG,
                   'NUM': self._addResultNUM,
                   'FIT': self._addResultFIT,
                   'KEYNUM': self._addResultKEYNUM}

        actions[result_type](result, result_source, *args)


class ManyDataFrames:
    def __init__(self, queryset):
        self.queryset = queryset

    def addResult(self, result, result_type, result_source):
        for item in self.queryset:
            item.addResult(result, result_type, result_source)


class JPEGPageFromTIF(models.Model):
    source_TIF = models.ForeignKey(DataFrameTIF, on_delete=models.CASCADE)
    page_location = models.FileField(max_length=1000)
    page_id = models.IntegerField()

    def __str__(self):
        return('page: %i' % self.page_id)


class TIFProperties(models.Model):
    source_TIF = models.ForeignKey(DataFrameTIF, on_delete=models.CASCADE)
    key = models.CharField(max_length=200)
    value = models.CharField(max_length=200)

    def __str__(self):
        return('%s: %s' % (self.key, self.value))


class TIFResult(models.Model):
    source_TIF = models.ForeignKey(DataFrameTIF, on_delete=models.CASCADE)
    result_source = models.CharField(max_length=1000)
    result_type = models.CharField(max_length=1000)
    result_location = models.FileField(max_length=1000)
    result_value = models.TextField()

    def __str__(self):
        return('Outcome from: %s' % self.result_source)


@receiver(post_save, sender=DataFrameTIF, dispatch_uid='post_upload_operations')
def postUploadOperations(sender, instance, **kwargs):
    if(not instance.is_processed):
        instance.addProperties() #Parses frame for its native properties
        for operation in init_ops.op_list:
            operations.AVAILABLE_OPERATIONS[operation['operation']]['instance'](instance, **operation['params'])
        instance.confirmProcessed()
