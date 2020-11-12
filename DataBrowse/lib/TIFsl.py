"""
The simple module for handling TIFs in the Ultra Cold Gases Laboratory
at University of Warsaw. The purpose of this module is to allow fast
operation with TIFs EXACTLY designed for needs of our data acquisiton.
P. Arciszewski 2019
"""

import matplotlib.pyplot as plt
from PIL import Image, ImageSequence
import numpy
import time
import pathlib
import json
import matplotlib
matplotlib.use('Agg')


def SaveTIF(images_data, filepath, **kwargs):
    '''
    The function saves list of arrays containing images' data as a TIF.

    Prameters:
    images_data (list): List of arrays containing images' data. Please prepare
        data in a np.array-like format.
    filepath (str): A complete path for desired file location. It should also
        contain the filename.
    **description: Object that will be included in the TIF's
        description (tag #270). For example it can be string, float or JSON.
    '''

    if(((filepath[-4:] != '.tif') and (filepath[-5:] != '.tiff'))):
        raise ValueError(('Filepath should include both file name',
                         'and file extension (.tif or .tiff)!'))

    imlist = []

    for im in images_data:
        imlist.append(Image.fromarray(im))

    imlist[0].save(filepath, save_all=True,
                   append_images=imlist[1:], **kwargs)


def LoadTIF(filepath):
    '''
    The function loads TIF from a given location and extracts
        data and included description.

    Prameters:
    filepath (str): The filepath indicating the location of the TIF file.

    Returns:
    List: List of extracted images as np.arrays.
    Obj: Extracted object from the TIF's description field (TIF tag 270).
        If there is none, None is returned
    '''

    TIFile = Image.open(filepath)

    try:
        descr = TIFile.tag_v2[270]
    except KeyError:
        descr = None

    data_list = []

    for _, page in enumerate(ImageSequence.Iterator(TIFile)):
        data_list.append(numpy.array(page))

    return((data_list, descr))


def LoadTIFDescription(filepath):

    TIFile = Image.open(filepath)
    try:
        descr = TIFile.tag_v2[270]
    except KeyError:
        descr = None
    TIFile.close()
    if descr is None:
        return({})
    else:
        return(json.loads(descr))


def PrepareFilePath(sequency_name, base_directory, metadata):
    '''
    The function prepares complete filepath (that includes filename) of a TIF
        that is meant to be saved.

    This function prepares filepath following the rules used for data
    archivisation in the Laboratory. The desired approach is to collect data
    in a following directory system:
    MAIN_DIRECTORY_RELATED_TO_THE_INSTRUMENT/
    <YEAR>/<MONTH:MM>/<DAY:DD>/<SEQUENCY_NAME>(i)/SEQUENCY_NAME_METADATA.tif

    Parameters:
    sequency_name (str): Name of the sequency during which data were acquired.
    base_directory (str): Path of the base directory for the data acquisiton.
    metadata (dict): Detailed information about various parameters that were
        used for the experimental sequency

    Returns:
    Path: A complete filepath for the tif to save (based on pathlib).
    '''

    directory = pathlib.Path(base_directory)
    directory = directory / time.strftime("%Y", time.gmtime())
    directory = directory / time.strftime("%m", time.gmtime())
    directory = directory / time.strftime("%d", time.gmtime())

    i = 0
    while((directory / (sequency_name + '(%i)' % i)).exists()):
        i = i + 1

    directory = directory / (sequency_name + '(%i)' % i)

    metadata_name = ''

    for key, value in metadata.items():
        metadata_name = metadata_name + '_' + str(key) + '_' + str(value)

    file_name = sequency_name + '(%i)' % i + metadata_name + '.tif'

    return(directory / file_name)


def SaveDataFrame(data, metadata, sequency_name, base_directory):
    '''
    The Function saves data frame (a TIF) from separate arrays representing
    images with assumed directory pattern (see PrepareFilePath function).
    This function also creates necessary directories if they do not exist.

    Parameters:
    data (list): List of arrays containing images' data. Please prepare
        data in a np.array-like format.
    metadata (dict): Detailed information about various parameters that were
        used for the experimental sequency. The information
        will be saved as JSON. !If there is no metadata, pass an empty dict.!
    sequency_name (str): Name of the sequency during which data were acquired.
    base_directory (str): Path of the base directory for the data acquisiton.

    Returns:
    Path: A complete filepath of the saved TIF (based on pathlib).
    '''

    directory = PrepareFilePath(sequency_name, base_directory, metadata)
    directory.parent.mkdir(parents=True)
    SaveTIF(data, str(directory), description=json.dumps(metadata))
    return(directory)


def ConvertToPNG(source_directory, output_directory='.'):
    TIFile = Image.open(source_directory)
    source_dir = pathlib.Path(source_directory).parents[0]
    directory = source_dir / pathlib.Path(output_directory) / 'PNGs'
    directory.mkdir(parents=True, exist_ok=True)

    for i, page in enumerate(ImageSequence.Iterator(TIFile)):
        jpeg_path = directory / ('%i.png' % i)
        page.save(jpeg_path)

    return(directory)


def subtractAndSavePNG(source_dir, first, second, output_dir, name):
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dir_and_name = output_dir / name
    data = LoadTIF(source_dir)[0]
    result = numpy.array(data[first], numpy.int16) - numpy.array(data[second], numpy.int16)
    plt.figure(figsize=(9, 9))
    plt.axis('off')
    Norm = matplotlib.colors.Normalize(-1, 50, True)
    fig = plt.imshow(result, norm=Norm)
    fig.axes.get_xaxis().set_visible(False)
    fig.axes.get_yaxis().set_visible(False)
    plt.savefig(str(dir_and_name), dpi=100, bbox_inches='tight', pad_inches = 0)
    plt.close()
    return(str(dir_and_name))


def savePNG2(data, name, output_dir):
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dir_and_name = output_dir / name
    #plt.figure(figsize=(10, 10))
    plt.axis('off')
    fig = plt.imshow(data)
    fig.axes.get_xaxis().set_visible(False)
    fig.axes.get_yaxis().set_visible(False)
    plt.savefig(str(dir_and_name), dpi=200,  bbox_inches='tight', pad_inches = 0)
    plt.clf()
    plt.close()
    return(str(dir_and_name))


def saveJPG(data, name, output_dir, norm_min=0, norm_max=255):
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dir_and_name = output_dir / name
    cmap = matplotlib.cm.get_cmap('viridis')
    norm = matplotlib.colors.Normalize(norm_min, norm_max, True)
    scalarMap = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    im = scalarMap.to_rgba(data)
    im = numpy.uint8(im * 255)
    im = Image.fromarray(im)
    im = im.convert('RGB')
    im.save(str(dir_and_name), quality=90)
    return(str(dir_and_name))
