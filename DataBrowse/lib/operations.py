from . import TIFsl
import numpy as np
from scipy.optimize import curve_fit
import scipy.constants as const

# IN IMAGES FIRST AXIS IS REFFERED AS Y (WITH CORRESPONDING HEIGHT) AND SECOND AS X (WITH WITDH)
# input variable maybe or maybe not string. Please convert it to the proper type


def ondeD_Gaussain(x, amplitude, xo, sigma, offset):
    a = 1/(2*sigma**2)
    b = offset+amplitude*np.exp(-1*(a*((x-xo)**2)))
    return b


def lin(x, a, b):
    return a*x + b


def subtractImages(TIFFrame, id1, id2, norm_min, norm_max):
    id1 = int(id1)
    id2 = int(id2)
    norm_min = int(norm_min)
    norm_max = int(norm_max)
    data = TIFFrame.getData()
    result = np.array(data[id1], dtype=np.int16) - np.array(data[id2], dtype=np.int16)
    TIFFrame.addResult(result, 'IMG', 'simpleSubtraction', norm_min, norm_max)


def extractFrames(TIFFrame):
    data = TIFFrame.getData()
    i = 0
    for frame in data:
        TIFFrame.addResult(frame, 'IMG', 'image_' + str(i))
        i = i + 1


def sumROI(TIFFrame, id1, id2, x, width, y, height):
    x = int(x)
    width = int(width)
    y = int(y)
    height = int(height)
    id1 = int(id1)
    id2 = int(id2)
    data = TIFFrame.getData()
    result = np.sum(np.array(data[id1][y:y+height, x:x + width], dtype=np.int16) - np.array(data[id2][y:y+height, x:x + width], dtype=np.int16))
    TIFFrame.addResult(result, 'NUM', 'sum_over_roi')


def cropROI(TIFFrame, id1, id2, x, width, y, height):
    x = int(x)
    width = int(width)
    y = int(y)
    height = int(height)
    id1 = int(id1)
    id2 = int(id2)
    data = TIFFrame.getData()
    result = np.array(data[id1][y:y+height, x:x + width], dtype=np.int16) - np.array(data[id2][y:y+height, x:x+width], dtype=np.int16)
    TIFFrame.addResult(result, 'IMG', 'crop')


def extractCloud(img_with_atoms, img_without_atoms, background_image):
    with_a = img_with_atoms - background_image
    without_a = img_without_atoms - background_image
    # For numerical purposes we are setting 1 for pixels <= 0
    with_a[with_a <= 0] = 1
    without_a[without_a <= 0] = 1
    result = -np.log(with_a / without_a)
    return(result)


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
    x = np.linspace(0, size_x-1, size_x)
    y = np.linspace(0, size_y-1, size_y)
    x_initial = (1, int((width)/2), 20, 1)
    y_initial = (1, int((height)/2), 20, 1)
    x_data = np.sum(data_processed, axis=0)
    y_data = np.sum(data_processed, axis=1)

    x_res, _ = curve_fit(ondeD_Gaussain, x, x_data, x_initial)
    y_res, _ = curve_fit(ondeD_Gaussain, y, y_data, y_initial)

    TIFFrame.addResult(x_res[1], 'NUM', 'fitX')
    TIFFrame.addResult(y_res[1], 'NUM', 'fitY')
    TIFFrame.addResult(abs(x_res[2]), 'NUM', 'fitSigmaX')
    TIFFrame.addResult(abs(y_res[2]), 'NUM', 'fitSigmaY')


def calcAtomNo(TIFFrame, id_dark, id_withA, id_noA, x, width, y, height, atom, wavelength, size_coef):
    id_dark = int(id_dark)
    id_withA = int(id_withA)
    id_noA = int(id_noA)
    x = int(x)
    width = int(width)
    y = int(y)
    height = int(height)
    wavelength = float(wavelength)
    size_coef = float(size_coef)

    data = TIFFrame.getData()
    data_dark = data[id_dark][y:y+height, x:x + width]
    data_no_atoms = data[id_noA][y:y+height, x:x + width]
    data_with_atoms = data[id_withA][y:y+height, x:x + width]

    if(atom == 'k'):
        density_coef = 0.1945 * wavelength**2
    elif(atom == 'cs'):
        density_coef = 0.2228 * wavelength**2

    result = extractCloud(data_with_atoms, data_no_atoms, data_dark)

    result *= 1/density_coef
    result *= size_coef**2


    TIFFrame.addResult(np.sum(result), 'NUM', 'atom_no')


def getCloudImage(TIFFrame, id_dark, id_withA, id_noA, norm_max, norm_min):
    id_dark = int(id_dark)
    id_withA = int(id_withA)
    id_noA = int(id_noA)

    data = TIFFrame.getData()
    result = extractCloud(data[id_withA], data[id_noA], data[id_dark])

    result = result - np.min(result)
    result = (result / np.max(result))*255

    TIFFrame.addResult(result, 'IMG', 'cloud_img', norm_min, norm_max)


def calcAtomsTemperature(TIFFrames, specimen, scale_factor):
    if specimen == 'cs':
        m = 2.2069468e-25
    elif specimen == 'k':
        m = 6.80187119e-26

    times = []
    sizes_x = []
    sizes_y = []

    for frame in TIFFrames.queryset:
        times.append(frame.getProperties()['falltime'])
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

    TIFFrames.addResult((fitted_x[0]*m)/const.k, 'NUM', 'temp_x')
    TIFFrames.addResult((fitted_y[0]*m)/const.k, 'NUM', 'temp_y')
    TIFFrames.addResult(fitted_x[1]**0.5, 'NUM', 'sigma0_x')
    TIFFrames.addResult(fitted_y[1]**0.5, 'NUM', 'sigma0_y')


AVAILABLE_OPERATIONS = {
    'calcTemp': {
        'instance': calcAtomsTemperature,
        'properties': {
            'type': 'many',
            'variables': {
                'specimen': 'cs',
                'scale_factor': 3.17e-6
            }
        }
    },
    'calcAtomNo': {
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
                'wavelength': 852e-9,
                'size_coef': 3.17e-6
            }
        }
    },
    'simpleSubtraction': {'instance': subtractImages,
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
    'getCloudImage': {'instance': getCloudImage,
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

    'cropROI': {'instance': cropROI,
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

    'sumROI': {'instance': sumROI,
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

    'fitGauss': {'instance': fitGauss,
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
    'extractFrames': {'instance': extractFrames,
                          'properties': {
                                'type': 'one',
                                'variables': {}
                          }
                          },
}