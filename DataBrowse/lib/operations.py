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
            data_object.addResult(frame, 'IMG', 'image_' + str(i))
            i = i + 1


AVAILABLE_OPERATIONS = {
    'extractFrames': {'instance': extractFrames,
                          'properties': {
                                'type': 'one',
                                'variables': {}
                          }
                     },
}
