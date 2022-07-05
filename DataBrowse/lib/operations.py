from . import TIFsl
import numpy as np
from scipy.optimize import curve_fit
import scipy.constants as const
import pandas as pd

# IN IMAGES FIRST AXIS IS REFFERED AS Y (WITH CORRESPONDING HEIGHT) AND SECOND AS X (WITH WITDH)
# input variable maybe or maybe not string. Please convert it to the proper type

SCALE_FACTOR = 4.08e-6
hbar = 6.62607004e-34 / 2/np.pi
kB = 1.38064852e-23

def ondeD_Gaussain(x, amplitude, xo, sigma, offset):
    a = 1/(2*sigma**2)
    b = offset+amplitude*np.exp(-1*(a*((x-xo)**2)))
    return b

def lin(x, a, b):
    return a*x + b

def extractCloud(img_with_atoms, img_without_atoms, background_image):
    with_a = img_with_atoms - background_image
    without_a = img_without_atoms - background_image
    # For numerical purposes we are setting 1 for pixels <= 0
    with_a[with_a <= 0] = 1
    without_a[without_a <= 0] = 1
    result = -np.log(with_a / without_a)
    return(result)

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

def getCloudImage(data_object, id_dark, id_withA, id_noA, norm_max, norm_min):
    id_dark = int(id_dark)
    id_withA = int(id_withA)
    id_noA = int(id_noA)

    data = data_object.getData()
    result = extractCloud(data[id_withA], data[id_noA], data[id_dark])

    result = result - np.min(result)
    result = (result / np.max(result))*255

    data_object.addResultIMG(result, 'cloud_img', norm_min, norm_max)

def fitGaussFluor(TIFFrame, id_withA, id_noA, x, width, y, height):
    id_withA = int(id_withA)
    id_noA = int(id_noA)
    x = int(x)
    width = int(width)
    y = int(y)
    height = int(height)

    data = TIFFrame.getData()
    data_no_atoms = data[id_noA][y:y+height, x:x + width]
    data_with_atoms = data[id_withA][y:y+height, x:x + width]

    data_processed = data_with_atoms - data_no_atoms

    size_y, size_x = data_processed.shape
    x_space = np.linspace(0, size_x-1, size_x)
    y_space = np.linspace(0, size_y-1, size_y)
    y_initial = (1, int((width)/2), 20, 1)
    x_initial = (1, int((height)/2), 20, 1)
    y_data = np.sum(data_processed, axis=1)
    x_data = np.sum(data_processed, axis=0)

    try:
        x_res, _ = curve_fit(ondeD_Gaussain, x_space, x_data, x_initial)
        y_res, _ = curve_fit(ondeD_Gaussain, y_space, y_data, y_initial)
    
    except RuntimeError:
        x_res = [-1,-1,-1]
        y_res = [-1,-1,-1]

    TIFFrame.addResultNUM(x_res[1], 'fitX')
    TIFFrame.addResultNUM(y_res[1], 'fitY')
    TIFFrame.addResultNUM(abs(x_res[2]), 'fitSigmaX')
    TIFFrame.addResultNUM(abs(y_res[2]), 'fitSigmaY')

def fitGauss(TIFFrame, id_withA, id_noA, id_background, x, width, y, height):
    id_withA = int(id_withA)
    id_noA = int(id_noA)
    x = int(x)
    width = int(width)
    y = int(y)
    height = int(height)

    data = TIFFrame.getData()
    data_no_atoms = data[id_noA][y:y+height, x:x + width]
    data_with_atoms = data[id_withA][y:y+height, x:x + width]
    data_background = data[id_background][y:y+height, x:x + width]

    data_processed = extractCloud(data_with_atoms, data_no_atoms, data_background)

    size_y, size_x = data_processed.shape
    x_space = np.linspace(0, size_x-1, size_x)
    y_space = np.linspace(0, size_y-1, size_y)
    y_initial = (1, int((width)/2), 20, 1)
    x_initial = (1, int((height)/2), 20, 1)
    y_data = np.sum(data_processed, axis=1)
    x_data = np.sum(data_processed, axis=0)

    try:
        x_res, _ = curve_fit(ondeD_Gaussain, x_space, x_data, x_initial)
        y_res, _ = curve_fit(ondeD_Gaussain, y_space, y_data, y_initial)
    
    except RuntimeError:
        x_res = [-1,-1,-1]
        y_res = [-1,-1,-1]

    TIFFrame.addResultNUM(x_res[1], 'fitX')
    TIFFrame.addResultNUM(y_res[1], 'fitY')
    TIFFrame.addResultNUM(abs(x_res[2]), 'fitSigmaX')
    TIFFrame.addResultNUM(abs(y_res[2]), 'fitSigmaY')

def calcAtomsTemperature(TIFFrames, specimen, scale_factor, fall_var_name):
    if specimen == 'cs':
        m = 2.2069468e-25
    elif specimen == 'k39':
        m = 6.47007511280837e-26
    elif specimen == 'k40':
        m = 6.636177440006e-26
    elif specimen == 'k41':
        m = 6.801870511611e-26
    else:
        raise ValueError('Unknown specimen! Available specimens are: cs, k39, k40, k41')

    scale_factor = float(scale_factor)

    times = []
    sizes_x = []
    sizes_y = []

    for frame in TIFFrames.queryset:
        times.append(float(frame.getProperties()[fall_var_name]))
        sizes_x.append(frame.getResults()['fitSigmaX'])
        sizes_y.append(frame.getResults()['fitSigmaY'])


    times = np.array(times)
    sizes_x = np.array(sizes_x)
    sizes_y = np.array(sizes_y)
    times = times*1e-3  # scale from ms to s
    sizes_x = sizes_x * scale_factor  # scale factor should be in m
    sizes_y = sizes_y * scale_factor

    times = times**2
    sizes_x = sizes_x**2
    sizes_y = sizes_y**2

    fitted_x, _ = curve_fit(lin, times, sizes_x)
    fitted_y, _ = curve_fit(lin, times, sizes_y)

    TIFFrames.addResultNUM((fitted_x[0]*m)/const.k, 'temp_x')
    TIFFrames.addResultNUM((fitted_y[0]*m)/const.k, 'temp_y')
    TIFFrames.addResultNUM(fitted_x[1]**0.5, 'size0_x')
    TIFFrames.addResultNUM(fitted_y[1]**0.5, 'size0_y')

def calcPhaseQI(data_object, col_Q, col_I, x1, x2):
    if data_object.object_type == 'CSV':
        x1 = int(x1)
        x2 = int(x2)

        data = data_object.getData()
        phase = np.arctan(
            data[col_Q][x1:x2]/data[col_I][x1:x2]
        )
        # phase %= np.pi 
        data_object.addResultCSV(phase, 'Phase_QI')
        data_object.addResultNUM(np.average(phase), 'Phase_QI_avg')

def calcAbsQI(data_object, col_Q, col_I, x1, x2):
    if data_object.object_type == 'CSV':
        x1 = int(x1)
        x2 = int(x2)

        data = data_object.getData()
        absorption = np.sqrt(
            np.power(data[col_Q][x1:x2], 2)
            + np.power(data[col_I][x1:x2], 2)
        )
        data_object.addResultCSV(absorption, 'Abs_QI')
        data_object.addResultNUM(np.average(absorption), 'Abs_QI_avg')

def avgCSV(data_object, col, x1, x2):
    if data_object.object_type == 'CSV':
        x1 = int(x1)
        x2 = int(x2)

        data = data_object.getData()
        avg = np.average(data[col][x1:x2])
        data_object.addResultNUM(avg, 'avg_{0}'.format(col))

def sumROI(TIFFrame, id1, id2, x, width, y, height):
    x = int(x)
    width = int(width)
    y = int(y)
    height = int(height)
    id1 = int(id1)
    id2 = int(id2)
    data = TIFFrame.getData()
    result = np.sum(np.array(data[id1][y:y+height, x:x + width], dtype=np.int16) - np.array(data[id2][y:y+height, x:x + width], dtype=np.int16))
    TIFFrame.addResultNUM(result, 'sum_over_roi')

def sumROIandSubtractBack(TIFFrame, id1, id2, x, width, y, height, x2, width2, y2, height2):
    x = int(x)
    width = int(width)
    y = int(y)
    height = int(height)
    x2 = int(x2)
    width2 = int(width2)
    y2 = int(y2)
    height2 = int(height2)
    id1 = int(id1)
    id2 = int(id2)
    data = TIFFrame.getData()
    back_average = np.average(np.array(data[id1][y2:y2+height2, x2:x2 + width2], dtype=np.int16) - np.array(data[id2][y2:y2+height2, x2:x2 + width2], dtype=np.int16))
    pre_result = np.array(data[id1][y:y+height, x:x + width], dtype=np.int16) - np.array(data[id2][y:y+height, x:x + width], dtype=np.int16) - back_average
    result = np.sum(pre_result)
    TIFFrame.addResultNUM(result, 'sum_over_roi_subtracted_back')

def calcAtomNo(TIFFrame, id_dark, id_withA, id_noA, x, width, y, height, atom, size_coef):
    id_dark = int(id_dark)
    id_withA = int(id_withA)
    id_noA = int(id_noA)
    x = int(x)
    width = int(width)
    y = int(y)
    height = int(height)
    size_coef = float(size_coef)

    data = TIFFrame.getData()
    data_dark = data[id_dark][y:y+height, x:x + width]
    data_no_atoms = data[id_noA][y:y+height, x:x + width]
    data_with_atoms = data[id_withA][y:y+height, x:x + width]

    if(atom == 'k'):
        density_coef = 0.1945 * 7.66701e-7 **2
    elif(atom == 'cs'):
        density_coef = 0.2228 * 8.52347e-7 **2

    result = extractCloud(data_with_atoms, data_no_atoms, data_dark)

    result *= 1/density_coef
    result *= size_coef**2

    TIFFrame.addResultNUM(np.sum(result), 'atom_no')

def drawProfile(data_object, id_1, id_2, x, y):
    id_1 = int(id_1)
    id_2 = int(id_2)

    data = data_object.getData()
    profile_x = np.array(data[id_1][y, :], dtype=np.int32) - np.array(data[id_2][y, :], dtype=np.int32)
    profile_y = np.array(data[id_1][:, x], dtype=np.int32) - np.array(data[id_2][:, x], dtype=np.int32)

    data_object.addResultCSV(pd.DataFrame(profile_x), 'profile_x')
    data_object.addResultCSV(pd.DataFrame(profile_y), 'profile_y')

def calcDensity(TIFFrame, id_dark, id_withA, id_noA, x, width, y, height, atom, size_coef):

    fitGauss(
        TIFFrame,
        id_withA,
        id_noA,
        id_dark,
        x,
        width,
        y,
        height
    )
    calcAtomNo(
        TIFFrame,
        id_dark,
        id_withA,
        id_noA,
        x,
        width,
        y,
        height,
        atom,
        size_coef
    )
    results = TIFFrame.getResults()
    print(results)
    volume = np.power(2*np.pi, 1.5) * results['fitSigmaX'] * results['fitSigmaY']**2
    volume *= size_coef**3
    n = results['atom_no']/volume

    TIFFrame.addResultNUM(n, 'density')

def calcPSD(TIFFrames, id_dark, id_withA, id_noA, x, width, y, height, atom, size_coef, fall_var_name):

    calcAtomsTemperature(
        TIFFrames,
        atom,
        size_coef,
        fall_var_name
    )

    for frame in TIFFrames.queryset:
        calcDensity(
            frame,
            id_dark,
            id_withA,
            id_noA,
            x,
            width,
            y,
            height,
            atom,
            size_coef
        )
        if atom == 'cs':
            m = 2.2069468e-25
        elif atom == 'k39':
            m = 6.47007511280837e-26
        elif atom == 'k40':
            m = 6.636177440006e-26
        elif atom == 'k41':
            m = 6.801870511611e-26

        results = frame.getResults()

        nPSD = results['density'] * np.power(2*np.pi*hbar**2, 1.5)
        nPSDx = nPSD / np.power(m*kB*results['temp_x'], 1.5)
        nPSDy = nPSD / np.power(m*kB*results['temp_y'], 1.5)

        frame.addResultNUM(nPSDx, 'PSD_x')
        frame.addResultNUM(nPSDy, 'PSD_y')

def normalizeSequence(TIFFrames, var_name):

    values = []

    for frame in TIFFrames.queryset:
        values.append(frame.getResults()[var_name])

    values = np.array(values)
    values -= np.amin(values)
    values /= np.amax(values)

    for i, frame in enumerate(TIFFrames.queryset):
        frame.addResultNUM(values[i], '{0}_norm'.format(var_name))

AVAILABLE_OPERATIONS = {
    'TIF_extractFrames': {
        'instance': extractFrames,
        'properties': {
            'type': 'one',
            'variables': {}
        }
    },
    'TIF_fitGauss': {
        'instance': fitGauss,
        'properties': {
            'type': 'one',
            'variables': {
                'id_background': 0,
                'id_withA': 1,
                'id_noA': 2,
                'x': 0,
                'width': 0,
                'y': 0,
                'height': 0
            }
        }
    },
    'TIF_subtractImages': {
        'instance': subtractImages,
        'properties': {
            'type': 'one',
            'variables': {
                'id1': 2,
                'id2': 1,
                'norm_min': 0,
                'norm_max': 255
            }
        }
    },
    'TIF_sumROI': {
        'instance': sumROI,
        'properties': {
            'type': 'one',
            'variables': {
                'id1': 2,
                'id2': 1,
                'x': 0,
                'width': 0,
                'y': 0,
                'height': 0
            }
        }
    },
    'TIF_sumROIBack': {
        'instance': sumROIandSubtractBack,
        'properties': {
            'type': 'one',
            'variables': {
                'id1': 2,
                'id2': 1,
                'x': 0,
                'width': 0,
                'y': 0,
                'height': 0,
                'x2': 0,
                'width2': 0,
                'y2': 0,
                'height2': 0
            }
        }
    },
    'TIF_calcAtomNo': {
        'instance': calcAtomNo,
        'properties': {
            'type': 'one',
            'variables': {
                'id_dark': 0,
                'id_withA': 1,
                'id_noA': 2,
                'x': 0,
                'width': 2000,
                'y': 0,
                'height': 2000,
                'atom': 'cs',
                'size_coef': SCALE_FACTOR
            }
        }
    },
    'TIF_plotProfile': {
        'instance': drawProfile,
        'properties': {
            'type': 'one',
            'variables': {
                'id_1': 0,
                'id_2': 1,
                'x': 0,
                'y': 0
            }
        }
    },
    'TIF_fitGaussFluor': {
        'instance': fitGaussFluor,
        'properties': {
            'type': 'one',
            'variables': {
                'id_withA': 1,
                'id_noA': 2,
                'x': 0,
                'width': 0,
                'y': 0,
                'height': 0
            }
        }
    },
    'TIF_getCloudImage': {
        'instance': getCloudImage,
        'properties': {
            'type': 'one',
            'variables': {
                'id_dark': 0,
                'id_withA': 1,
                'id_noA': 2,
                'norm_min': 0,
                'norm_max': 255
            }
        }
    },
    'TIF_calcDensity' : {
        'instance' : calcDensity,
        'properties' : {
            'type' : 'one',
            'variables' : {
                'id_dark': 0,
                'id_withA': 1,
                'id_noA': 2,
                'x': 0,
                'width': 2000,
                'y': 0,
                'height': 2000,
                'atom': 'cs',
                'size_coef': SCALE_FACTOR
            }
        }
    },
    'TIF_calcPSD' : {
        'instance' : calcDensity,
        'properties' : {
            'type' : 'many',
            'variables' : {
                'atom' : 'cs',
                'fall_var_name' : 'falltime',
                'id_dark': 0,
                'id_withA': 1,
                'id_noA': 2,
                'x': 0,
                'width': 2000,
                'y': 0,
                'height': 2000,
                'atom': 'cs',
                'size_coef': SCALE_FACTOR
            }
        }
    },
    'CSV_extractColumns': {
        'instance': extractColumns,
        'properties': {
            'type': 'one',
            'variables': {}
        }
    },
    'CSV_calcPhaseQI': {
        'instance': calcPhaseQI,
        'properties': {
            'type': 'one',
            'variables': {
                'col_Q': 'Q',
                'col_I': 'I',
                'x1': 0,
                'x2': -1
            }
        }
    },
    'CSV_calcAbsQI': {
        'instance': calcAbsQI,
        'properties': {
            'type': 'one',
            'variables': {
                'col_Q': 'Q',
                'col_I': 'I',
                'x1': 0,
                'x2': -1
            }
        }
    },
    'CSV_avgCSV': {
        'instance': avgCSV,
        'properties': {
            'type': 'one',
            'variables': {
                'col': '0',
                'x1': 0,
                'x2': -1
            }
        }
    },
    'RESULT_normSeq' : {
        'instance' : normalizeSequence,
        'properties' : {
            'type' : 'many',
            'variables' : {
                'var_name' : 'temp'
            }
        }
    },
    'RESULT_calcTemp': {
        'instance': calcAtomsTemperature,
        'properties': {
            'type': 'many',
            'variables': {
                'specimen': 'k39',
                'scale_factor': SCALE_FACTOR,
                'fall_var_name' : 'falltime'
            }
        }
    }
}
