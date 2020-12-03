from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, FileResponse, HttpResponseNotFound
from django.views import generic
import json
from django.views.decorators.csrf import csrf_exempt

from django.utils.datastructures import MultiValueDictKeyError

from .forms import UploadDataFrameForm
from .models import DataObject, ManyDataObjects
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models.signals import post_save
from django.dispatch import receiver

from .lib import TIFsl, operations
from pathlib import Path

import datetime

import zipfile
import tempfile

import os
from io import BytesIO

from . import init_ops


# MAIN FRONT END APP GENERIC TEMPLATE
class IndexView(generic.TemplateView):
    template_name = 'DataBrowse/index.html'
#


# DATA TREE EXPORT
MONTHS_DICT = {1: 'Jan.', 2: 'Feb.', 3: 'Mar.', 4: 'Apr.',
               5: 'May', 6: 'June', 7: 'Jul.', 8: 'Aug.', 9: 'Sep.',
               10: 'Oct.', 11: 'Nov.', 12: 'Dec.'}


def findInListIfnoThenCreate(target_list, label, expanded=False):
    index = -1
    for i in range(len(target_list)):
        if target_list[i]['label'] == label:
            index = i
            break

    if index == -1:
        target_list.insert(0, {'label': label, 'children': [], 'expanded': expanded})
        index = 0

    return index


def findInListIfnoThenCreateIteration(target_list, iter_token, expanded=False):
    index = -1
    for i in range(len(target_list)):
        if target_list[i]['iter_token'] == iter_token:
            index = i
            break

    if index == -1:
        label = len(target_list) + 1
        target_list.insert(0, {'label': label, 'children': [], 'expanded': expanded, 'iter_token': iter_token})
        index = 0

    return index


def getAllDataTree():
    now = datetime.datetime.now()
    data_entries = DataObject.objects.all()
    prepared_tree = []
    for item in data_entries:
        date = item.upload_date
        item_year = date.strftime('%Y')
        item_month = MONTHS_DICT[int(date.strftime('%m'))]
        item_day = date.strftime('%d')

        expanded_y = date.year == now.year
        expanded_m = date.month == now.month
        expanded_d = date.day == now.day

        item_seq_name = item.sequence_name
        item_name = item.data_frame_name
        item_iteration_token = item.iteration_token

        item_id = item.id

        year_index = findInListIfnoThenCreate(prepared_tree, item_year, expanded_y)
        month_index = findInListIfnoThenCreate(prepared_tree[year_index]['children'], item_month, expanded_m)
        day_index = findInListIfnoThenCreate(prepared_tree[year_index]['children'][month_index]['children'], item_day, expanded_d)
        seq_index = findInListIfnoThenCreate(prepared_tree[year_index]['children'][month_index]['children'][day_index]['children'], item_seq_name)
        iteration_index = findInListIfnoThenCreateIteration(prepared_tree[year_index]['children'][month_index]['children'][day_index]['children'][seq_index]['children'], item_iteration_token)

        prepared_tree[year_index]['children'][month_index]['children'][day_index]['children'][seq_index]['children'][iteration_index]['children'].insert(0, {'label': item_name, 'value': item_id})

    return(prepared_tree)


def getDataTree(request):
    return JsonResponse(getAllDataTree(), safe=False)
#


# FILE UPLOAD AND POST UPLOAD OPERATIONS CONTROL
def upload_file(request):
    if request.method == 'POST':
        form = UploadDataFrameForm(request.POST, request.FILES)
        if form.is_valid():
            dataobject_model = form.save(commit=False)
            try:
                properties_to_add = request.POST['properties']
                for prop in properties_to_add:
                    dataobject_model.addProperty(properties_to_add[prop])
            except MultiValueDictKeyError:
                pass
            dataobject_model.save() # Post upload operations heavylighting is postponed to release the client
            return HttpResponse('Succes')
        else:
            return(HttpResponseBadRequest('Check data'))
    else:
        form = UploadDataFrameForm()
    return render(request, 'DataBrowse/data_frame_upload.html', {
        'form': form
    })


@receiver(post_save, sender=DataObject, dispatch_uid='post_upload_operations')
def postUploadOperations(sender, instance, **kwargs):
    if(not instance.is_processed):
        # instance.addProperties()  # Parses frame for its native properties
        for operation in init_ops.op_list:
            operations.AVAILABLE_OPERATIONS[operation['operation']]['instance'](instance, **operation['params'])
        instance.confirmProcessed()
#


# OPERATIONS CONTROL
@csrf_exempt
def performOperation(request):
    result = 'Operation performed.'
    try:
        if request.method == "POST":
            command = json.loads(request.body)
            selected = command['selected']
            operation = command['operation']
            params = command['parameters']
            queryset = DataObject.objects.filter(id__in=selected)
        else:
            queryset = DataObject.objects.none()

        if operations.AVAILABLE_OPERATIONS[operation]['properties']['type'] == 'one':
            for item in queryset:
                operations.AVAILABLE_OPERATIONS[operation]['instance'](item, **params)

        elif operations.AVAILABLE_OPERATIONS[operation]['properties']['type'] == 'many':
            operations.AVAILABLE_OPERATIONS[operation]['instance'](ManyDataObjects(queryset), **params)

    except Exception as E:
        result = str(type(E).__name__)+": " + str(E)
    return(HttpResponse(json.dumps(result)))


def fetchOps(request):
    response = {}
    for op in operations.AVAILABLE_OPERATIONS:
        response[op] = operations.AVAILABLE_OPERATIONS[op]['properties']
    return(HttpResponse(json.dumps(response)))
#


# EXPORTING DATA API CONTROL
@csrf_exempt
def fetchRequestedData(request):
    command = json.loads(request.body)
    selected = command['selected']
    queryset = DataObject.objects.filter(id__in=selected)
    response = []

    for frame in queryset:
        property_dict = {}

        for tif_property in frame.dataobjectproperty_set.all():
            property_dict[tif_property.key] = tif_property.value

        result_dict = {}

        for result in frame.dataobjectresult_set.all():
            result_dict[result.result_source] = {'type':result.result_type, 'value':result.result_value}

        response.append({'id': frame.id,
                         'data': {'name': frame.data_frame_name,
                                  'sequence_name': frame.sequence_name,
                                  'properties': property_dict,
                                  'results': result_dict}})
    return(HttpResponse(json.dumps(response)))


def getNewestID(request):
    i = 0
    frames = DataObject.objects.order_by('-id')
    try:
        while(not frames[i].is_processed):
            i = i + 1
        nID = DataObject.objects.order_by('-id')[i].id
        return(JsonResponse(nID, safe=False))
    except IndexError:
        return(HttpResponseNotFound('Lack of processed data'))
#


# ROUTINES CONTROL
def fetchRoutine(request):
    return(HttpResponse(json.dumps(init_ops.op_list)))


@csrf_exempt
def setRoutine(request):
    new_routine = json.loads(request.body)['new_routine']
    init_ops.op_list = new_routine
    return(HttpResponse(json.dumps('set')))
#


# FILE DOWNLOAD CONTROL
class CleanFileResponse(FileResponse):
    def __init__(self, temp, **kwargs):
        super().__init__(open(temp.name, 'rb'), **kwargs)
        self.tmp = temp

    def close(self):
        super().close()
        self.tmp.close()
        os.unlink(self.tmp.name)


def getPathsFromIDs(ids):
    paths = []
    for item in ids:
        paths.append(DataObject.objects.get(id=item).upload.path)
    return paths


@csrf_exempt
def download_files(request):
    ids = json.loads(request.POST['ids'])
    filelist = getPathsFromIDs(ids)

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        with zipfile.ZipFile(tmp, 'w') as archive:
            for item in filelist:
                filename = os.path.basename(os.path.normpath(item))
                archive.write(item, filename)

        response = CleanFileResponse(tmp)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment; filename=files.zip'
        response['Content-Length'] = tmp.tell()

        return response
#
