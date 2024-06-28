#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 23 10:26:20 2019

@author: bioelectrics
"""
import sys, linecache
from multiprocessing import Process
from queue import Empty
import multiCam_DLC_utils_v2 as clara
import time
import serial
# import pickle
        
class arduinoCtrl(Process):
    def __init__(self, ardq, ardq_p2read, frm, com, is_shift):
        super().__init__()
        self.ardq = ardq
        self.ardq_p2read = ardq_p2read
        self.frm = frm
        self.com = com
        self.is_shift = is_shift
        
    def run(self):
        serSuccess = False
        try:
            for i in range(10):
                try:
                    print('/dev/ttyACM'+str(i))
                    # self.ser = serial.Serial('/dev/ttyACM'+str(i), baudrate=115200, write_timeout = 0.001)
                    self.ser = serial.Serial('/dev/ttyACM'+str(i), write_timeout = 0.001)
                    serSuccess = True
                    break
                except:
                    pass
            
        except:
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
            print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
            
            self.com.value = -1
            print('\n ---Failed to connect to Arduino--- \n')
            self.ardq_p2read.put('done')
            
        
        time.sleep(2)
        print('---Arduino ready---\n')
        self.ardq_p2read.put('done')
        self.record = False 
        while True:
            if not serSuccess:
                self.com.value = -1
                continue
            try:
                if self.com.value > 0:
                    self.comFun()
                msg = self.ardq.get(block=False)
#                print(msg)
                try:
                    if msg == 'Release':
                        self.com.value = 5
                        self.comFun()
                        time.sleep(1)
                        self.ser.close()
                        self.ardq_p2read.put('done')
                    elif msg == 'recordPrep':
                        path_base = self.camq.get()
                        self.events = open('%s_events.txt' % path_base, 'w')
                        self.record = True
                        self.ardq_p2read.put('done')
                    elif msg == 'Stop':
                        if self.record:
                            self.events.close()
                            self.record = False
                except:
                    exc_type, exc_obj, tb = sys.exc_info()
                    f = tb.tb_frame
                    lineno = tb.tb_lineno
                    filename = f.f_code.co_filename
                    linecache.checkcache(filename)
                    line = linecache.getline(filename, lineno, f.f_globals)
                    print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
                    
                    self.ardq_p2read.put('done')
            
            except Empty:
                pass
    
    def comFun(self):
        stA = time.time()
        comVal = self.com.value
        attmpt = 0
        event = ''
        msg = 'none'
        while True:
            try:
                attmpt+=1
                stB = time.time()
                if comVal == 1:
                    # self.ser.write(b'Q')
                    if self.is_shift.value == 1:
                        return
                    msg = 'Q1x'
                    event = 'pellet_delivery'
                elif comVal == 2:
                    msg = 'R1x'
                elif comVal == 3:
                    msg = 'T1x'
                    event = 'toneA_played'
                elif comVal == 33:
                    msg = 'T2x'
                    event = 'toneB_played'
                elif comVal == 333:
                    msg = 'T3x'
                    event = 'toneC_played'
                elif comVal == 4:
                    msg = 'L1x'
                elif comVal == 5:
                    msg = 'U1x'
                    self.is_shift.value = 0
                elif comVal == 6:
                    msg = 'Z1x'
                    event = 'solenoid_trigger'
                    self.is_shift.value = 1
                elif comVal == 8:
                    user_cfg = clara.read_config()
                    msg = 'F'+str(user_cfg['toneFreqA'])+'x'
                elif comVal == 9:
                    user_cfg = clara.read_config()
                    msg = 'G'+str(user_cfg['toneFreqB'])+'x'
                elif comVal == 10:
                    user_cfg = clara.read_config()
                    msg = 'H'+str(user_cfg['toneFreqC'])+'x'
                elif comVal == 11:
                    user_cfg = clara.read_config()
                    msg = 'D'+str(user_cfg['toneDur'])+'x'
                elif comVal == 12:
                    if self.is_shift.value == 1:
                        return
                    user_cfg = clara.read_config()
                    shmag = user_cfg['shiftMag']
                    if shmag < 0:
                        msg = 'Y'+str(abs(shmag))+'x'
                    else:
                        msg = 'X'+str(abs(shmag))+'x'
                    event = str(user_cfg['jumpMag'])+'mm'
                elif comVal == 13:
                    msg = 'V1x'
                elif comVal == 14:
                    msg = 'W1x'
                self.ser.write(msg.encode())
                while True:
                    try:
                        if (time.time() > (stB + 0.1)):
                            break
                        elif self.ser.in_waiting:
                            line = ''
                            while self.ser.in_waiting:
                                c = self.ser.read()
                                line = line+str(c.strip())[2:-1]
                            # pickleFile = open("pickle.txt", 'wb')
                            # pickle.dump(line, pickleFile)
                            # pickleFile.close()
                            if self.record and len(event):
                                self.events.write("%s\t%s\n\r" % (event,self.frm.value))
                            print('%s in %d attempt(s)' % (line,attmpt))
                            self.com.value = 0
                            return
                    except:
                        pass
            except:
                exc_type, exc_obj, tb = sys.exc_info()
                f = tb.tb_frame
                lineno = tb.tb_lineno
                filename = f.f_code.co_filename
                linecache.checkcache(filename)
                line = linecache.getline(filename, lineno, f.f_globals)
                print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
                
            
            if (time.time() > (stA + 2)):
                print('Arduino send fail - %d - %s in %d tries' % (comVal,msg,attmpt))
                self.com.value = 0
                return
        
        
            
