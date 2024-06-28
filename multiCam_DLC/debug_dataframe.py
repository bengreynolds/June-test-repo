"""
Created on Mon Jul 25 14:06:19 2022

@author: christielab
"""

from deeplabcut.multiCam_reachRT import multiCam_DLC_utils_v2 as clara
import numpy as np
import pandas as pd
import os
from pathlib import Path
import glob
import cv2
import imageio
#%%

sourceDir = r'C:\ProgramData\Anaconda3\envs\dlc\Lib\site-packages\deeplabcut\LocoMouseCorrections-christie-2022-07-25\labeled-data'
labelDirs = os.path.join(sourceDir, '*corrected')
labelDirs = glob.glob(labelDirs)
config_path = 'C:\ProgramData\Anaconda3\envs\dlc\Lib\site-packages\deeplabcut\LocoMouseCorrections-christie-2022-07-25\config.yaml'
cfg = clara.read_dlc_config(config_path)
bodyparts = cfg['bodyparts']
scorer = cfg['scorer']
for d in labelDirs:
    pngList = os.path.join(d,'*.png')
    pngList = glob.glob(pngList)
    imgNames = list()
    h5path = os.path.join(d,'CollectedData_christie.h5')
    df = pd.read_hdf(h5path,'df_with_missing')
    labeledParts = df.columns.get_level_values(1)
    nanList = list()
    for p in pngList:
        imgRef = os.path.split(p)[1]
        goodCt = 0
        for bp in bodyparts:
            if bp in labeledParts:
                if not np.isnan(df.loc[imgRef][scorer, bp, 'x' ]):
                    goodCt+=1
        nanList.append(goodCt)
    # datastats = df.count().values
    # runTot = np.zeros((len(bodyparts),1))
    # for n,s in enumerate(range(0,len(datastats),2)):
    #     runTot[n]+=datastats[s]
    #     print('%s: %d' % (bodyparts[n],datastats[s]))
    
    if np.any(np.asarray(nanList) < 20):
        print(os.path.split(d)[1])
        print(nanList)
#%%
from deeplabcut.utils import auxiliaryfunctions
sourceDir = r'C:\ProgramData\Anaconda3\envs\dlc\Lib\site-packages\deeplabcut\LocoMouseCorrections-christie-2022-07-25\labeled-data'
labelDirs = os.path.join(sourceDir, '*corrected')
labelDirs = glob.glob(labelDirs)
config_path = 'C:\ProgramData\Anaconda3\envs\dlc\Lib\site-packages\deeplabcut\LocoMouseCorrections-christie-2022-07-25\config.yaml'
cfg = clara.read_dlc_config(config_path)
bodyparts = cfg['bodyparts']
scorer = cfg['scorer']
video_sets = {}
for d in labelDirs:
    vidName = d+'.mp4'
    pngList = os.path.join(d,'*.png')
    pngList = glob.glob(pngList)
    if len(pngList):
        im = imageio.imread(pngList[0])
        
        width = int(im.shape[1])
        height = int(im.shape[0])
        video_sets[vidName] = {'crop': ', '.join(map(str, [0, width, 0, height]))}

cfg_file,ruamelFile = auxiliaryfunctions.create_config_template()
cfg_file['video_sets']=video_sets
project_path = r'C:\Users\christielab\Documents\Curators'
projconfigfile=os.path.join(str(project_path),'config.yaml')
# Write dictionary to yaml  config file
auxiliaryfunctions.write_config(projconfigfile,cfg_file)
#%%
filename = r'C:\ProgramData\Anaconda3\envs\dlc\Lib\site-packages\deeplabcut\LocoMouseTesting\labeled-data\20220526_idea05_session016_locoMouse_0002_L_corrected\CollectedData_WRW.h5'
# dataFrame = [pd.read_hdf(filename,'df_with_missing')]
dataFrame = [pd.read_hdf(filename)]

cfg = clara.read_dlc_config(config_path)
currFrame = 0
bodyparts = cfg['bodyparts']
videos = [r'Z:\Data\LocoMouse\Mouse_A718\05262022\session016\correctedVideos\20220526_idea05_session016_locoMouse_0002_L_corrected.mp4']
currFrame = 1
a = np.where(np.asarray(dataFrame[0].count(1))[currFrame+1:] > 0)
#%%

from skimage import io
import scipy.io as sio
from deeplabcut.utils import auxiliaryfunctions, auxfun_models
import deeplabcut
config = 'C:\ProgramData\Anaconda3\envs\dlc\Lib\site-packages\deeplabcut\LocoMouse-WRW-2022-05-30\config.yaml'
# Loading metadata from config file:
cfg = auxiliaryfunctions.read_config(config)
scorer = cfg['scorer']
project_path = cfg['project_path']
# Create path for training sets & store data there
trainingsetfolder = auxiliaryfunctions.GetTrainingSetFolder(cfg) #Path concatenation OS platform independent
auxiliaryfunctions.attempttomakefolder(Path(os.path.join(project_path,str(trainingsetfolder))),recursive=True)

"""
Merges all the h5 files for all labeled-datasets (from individual videos).
"""
AnnotationData=None
data_path = Path(os.path.join(project_path , 'labeled-data'))
videos = cfg['video_sets'].keys()
video_names = [Path(i).stem for i in videos]

for i in video_names:
    print(str(data_path / Path(i))+'/CollectedData_'+cfg['scorer']+'.h5')
    try:
        data = pd.read_hdf((str(data_path / Path(i))+'/CollectedData_'+cfg['scorer']+'.h5'),'df_with_missing')
        # data = data.dropna(how='all')
        # smlKeys = list(smlData.index.values)
        # smlKeyLong = list()
        # for sk in smlKeys:
        #     # print(str(Path(i)))
        #     # print(sk)
        #     smlKeyLong.append('labeled-data/'+str(Path(i))+'/'+sk[-1])
        # smlData.index = smlKeyLong
        # data = smlData
        if AnnotationData is None:
            AnnotationData=data
        else:
            AnnotationData=pd.concat([AnnotationData, data])
        
    except:
        try:
            scorer = 'christie'
            data = pd.read_hdf((str(data_path / Path(i))+'/CollectedData_'+scorer+'.h5'),'df_with_missing')
            smlData = data.dropna(how='all')
            smlKeys = list(smlData.index.values)
            smlKeyLong = list()
            for sk in smlKeys:
                # print(str(Path(i)))
                # print(sk)
                smlKeyLong.append('labeled-data/'+str(Path(i))+'/'+sk)
            smlData.index = smlKeyLong
            data = smlData
            if AnnotationData is None:
                AnnotationData=data
            else:
                AnnotationData=pd.concat([AnnotationData, data])
        except:
            pass
        
    pass
    # print((str(data_path / Path(i))+'/CollectedData_'+cfg['scorer']+'.h5'), " not found (perhaps not annotated)")

trainingsetfolder_full = Path(os.path.join(project_path,trainingsetfolder))
filename=str(str(trainingsetfolder_full)+'/'+'/CollectedData_'+cfg['scorer'])
AnnotationData.to_hdf(filename+'.h5', key='df_with_missing', mode='w')
AnnotationData.to_csv(filename+'.csv') #human readable.
deeplabcut.convertcsv2h5

#%%
import pandas as pd
scorer = 'WRW'
fn = r'C:\ProgramData\Anaconda3\envs\dlc\Lib\site-packages\deeplabcut\LocoMouse-WRW-2022-05-30\training-datasets\iteration-0\UnaugmentedDataSet_LocoMouseMay30\CollectedData_WRW.csv'
with open(fn) as datafile:
    next(datafile)
    if "individuals" in next(datafile):
        header = list(range(4))
    else:
        header = list(range(3))
data = pd.read_csv(fn, index_col=0, header=header)
data.columns = data.columns.set_levels([scorer], level="scorer")
data.to_hdf(fn.replace(".csv", ".h5"), key="df_with_missing", mode="w")
data.to_csv(fn)
#%%
runTot = np.zeros((len(bodyparts),1))
sumry = '---Subtotals---'
for ndx,df in enumerate(dataFrame):
    datastats = df.count().values
    if ndx > 0:
        sumry+='\n'
    sumry+= '\n%s:\n' % os.path.split(videos[ndx])[1]
    for n,s in enumerate(range(0,len(datastats),2)):
        if n > 0:
            sumry+=' - '
        runTot[n]+=datastats[s]
        sumry+='%s: %d' % (bodyparts[n],datastats[s])
        
sumry+='\n\n---Total Counts---\n'
for ndx, t in enumerate(runTot):
    if n > 0:
        sumry+=' - '
    sumry+='%s: %d' % (bodyparts[ndx],t)
    
data_path = Path(config_path).parents[0] / 'labeled-data'
f_list = [name for name in os.listdir(data_path)]
runTot = np.zeros((len(bodyparts),1))
for f in f_list:
    dataFiles = os.path.join(data_path, f, '*.h5')
    data_list = glob.glob(dataFiles)
    for d in data_list:
        if not len(d):
            continue
        print(d)
        statData = pd.read_hdf(d,'df_with_missing')
        datastats = statData.count().values
        for n,s in enumerate(range(0,len(datastats),2)):
            runTot[n]+=datastats[s]
            
sumry+='\n\n---Grand Total Counts---\n'
for ndx, t in enumerate(runTot):
    if n > 0:
        sumry+=' - '
    sumry+='%s: %d' % (bodyparts[ndx],t)