#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 23 10:26:20 2019

@author: bioelectrics
"""
import PySpin
from math import floor
import os, sys, linecache
from multiprocessing import Process
from queue import Empty
import numpy as np
from PIL import Image
import multiCam_DLC_utils_v2 as clara
import time
from pathlib import Path
import ruamel.yaml
import serial
        
class multiCam_DLC_Cam(Process):
    def __init__(self, camq, camq_p2read, camID,
                 idList, cpt, aq, frm, array4feed, frmGrab,
                 com):
        super().__init__()
        self.camID = camID
        self.camq = camq
        self.camq_p2read = camq_p2read
        self.idList = idList
        self.cpt = cpt
        self.aq = aq
        self.frm = frm
        self.array4feed = array4feed
        self.frmGrab = frmGrab
        self.com = com
        
    def run(self):
        benchmark = False
        record = False
        ismaster = False
        record_frame_rate = 30
        user_cfg = clara.read_config()
        key_list = list()
        for cat in user_cfg.keys():
            key_list.append(cat)
        camStrList = list()
        for key in key_list:
            if 'cam' in key:
                camStrList.append(key)
        for s in camStrList:
            if self.camID == str(user_cfg[s]['serial']):
                camStr = s
        frameSml = np.zeros([200,200],'ubyte')
        aqW = self.cpt[3]
        aqH = self.cpt[1]
        frame = np.zeros([aqH,aqW],'ubyte')
        method = 'none'
        isstim = False
        if user_cfg['stimAxes'] == camStr:
            isstim = True
        
        while True:
            try:
                msg = self.camq.get(block=False)
#                print(msg)
                try:
                    if msg == 'InitM':
                        ismaster = True
                        system = PySpin.System.GetInstance()
                        cam_list = system.GetCameras()
                        cam = cam_list.GetBySerial(self.camID)
                        cam.Init()
                        cam.CounterSelector.SetValue(PySpin.CounterSelector_Counter0)
                        cam.CounterEventSource.SetValue(PySpin.CounterEventSource_ExposureStart)
                        cam.CounterEventActivation.SetValue(PySpin.CounterEventActivation_RisingEdge)
                        cam.CounterTriggerSource.SetValue(PySpin.CounterTriggerSource_ExposureStart)
                        cam.CounterTriggerActivation.SetValue(PySpin.CounterTriggerActivation_RisingEdge)
                        cam.LineSelector.SetValue(PySpin.LineSelector_Line2)
                        cam.V3_3Enable.SetValue(True)
                        cam.LineSelector.SetValue(PySpin.LineSelector_Line1)
                        cam.LineSource.SetValue(PySpin.LineSource_Counter0Active)
                        cam.LineInverter.SetValue(False)
                        cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
                        cam.TriggerSource.SetValue(PySpin.TriggerSource_Software)
                        cam.TriggerOverlap.SetValue(PySpin.TriggerOverlap_Off)
                        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
                        self.camq_p2read.put('done')
                    if msg == 'InitS':
                        system = PySpin.System.GetInstance()
                        cam_list = system.GetCameras()
                        cam = cam_list.GetBySerial(self.camID)
                        cam.Init()
                        cam.TriggerSource.SetValue(PySpin.TriggerSource_Line3)
                        cam.TriggerOverlap.SetValue(PySpin.TriggerOverlap_ReadOut)
                        cam.TriggerActivation.SetValue(PySpin.TriggerActivation_AnyEdge)
                        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
                        self.camq_p2read.put('done')
                    elif msg == 'Release':
                        cam.DeInit()
                        del cam
                        for i in self.idList:
                            cam_list.RemoveBySerial(str(i))
                        system.ReleaseInstance() # Release instance
                        self.camq_p2read.put('done')
                    elif msg == 'recordPrep':
                        proto_name = self.camq.get()
                        totTime = 0
                            
                        if not proto_name == 'none' and isstim:
                            totTime = -1
                            user_cfg = clara.read_config()
                            ruamelFile = ruamel.yaml.YAML()
                            protopath = Path(proto_name)
                            cgf_success = False
                            if os.path.exists(protopath):
                                try:
                                    with open(protopath, 'r') as ln:
                                        proto_cfg = ruamelFile.load(ln)
                                        cgf_success = True
                                except:
                                    print('Failed to open protocol')
                                    pass
                            else:
                                print('Protocol not found')
                                pass
                            
                            if cgf_success:
                                jumpDists = np.linspace(0,proto_cfg['max dist'],proto_cfg['iterations'])
                                while len(jumpDists) < proto_cfg['iterations']:
                                    jumpDists = np.concatenate((jumpDists,np.linspace(0,proto_cfg['max dist'],proto_cfg['iterations'])))
                                jumpDists = jumpDists[:proto_cfg['iterations']]
                                # randomly shuffling that vector of lanes
                                np.random.shuffle(jumpDists)
                                # yaml file's record delay
                                time.sleep(proto_cfg['record delay'])
                                # setting up other reference variables
                                stimiter = 0
                                self.tone_pair = proto_cfg['pairWithTone']
                                auto = True
                            else:
                                auto = False
                        
                        self.camq_p2read.put(totTime)
                        
                        path_base = self.camq.get()
                        if not path_base == 'space':
                            write_frame_rate = 30
                            s_node_map = cam.GetTLStreamNodeMap()
                            handling_mode = PySpin.CEnumerationPtr(s_node_map.GetNode('StreamBufferHandlingMode'))
                            if not PySpin.IsAvailable(handling_mode) or not PySpin.IsWritable(handling_mode):
                                print('Unable to set Buffer Handling mode (node retrieval). Aborting...\n')
                                return
                            handling_mode_entry = handling_mode.GetEntryByName('OldestFirst')
                            handling_mode.SetIntValue(handling_mode_entry.GetValue())
                            
                            if not(method == 'roi' and isstim):
                                avi = PySpin.SpinVideo()
                                option = PySpin.AVIOption()
                                option.frameRate = write_frame_rate
                                print(path_base)
                                avi.Open(path_base, option)
                                
                            f = open('%s_timestamps.txt' % path_base, 'w')
                            start_time = 0
                            capture_duration = 0
                            record = True
                            self.camq_p2read.put('done')
                    elif msg == 'Start':
                        cam.BeginAcquisition()
                        if ismaster:
                            cam.LineSelector.SetValue(PySpin.LineSelector_Line1)
                            cam.LineSource.SetValue(PySpin.LineSource_Counter0Active)
                            self.frm.value = 0
                            self.camq.get()
                            cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
                        if benchmark:
                            bA = 0
                            bB = 0
                            pre = time.perf_counter()
                        
                        while self.aq.value > 0:
                            image_result = cam.GetNextImage()
                            image_result = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
                            if record:
                                if start_time == 0:
                                    start_time = image_result.GetTimeStamp()
                                else:
                                    capture_duration = image_result.GetTimeStamp()-start_time
                                    start_time = image_result.GetTimeStamp()
                                    # capture_duration = capture_duration/1000/1000
                                    if not(method == 'roi' and isstim):
                                        avi.Append(image_result)
                                    f.write("%s\n" % round(capture_duration))
                            
                            
                            if self.aq.value == 1:
                                frame[:,:] = image_result.GetNDArray()
                                # Live feed array
                                if self.frmGrab.value == 0:
                                    self.array4feed[0:aqH*aqW] = frame.flatten()
                                    self.frmGrab.value = 1
                                    # if method == 'roi' and isstim:
                                    #     print(np.sum(frame,axis=0))
                            if ismaster:
                                self.frm.value+=1
                            if benchmark:
                                bA+=1
                                bB+=time.perf_counter()-pre
                                pre = time.perf_counter()
                            
                        self.camq.get()
                        
                        if record:
                            if not(method == 'roi' and isstim):
                                avi.Close()
                            f.close()
                            record = False
                            if benchmark:
                                was = round(bB/bA*1000*1000)
                                tried = round(1/record_frame_rate*1000*1000)
                                print(user_cfg[camStr]['nickname'] + ' actual: ' + str(was) + ' - target: ' + str(tried))
                                
                        cam.EndAcquisition()
                        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
                        self.frmGrab.value = 0
                        if ismaster:
                            cam.LineSelector.SetValue(PySpin.LineSelector_Line1)
                            cam.LineSource.SetValue(PySpin.LineSource_FrameTriggerWait)
                            cam.LineInverter.SetValue(True)
                        self.camq_p2read.put('done')
                    
                        
                    elif msg == 'updateSettings':
                        nodemap = cam.GetNodeMap()
                        binsize = user_cfg[camStr]['bin']
                        cam.BinningHorizontal.SetValue(int(binsize))
                        cam.BinningVertical.SetValue(int(binsize))
                        
                        # cam.IspEnable.SetValue(False)
                        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
                        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
                            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
                            return False
                        # Retrieve entry node from enumeration node
                        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
                        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
                                node_acquisition_mode_continuous):
                            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
                            return False
                        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
                        # Set integer value from entry node as new value of enumeration node
                        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
                        # Retrieve the enumeration node from the nodemap
                        node_pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
                        if PySpin.IsAvailable(node_pixel_format) and PySpin.IsWritable(node_pixel_format):
                            
                            # Retrieve the desired entry node from the enumeration node
                            node_pixel_format_mono8 = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('Mono8'))
                            if PySpin.IsAvailable(node_pixel_format_mono8) and PySpin.IsReadable(node_pixel_format_mono8):
                                # Retrieve the integer value from the entry node
                                pixel_format_mono8 = node_pixel_format_mono8.GetValue()
                                # Set integer as new value for enumeration node
                                node_pixel_format.SetIntValue(pixel_format_mono8)
                            else:
                                print('Pixel format mono 8 not available...')
                                
# =============================================================================
#                             node_pixel_format_BayerRG8 = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('BayerRG8'))
#                             if PySpin.IsAvailable(node_pixel_format_BayerRG8) and PySpin.IsReadable(node_pixel_format_BayerRG8):
#                                 # Retrieve the integer value from the entry node
#                                 pixel_format_BayerRG8 = node_pixel_format_BayerRG8.GetValue()
#                                 # Set integer as new value for enumeration node
#                                 node_pixel_format.SetIntValue(pixel_format_BayerRG8)
#                             else:
#                                 print('Pixel format BayerRG8 not available...')
#                         else:
#                             print('Pixel format not available...')
# =============================================================================
                        # Apply minimum to offset X
                        node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
                        if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
                            node_offset_x.SetValue(node_offset_x.GetMin())
                        else:
                            print('Offset X not available...')
                        # Apply minimum to offset Y
                        node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
                        if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
                            node_offset_y.SetValue(node_offset_y.GetMin())
                        else:
                            print('Offset Y not available...')
                        # Set maximum width
                        node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
                        if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
                            width_to_set = node_width.GetMax()
                            node_width.SetValue(width_to_set)
                        else:
                            print('Width not available...')
                        # Set maximum height
                        node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
                        if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
                            height_to_set = node_height.GetMax()
                            node_height.SetValue(height_to_set)
                        else:
                            print('Height not available...')
                        cam.GainAuto.SetValue(PySpin.GainAuto_Off)
                        # cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Off)
                        
                        # cam.AdcBitDepth.SetValue(PySpin.AdcBitDepth_Bit8)
                        
                        self.camq_p2read.put('done')
                        method = self.camq.get()
                        if (method == 'crop') or (method == 'roi'):

                            dimRef = self.cpt
                            user_cfg = clara.read_config()
                            record_frame_rate = int(user_cfg[camStr]['framerate'])
                            roi = user_cfg[camStr]['crop']
                            if method == 'roi' and isstim:
                                roi = user_cfg['stimXWYH']
                                record_frame_rate = int(record_frame_rate*user_cfg['stimRateX'])
                                
                            nodemap = cam.GetNodeMap()
                            
                            # Set width
                            node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
                            width_max = node_width.GetMax()
                            width_to_set = np.floor(width_max/dimRef[3]*roi[1]/4)*4
                            if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
                                node_width.SetValue(int(width_to_set))
                            else:
                                print('Width not available...')
                            # Set height
                            node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
                            height_max = node_height.GetMax()
                            height_to_set = np.floor(height_max/dimRef[1]*roi[3]/4)*4
                            if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
                                node_height.SetValue(int(height_to_set))
                            else:
                                print('Height not available...')
    
                            # Apply offset X
                            node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
                            offset_x = np.floor(width_max/dimRef[3]*roi[0]/4)*4
                            if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
                                node_offset_x.SetValue(int(offset_x))
                            else:
                                print('Offset X not available...')
                            # Apply offset Y
                            node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
                            offset_y = np.floor(height_max/dimRef[1]*roi[2]/4)*4
                            if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
                                node_offset_y.SetValue(int(offset_y))
                            else:
                                print('Offset Y not available...')
                                
                            aqW = int(width_to_set)
                            aqH = int(height_to_set)
                            
                        else:
                            aqW = self.cpt[3]
                            aqH = self.cpt[1]
                            record_frame_rate = int(30)
                        
                        frame = np.zeros([aqH,aqW],'ubyte')
                        
                        exposure_time_request = int(user_cfg[camStr]['exposure'])
                        
                        cam.AcquisitionFrameRateEnable.SetValue(False)
                        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
                            print('Unable to disable automatic exposure. Aborting...')
                            continue
                        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                        if cam.ExposureTime.GetAccessMode() != PySpin.RW:
                            print('Unable to set exposure time. Aborting...')
                            continue
                        # Ensure desired exposure time does not exceed the maximum
                        exposure_time_to_set = floor(1/record_frame_rate*1000*1000)
                        if exposure_time_request <= exposure_time_to_set:
                            exposure_time_to_set = exposure_time_request
                        max_exposure = cam.ExposureTime.GetMax()
                        exposure_time_to_set = min(max_exposure, exposure_time_to_set)
                        cam.ExposureTime.SetValue(exposure_time_to_set)
                        cam.AcquisitionFrameRateEnable.SetValue(True)
                        
                        # Ensure desired frame rate does not exceed the maximum
                        max_frmrate = cam.AcquisitionFrameRate.GetMax()
                        exposure_time_to_set = min(max_frmrate, record_frame_rate)
                        
                        cam.AcquisitionFrameRate.SetValue(record_frame_rate)
                        exposure_time_to_set = cam.ExposureTime.GetValue()
                        record_frame_rate = cam.AcquisitionFrameRate.GetValue()
                        # max_exposure = cam.ExposureTime.GetMax()
                        # self.camq_p2read.put(exposure_time_to_set)
                        print('frame rate ' + user_cfg[camStr]['nickname'] + ' : ' + str(round(record_frame_rate)))
                        # self.camq_p2read.put(max_exposure)
                        self.camq_p2read.put(record_frame_rate)
                        self.camq_p2read.put(width_to_set)
                        self.camq_p2read.put(height_to_set)

                except PySpin.SpinnakerException as ex:
                    exc_type, exc_obj, tb = sys.exc_info()
                    f = tb.tb_frame
                    lineno = tb.tb_lineno
                    filename = f.f_code.co_filename
                    linecache.checkcache(filename)
                    line = linecache.getline(filename, lineno, f.f_globals)
                    print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
                    print(ex)
                    print(self.camID + ' : ' + camStr)
                    
                    if msg == 'updateSettings':
                        self.camq_p2read.put(30)
                        self.camq_p2read.put(30)
                        self.camq_p2read.put(30)
                    else:
                        self.camq_p2read.put('done')
            
            except Empty:
                pass
        
        

        
    
    