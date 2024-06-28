# -*- coding: utf-8 -*-
"""
Created on Thu Jan 18 14:50:48 2024

@author: reynoben
"""
from __future__ import print_function
import wx
import wx.lib.dialogs
import wx.lib.scrolledpanel as SP
import os, sys, linecache
import glob
import cv2
import numpy as np
from pathlib import Path
import pandas as pd
#import matplotlib
#matplotlib.use('GTK3Agg') 
from matplotlib.figure import Figure
import matplotlib.colors as mcolors
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.animation import FFMpegWriter
import datetime, time
import ruamel.yaml
import pickle
from pathlib import PurePath
import shutil
import multiCam_DLC_utils_v2 as clara
from scipy.signal import savgol_coeffs, butter, filtfilt
#%%
bodyparts = ['Hand', 'Pellet']
coordinates = ['x', 'y', 'likelihood']
columns = pd.MultiIndex.from_product([bodyparts, coordinates], names=['parts', 'coordinates'])
filt_df = list()

h5list = [r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230821\christie2P\session005\20230821_christie2P_session005_sideCam-0000_264DLC_resnet50_Reach2PDec5shuffle1_1030000.h5',
          r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230821\christie2P\session005\20230821_christie2P_session005_frontCam-0000_264DLC_resnet50_Reach2PDec5shuffle1_1030000.h5']
df_list = list()
df_list.append(pd.read_hdf(h5list[0]))
df_list.append(pd.read_hdf(h5list[1]))
dlc_seg = 'DLC_resnet50_Reach2PDec5shuffle1_1030000'
for i in range(2):
    df = df_list[i]
    coordinates = ['x', 'y', 'likelihood']
    columns = pd.MultiIndex.from_product([bodyparts, coordinates], names=['parts', 'coordinates'])
    newdf = pd.DataFrame(columns=columns,index=range(len(df)))
    frm_count = np.shape(df)[0]
    full_frm_ref = np.arange(frm_count)
    all_categories = ['SdH_Flat', 'SdH_Spread', 'SdH_Grab', 'FtH_Reach', 'FtH_Grasp']
   
    likelihood_array = np.empty((len(df), len(all_categories)), dtype=np.float64)
    for cndx, cat in enumerate(all_categories):
        likelihood_array[:,cndx] = df[dlc_seg][cat]['likelihood'].values
    x_array = np.empty((len(df), len(all_categories)), dtype=np.float64)
    for cndx, cat in enumerate(all_categories):
        x_array[:,cndx] = df[dlc_seg][cat]['x'].values
    y_array = np.empty((len(df), len(all_categories)), dtype=np.float64)
    for cndx, cat in enumerate(all_categories):
        y_array[:,cndx] = df[dlc_seg][cat]['y'].values
    
    col_index = np.argmax(likelihood_array, axis=1)
    row_index = np.arange(len(df))
    p2keep = likelihood_array[row_index, col_index]
    x2keep = x_array[row_index, col_index]
    print(np.shape(x2keep))
    print(np.shape(newdf.loc[np.arange(len(df)), ('Hand', 'x')]))
    
    y2keep = y_array[row_index, col_index]
    
    p2keep_p = df[(dlc_seg, 'Pellet', 'likelihood')].values
    x2keep_p = df[(dlc_seg, 'Pellet', 'x')].values
    y2keep_p = df[(dlc_seg, 'Pellet', 'y')].values