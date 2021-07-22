# This module contains functions that exctract raw data from files
# uploaded on the server. Each extractor should get file location path and
# return desired content that later will be handled by operation-type
# functions. Finally, a dictionary is exported from this file
# containing pairs: "key: function". The key will be mached later with
# DataObject.object_type string to resolve, which extractor should be used.

import pandas as pd
import numpy as np
from . import TIFsl


def TIFextractor(file_path):
    frames, _ = TIFsl.LoadTIF(file_path)
    return(frames)


def CSVextractor(file_path):
    return(pd.read_csv(file_path))


EXTRACTORS = {'TIF': TIFextractor, 'CSV': CSVextractor}
