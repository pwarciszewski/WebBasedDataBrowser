from . import TIFsl
import numpy as np
from scipy.optimize import curve_fit
import scipy.constants as const

# IN IMAGES FIRST AXIS IS REFFERED AS Y (WITH CORRESPONDING HEIGHT) AND SECOND AS X (WITH WITDH)
# input variable maybe or maybe not string. Please convert it to the proper type


def extractFrames(data_object):
    if data_object.object_type == 'TIF':
        data = data_object.getData()
        i = 0
        for frame in data:
            data_object.addResultIMG(frame, 'image_' + str(i))
            i = i + 1


def extractColumns(data_object):
    if data_object.object_type == 'CSV':
        data = data_object.getData()
        i = 0
        for column_index in data:
            data_object.addResultCSV(data[column_index], 'column_' + str(i))
            i = i + 1


def subtractImages(data_object, id1, id2, norm_min, norm_max):
    if data_object.object_type == 'TIF':
        id1 = int(id1)
        id2 = int(id2)
        norm_min = int(norm_min)
        norm_max = int(norm_max)
        data = data_object.getData()
        result = np.array(data[id1], dtype=np.int16) - np.array(data[id2], dtype=np.int16)
        data_object.addResultIMG(result, 'simpleSubtraction', norm_min, norm_max)


def addDummyProperty(data_object, value):
    data_object.addProperty('dummy_property', int(value))


def addDummyResult(data_object, value):
    data_object.addResultNUM(int(value), 'dummy_result')


AVAILABLE_OPERATIONS = {
    'extractFrames': {'instance': extractFrames,
                          'properties': {
                                'type': 'one',
                                'variables': {}
                          }
                     },

    'extractColumns': {'instance': extractColumns,
                          'properties': {
                                'type': 'one',
                                'variables': {}
                          }
                     },

    'dummy_result': {'instance': addDummyResult,
                          'properties': {
                                'type': 'one',
                                'variables': {'value':1}
                          }
                     },

    'dummy_property': {'instance': addDummyProperty,
                          'properties': {
                                'type': 'one',
                                'variables': {'value':1}
                          }
                     },



    'subtractImages': {'instance': subtractImages,
                       'properties': {'type': 'one',
                                      'variables': {'id1': 2,
                                                    'id2': 1,
                                                    'norm_min': 0,
                                                    'norm_max': 255}
                                     }
                       }

}

