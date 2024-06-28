"""
CLARA toolbox
https://github.com/wryanw/CLARA
W Williamson, wallace.williamson@ucdenver.edu

"""


from __future__ import print_function
from multiprocessing import Array, Queue, Value
from queue import Empty
import wx
import wx.lib.dialogs
import os
import numpy as np
import time, datetime
import ctypes
from deeplabcut.utils import auxiliaryfunctions
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from deeplabcut.multiCam_DLC import multiCam_DLC_PySpin_v1 as spin
from deeplabcut.multiCam_DLC import multiCam_DLC_utils_v2 as clara
from deeplabcut.multiCam_DLC import multiCam_RT_DLC_v1 as rtdlc
from deeplabcut.multiCam_DLC import CLARA_MINISCOPE as mscam
from deeplabcut.multiCam_DLC import compressVideos_v3 as compressVideos
import serial
import shutil

# ###########################################################################
# Class for GUI MainFrame
# ###########################################################################
class ImagePanel(wx.Panel):

    def __init__(self, parent, gui_size, axesCt, **kwargs):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)
            
        self.figure = Figure()
        self.axes = list()
        for a in range(axesCt):
            if gui_size[0] > gui_size[1]:
                self.axes.append(self.figure.add_subplot(1, axesCt, a+1, frameon=False))
                self.axes[a].set_position([a*1/axesCt+0.005,0.005,1/axesCt-0.01,1-0.01])
            else:
                self.axes.append(self.figure.add_subplot(axesCt, 1, a+1, frameon=False))
                self.axes[a].set_position([0.005,a*1/axesCt+0.005,1-0.01,1/axesCt-0.01])
            
            self.axes[a].xaxis.set_visible(False)
            self.axes[a].yaxis.set_visible(False)
            
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()

    def getfigure(self):
        """
        Returns the figure, axes and canvas
        """
        return(self.figure,self.axes,self.canvas)

class ControlPanel(wx.Panel):
    def __init__(self, parent, gui_size):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)
        
        wSpace = 16
        if gui_size[0] > gui_size[1]:
            ctrlsizer = wx.BoxSizer(wx.HORIZONTAL)
        else:
            ctrlsizer = wx.BoxSizer(wx.VERTICAL)
        self.figC = Figure()
        self.axC = self.figC.add_subplot(1, 1, 1)
        self.canC = FigureCanvas(self, -1, self.figC)
        ctrlsizer.Add(self.canC, 8, wx.ALL)
        
        self.com_ctrl = wx.CheckBox(self, id=wx.ID_ANY, label="Due COM")
        ctrlsizer.Add(self.com_ctrl, 1, wx.TOP | wx.LEFT | wx.RIGHT, wSpace)
        
        
        self.load_pellet = wx.Button(self, id=wx.ID_ANY, label="Load Pellet")
        ctrlsizer.Add(self.load_pellet, 1, wx.TOP, wSpace)
        
        self.send_stim = wx.Button(self, id=wx.ID_ANY, label="Stim")
        ctrlsizer.Add(self.send_stim, 1, wx.TOP, wSpace)
        
        self.bipolar = wx.CheckBox(self, id=wx.ID_ANY, label="Bipolar")
        ctrlsizer.Add(self.bipolar, 1, wx.TOP | wx.LEFT | wx.RIGHT, wSpace)
        
        
        self.fill = wx.Button(self, id=wx.ID_ANY, label="Fill Cone")
        ctrlsizer.Add(self.fill, 1, wx.TOP, wSpace)
        
        self.SetSizer(ctrlsizer)
        ctrlsizer.Fit(self)
        self.Layout()
        
    def getfigure(self):
        """
        Returns the figure, axes and canvas
        """
        return(self.figC,self.axC,self.canC)
        
    def getHandles(self):
        return self.bipolar,self.com_ctrl,self.load_pellet,self.send_stim,self.fill
#    
class WidgetPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)

class MainFrame(wx.Frame):
    """Contains the main GUI and button boxes"""
    def __init__(self, parent):
        
# Settting the GUI size and panels design
        displays = (wx.Display(i) for i in range(wx.Display.GetCount())) # Gets the number of displays
        screenSizes = [display.GetGeometry().GetSize() for display in displays] # Gets the size of each display
        index = 0 # For display 1.
        screenW = screenSizes[index][0]
        screenH = screenSizes[index][1]
        
        self.user_cfg = clara.read_config()
        key_list = list()
        for cat in self.user_cfg.keys():
            key_list.append(cat)
        self.camStrList = list()
        for key in key_list:
            if 'cam' in key:
                self.camStrList.append(key)
        self.slist = list()
        for s in self.camStrList:
            if not self.user_cfg[s]['ismaster']:
                self.slist.append(str(self.user_cfg[s]['serial']))
            else:
                self.masterID = str(self.user_cfg[s]['serial'])
        
        camCt = len(self.camStrList)
        
        self.gui_size = (800,1750)
        if screenW > screenH:
            self.gui_size = (1750,650)
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = 'CLARA DLC Video Explorer',
                            size = wx.Size(self.gui_size), pos = wx.DefaultPosition, style = wx.RESIZE_BORDER|wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText("")

        self.SetSizeHints(wx.Size(self.gui_size)) #  This sets the minimum size of the GUI. It can scale now!
        
###################################################################################################################################################
# Spliting the frame into top and bottom panels. Bottom panels contains the widgets. The top panel is for showing images and plotting!
        self.guiDim = 0
        if screenH > screenW:
            self.guiDim = 1
        topSplitter = wx.SplitterWindow(self)
        vSplitter = wx.SplitterWindow(topSplitter)
        self.image_panel = ImagePanel(vSplitter,self.gui_size, camCt)
        self.ctrl_panel = ControlPanel(vSplitter, self.gui_size)
        self.widget_panel = WidgetPanel(topSplitter)
        if self.guiDim == 0:
            vSplitter.SplitHorizontally(self.image_panel,self.ctrl_panel, sashPosition=self.gui_size[1]*0.75)
            vSplitter.SetSashGravity(0.5)
            self.widget_panel = WidgetPanel(topSplitter)
            topSplitter.SplitVertically(vSplitter, self.widget_panel,sashPosition=self.gui_size[0]*0.8)#0.9
        else:
            vSplitter.SplitVertically(self.image_panel,self.ctrl_panel, sashPosition=self.gui_size[0]*0.75)
            vSplitter.SetSashGravity(0.5)
            self.widget_panel = WidgetPanel(topSplitter)
            topSplitter.SplitHorizontally(vSplitter, self.widget_panel,sashPosition=self.gui_size[1]*0.7)#0.9
        topSplitter.SetSashGravity(0.5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

###################################################################################################################################################
# Add Buttons to the WidgetPanel and bind them to their respective functions.
        
        

        wSpace = 0
        wSpacer = wx.GridBagSizer(5, 5)
        
        camctrlbox = wx.StaticBox(self.widget_panel, label="Camera Control")
        bsizer = wx.StaticBoxSizer(camctrlbox, wx.HORIZONTAL)
        camsizer = wx.GridBagSizer(5, 5)
        
        bw = 76
        vpos = 0
        self.init = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Enable", size=(bw,-1))
        camsizer.Add(self.init, pos=(vpos,0), span=(1,3), flag=wx.ALL, border=wSpace)
        self.init.Bind(wx.EVT_TOGGLEBUTTON, self.initCams)
        
        self.reset = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Reset", size=(bw, -1))
        camsizer.Add(self.reset, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.reset.Bind(wx.EVT_BUTTON, self.camReset)
        
        self.update_settings = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Update Settings", size=(bw*2, -1))
        camsizer.Add(self.update_settings, pos=(vpos,6), span=(1,6), flag=wx.ALL, border=wSpace)
        self.update_settings.Bind(wx.EVT_BUTTON, self.updateSettings)
        self.update_settings.Enable(False)
        
        vpos+=1
        self.set_crop = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Set Crop")
        camsizer.Add(self.set_crop, pos=(vpos,0), span=(0,3), flag=wx.TOP | wx.BOTTOM, border=3)
        self.set_crop.Enable(False)
        
        text = wx.StaticText(self.widget_panel, label='User:')
        camsizer.Add(text, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        userlist = ['Anon','Gustavo','Michael']
        self.users = wx.Choice(self.widget_panel, size=(100, -1), id=wx.ID_ANY, choices=userlist)
        camsizer.Add(self.users, pos=(vpos,6), span=(1,6), flag=wx.ALL, border=wSpace)
        
        vpos+=1
        self.crop = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Crop", size=(bw, -1))
        camsizer.Add(self.crop, pos=(vpos,0), span=(0,3), flag=wx.TOP, border=0)
        self.crop.SetValue(True)
        
        self.mini_scope = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Miniscope")
        self.mini_scope.Bind(wx.EVT_CHECKBOX, self.miniScope)
        camsizer.Add(self.mini_scope, pos=(vpos,3), span=(0,6), flag=wx.TOP, border=5)
        self.widget_panel.SetSizer(wSpacer)
        self.mini_scope.Enable(False)
        
        
        vpos+=2
        self.play = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Live", size=(bw, -1))
        camsizer.Add(self.play, pos=(vpos,0), span=(1,3), flag=wx.ALL, border=wSpace)
        self.play.Bind(wx.EVT_TOGGLEBUTTON, self.liveFeed)
        self.play.Enable(False)
        
        self.rec = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Record", size=(bw, -1))
        camsizer.Add(self.rec, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.rec.Bind(wx.EVT_TOGGLEBUTTON, self.recordCam)
        self.rec.Enable(False)
        
        self.minRec = wx.TextCtrl(self.widget_panel, value='20', size=(50, -1))
        self.minRec.Enable(False)
        min_text = wx.StaticText(self.widget_panel, label='M:')
        camsizer.Add(self.minRec, pos=(vpos,7), span=(1,2), flag=wx.ALL, border=wSpace)
        camsizer.Add(min_text, pos=(vpos,6), span=(1,1), flag=wx.TOP, border=5)
        
        self.secRec = wx.TextCtrl(self.widget_panel, value='0', size=(50, -1))
        self.secRec.Enable(False)
        sec_text = wx.StaticText(self.widget_panel, label='S:')
        camsizer.Add(self.secRec, pos=(vpos,10), span=(1,2), flag=wx.ALL, border=wSpace)
        camsizer.Add(sec_text, pos=(vpos,9), span=(1,1), flag=wx.TOP, border=5)
        vpos+=4
        bsizer.Add(camsizer, 1, wx.EXPAND | wx.ALL, 5)
        wSpacer.Add(bsizer, pos=(0, 0), span=(vpos,3),flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)
#       
        wSpace = 10
        
        self.slider = wx.Slider(self.widget_panel, -1, 0, 0, 100,size=(300, -1), style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        wSpacer.Add(self.slider, pos=(vpos,0), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.slider.Enable(False)
        
        vpos+=1
        self.rtdlc = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="RT DLC")
        wSpacer.Add(self.rtdlc, pos=(vpos,0), span=(1,1), flag=wx.LEFT, border=wSpace)
        self.rtdlc.Bind(wx.EVT_CHECKBOX, self.dlcChecked)
        self.widget_panel.SetSizer(wSpacer)
        self.rtdlc.Enable(False)
        
        self.pause_dlc = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Pause DLC")
        wSpacer.Add(self.pause_dlc, pos=(vpos,1), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.pause_dlc.Bind(wx.EVT_TOGGLEBUTTON, self.pauseDLC)
        self.pause_dlc.Enable(False)
        
        self.compress_vid = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Compress Vid")
        wSpacer.Add(self.compress_vid, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.compress_vid.Bind(wx.EVT_BUTTON, self.compressVid)
        
        vpos+=1
        self.run_expt = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Run Expt ID:")
        wSpacer.Add(self.run_expt, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.run_expt.Bind(wx.EVT_TOGGLEBUTTON, self.runExpt)
        self.run_expt.Enable(False)
        
        self.expt_id = wx.TextCtrl(self.widget_panel, id=wx.ID_ANY, size=(150, -1), value="Mouse Ref")
        wSpacer.Add(self.expt_id, pos=(vpos,1), span=(0,2), flag=wx.LEFT, border=wSpace)
        self.expt_id.Bind(wx.EVT_TEXT, self.exptID)
        self.expt_id.Enable(False)
        
        vpos+=1
        start_text = wx.StaticText(self.widget_panel, label='Automate:')
        wSpacer.Add(start_text, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        
        self.auto_pellet = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Pellet")
        wSpacer.Add(self.auto_pellet, pos=(vpos,1), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.auto_pellet.SetValue(1)
        self.auto_stim = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Stimulus")
        wSpacer.Add(self.auto_stim, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.auto_stim.SetValue(1)
        
        vpos+=1
        self.quit = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Quit")
        wSpacer.Add(self.quit, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.quit.Bind(wx.EVT_BUTTON, self.quitButton)
        self.Bind(wx.EVT_CLOSE, self.quitButton)

        self.widget_panel.SetSizer(wSpacer)
        wSpacer.Fit(self.widget_panel)
        self.widget_panel.Layout()
        
        self.liveTimer = wx.Timer(self, wx.ID_ANY)
        self.recTimer = wx.Timer(self, wx.ID_ANY)
        self.shuffle = 1
        self.trainingsetindex = 0
        self.currAxis = 0
        self.x1 = 0
        self.y1 = 0
        self.im = list()
        
        
        self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        self.figC,self.axC,self.canC = self.ctrl_panel.getfigure()
        self.bipolar,self.com_ctrl,self.load_pellet,self.send_stim,self.fill = self.ctrl_panel.getHandles()
        self.com_ctrl.Bind(wx.EVT_CHECKBOX, self.comInit)
        self.bipolar.Bind(wx.EVT_CHECKBOX, self.biVmono)
        self.load_pellet.Bind(wx.EVT_BUTTON, self.comFun)
        self.send_stim.Bind(wx.EVT_BUTTON, self.comFun)
        self.fill.Bind(wx.EVT_BUTTON, self.comFun)
        self.axC.plot([0,100],[0,1])
        self.figC.canvas.draw()
        
        
        self.im = list()
        self.frmDims = [0,270,0,360]
        self.camIDlsit = list()
        self.dlc = Value(ctypes.c_byte, 0)
        self.camaq = Value(ctypes.c_byte, 0)
        self.frmaq = Value(ctypes.c_int, 0)
        self.com = Value(ctypes.c_int, 0)
        self.dir = Value(ctypes.c_int, 0)
        self.dir.value = 1
        self.dlc_frmct = 5
        self.pLoc = list()
        self.croprec = list()
        self.croproi = list()
        self.frame = list()
        self.frameBuff = list()
        self.dtype = 'uint8'
        self.array = list()
        self.frmGrab = list()
        self.size = self.frmDims[1]*self.frmDims[3]
        self.shape = [self.frmDims[1], self.frmDims[3]]
        frame = np.zeros(self.shape, dtype='ubyte')
        frameBuff = np.zeros(self.size, dtype='ubyte')
        self.circleH = list()
        self.circleP = list()
        self.markerSize = 6
        self.cropPts = list()    
        self.pX = list()
        self.pY = list()
        self.array = list()
        self.array4feed = list()
        for ndx, s in enumerate(self.camStrList):
            self.camIDlsit.append(str(self.user_cfg[s]['serial']))
            self.croproi.append(self.user_cfg[s]['crop'])
            self.array4feed.append(Array(ctypes.c_ubyte, self.size))
            self.frmGrab.append(Value(ctypes.c_byte, 0))
            self.frame.append(frame)
            self.frameBuff.append(frameBuff)
            self.im.append(self.axes[ndx].imshow(self.frame[ndx],cmap='gray'))
            self.im[ndx].set_clim(0,255)
            self.points = [-10,-10,1.0]
            
            circle = [patches.Circle((self.points[0], self.points[1]), radius=self.markerSize, fc = None , alpha=0)]
            self.circleH.append(self.axes[ndx].add_patch(circle[0]))
            circle = [patches.Circle((self.points[0], self.points[1]), radius=self.markerSize, fc = None , alpha=0)]
            self.circleP.append(self.axes[ndx].add_patch(circle[0]))
            circle = [patches.Circle((-10, -10), radius=5, fc=[0.8,0,0], alpha=0.0)]
            self.pLoc.append(self.axes[ndx].add_patch(circle[0]))
            
            cpt = self.croproi[ndx]
            self.cropPts.append(cpt)
            rec = [patches.Rectangle((cpt[0],cpt[2]), cpt[1], cpt[3], fill=False, ec = [0.25,0.25,0.75], linewidth=2, linestyle='-',alpha=0.0)]
            self.croprec.append(self.axes[ndx].add_patch(rec[0]))
                
            self.pX.append(Value(ctypes.c_int, 0))
            self.pY.append(Value(ctypes.c_int, 0))
            dlcA = list()
            dlcB = list()
            dlcC = list()
            for _ in range(self.dlc_frmct):
                dlcA.append(Array(ctypes.c_ubyte, 200*200))
                dlcB.append(Array(ctypes.c_ubyte, 200*200))
                dlcC.append(Array(ctypes.c_ubyte, 200*200))
            self.array.append([dlcA, dlcB, dlcC])
        
        self.figure.canvas.draw()
        self.users.SetSelection(0)
        
        self.config_path=self.user_cfg['config_path']
        self.cfg = auxiliaryfunctions.read_config(self.config_path)
        self.alpha = self.cfg['alphavalue']
        self.colormap = plt.get_cmap(self.cfg['colormap'])
        self.colormap = self.colormap.reversed()
        
        self.canvas.mpl_connect('button_press_event', self.onClick)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyPressed)
        
    def biVmono(self, event):
        if self.rtdlc.GetValue():
            if self.bipolar.GetValue():
                self.dlcq.put('B')
            else:
                self.dlcq.put('M')
                
    def comInit(self, event):
        if self.com_ctrl.GetValue():
            if self.rtdlc.GetValue():
                self.dlcq.put('initSerial')
            else:
                for i in range(10):
                    try:
                        self.ser = serial.Serial('/dev/ttyACM'+str(i), baudrate=115200)
                        break
                    except:
                        pass
        else:
            if self.rtdlc.GetValue():
                self.dlcq.put('stopSerial')
            else:
                self.ser.close()
        
    def comFun(self, event):
        if self.load_pellet == event.GetEventObject():
            if self.rtdlc.GetValue():
                self.dlcq.put('Q')
            else:
                self.ser.write(b'Q')
        elif self.fill == event.GetEventObject():
            if self.rtdlc.GetValue():
                self.dlcq.put('L')
            else:
                self.ser.write(b'L')
        elif self.send_stim == event.GetEventObject():
            if self.rtdlc.GetValue():
                self.dlcq.put('S')
            elif self.bipolar.GetValue():
                self.ser.write(b'T')
            else:
                self.ser.write(b'S')

    def OnKeyPressed(self, event):
        # print(event.GetModifiers())
        # print(event.GetKeyCode())
        if event.GetKeyCode() == wx.WXK_RETURN or event.GetKeyCode() == wx.WXK_NUMPAD_ENTER:
            if self.set_crop.GetValue():
                ndx = self.axes.index(self.cropAxes)
                s = self.camStrList[ndx]
                self.user_cfg[s]['crop'] = np.ndarray.tolist(self.croproi[ndx])
        
            clara.write_config(self.user_cfg)
            self.set_crop.SetValue(False)
            self.widget_panel.Enable(True)
            self.play.SetFocus()
        elif self.set_crop.GetValue():
            if event.GetKeyCode() == 314: #LEFT
                x = -1
                y = 0
            elif event.GetKeyCode() == 316: #RIGHT
                x = 1
                y = 0
            elif event.GetKeyCode() == 315: #UP
                x = 0
                y = -1
            elif event.GetKeyCode() == 317: #DOWN
                x = 0
                y = 1
            elif event.GetKeyCode() == 127: #DELETE
                if self.set_crop.GetValue():
                    ndx = self.axes.index(self.cropAxes)
                    self.croproi[ndx][0] = 0
                    self.croproi[ndx][2] = 0
                    self.croprec[ndx].set_alpha(0)
                    clara.write_config(self.user_cfg)
                    self.set_crop.SetValue(False)
                    self.widget_panel.Enable(True)
                    self.play.SetFocus()
                    self.figure.canvas.draw()
        else:
            event.Skip()
            
        if self.set_crop.GetValue():
            ndx = self.axes.index(self.cropAxes)
            self.croproi[ndx][0]+=x
            self.croproi[ndx][2]+=y
            self.drawROI()
            
    def drawROI(self):
        if self.set_crop.GetValue():
            ndx = self.axes.index(self.cropAxes)
            self.croprec[ndx].set_x(self.croproi[ndx][0])
            self.croprec[ndx].set_y(self.croproi[ndx][2])
            self.croprec[ndx].set_width(self.croproi[ndx][1])
            self.croprec[ndx].set_height(self.croproi[ndx][3])
            if not self.croproi[ndx][0] == 0:
                self.croprec[ndx].set_alpha(0.6)
        self.figure.canvas.draw()
        
        
    def onClick(self,event):
        self.user_cfg = clara.read_config()
        if self.set_crop.GetValue():
            self.cropAxes = event.inaxes
            ndx = self.axes.index(event.inaxes)
            s = self.camStrList[ndx]
            self.croproi[ndx] = self.user_cfg[s]['crop']
            roi_x = event.xdata
            roi_y = event.ydata
            self.croproi[ndx] = np.asarray([roi_x-self.croproi[ndx][1]/2,self.croproi[ndx][1],
                                            roi_y-self.croproi[ndx][3]/2,self.croproi[ndx][3]], int)
        self.drawROI()
                
            
    def compressVid(self, event):
        ok2compress = False
        try:
            if not self.mv.is_alive():
                self.mv.terminate()   
                ok2compress = True
            else:
                if wx.MessageBox("Compress when transfer completes?", caption="Abort", style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION):
                    while self.mv.is_alive():
                        time.sleep(10)
                    self.mv.terminate()   
                    ok2compress = True
        except:
            ok2compress = True
            
        if ok2compress:
            print('\n\n---- Please DO NOT close this GUI until compression is complete!!! ----\n\n')
            compressThread = compressVideos.CLARA_compress()
            compressThread.start()
            self.compress_vid.Enable(False)
            

    def camReset(self,event):
        self.initThreads()
        self.camaq.value = 2
        self.startAq()
        time.sleep(3)
        self.stopAq()
        self.deinitThreads()
        print('\n*** CAMERAS RESET ***\n')
    
    def runExpt(self,event):
        print('todo')
    def exptID(self,event):
        pass
        
    def liveFeed(self, event):
        if self.play.GetLabel() == 'Abort':
            self.rec.SetValue(False)
            self.recordCam(event)
            
            if wx.MessageBox("Are you sure?", caption="Abort", style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION):
                shutil.rmtree(self.sess_dir)
                time.sleep(5)
            self.play.SetValue(False)
                        
        elif self.play.GetValue() == True:
            if not self.liveTimer.IsRunning():
                self.camaq.value = 1
                self.startAq()
                self.liveTimer.Start(150)
                self.play.SetLabel('Stop')
            
            self.rtdlc.Enable(False)
            self.set_crop.Enable(False)
            self.rec.Enable(False)
            self.minRec.Enable(False)
            self.secRec.Enable(False)
            self.run_expt.Enable(False)
            self.expt_id.Enable(False)
            self.pause_dlc.SetValue(False)
            self.update_settings.Enable(False)
        else:
            if self.liveTimer.IsRunning():
                self.liveTimer.Stop()
            self.stopAq()
            time.sleep(2)
            self.play.SetLabel('Live')
            
            self.rtdlc.Enable(True)
            self.set_crop.Enable(True)
            self.rec.Enable(True)
            self.minRec.Enable(True)
            self.secRec.Enable(True)
            self.run_expt.Enable(True)
            self.expt_id.Enable(True)
            self.update_settings.Enable(True)
        
    def vidPlayer(self, event):
        if self.camaq.value == 2:
            return
        for ndx, im in enumerate(self.im):
            if self.frmGrab[ndx].value == 1:
                self.frameBuff[ndx][0:] = np.frombuffer(self.array4feed[ndx].get_obj(), self.dtype, self.size)
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.h[ndx], self.w[ndx]])
                self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx]] = frame
                im.set_data(self.frame[ndx])
                self.frmGrab[ndx].value = 0
                
                # self.croproi[ndx][2]
                x = self.pX[ndx].value
                y = self.pY[ndx].value
                pXY = [x+self.croproi[ndx][0],y+self.croproi[ndx][2]]
                # print(self.croproi[ndx][0])
                # print(x)
                # print(x+self.croproi[ndx][0])
                if x == 0:
                    self.pLoc[ndx].set_alpha(0.0)
                elif x == -1:
                    self.pause_dlc.SetValue(True)
                    self.pauseDLC(event)
                else:
                    self.pLoc[ndx].set_center(pXY)
                    self.pLoc[ndx].set_alpha(self.alpha)
                
            
        self.figure.canvas.draw()
        
        
    def autoCapture(self, event):
        self.sliderTabs+=self.sliderRate
        msg = '-'
        if self.mini_scope.GetValue():
            msg = self.ms2p.get(block=False)
        if (self.sliderTabs > self.slider.GetMax()) and not (msg == 'fail'):
            self.rec.SetValue(False)
            self.recordCam(event)
            self.slider.SetValue(0)
        else:
            self.slider.SetValue(round(self.sliderTabs))
            self.vidPlayer(event)
        
    def recordCam(self, event):
        if self.rec.GetValue():
            
            if int(self.minRec.GetValue()) == 0 and int(self.secRec.GetValue()) == 0:
                return
            liveRate = 500
            self.Bind(wx.EVT_TIMER, self.autoCapture, self.recTimer)
            totTime = int(self.secRec.GetValue())+int(self.minRec.GetValue())*60
            spaceneeded = 0
            for ndx, w in enumerate(self.aqW):
                recSize = w*self.aqH[ndx]*3*self.recSet[ndx]*totTime
                spaceneeded+=recSize
                
            self.slider.SetMax(100)
            self.slider.SetMin(0)
            self.slider.SetValue(0)
            self.sliderTabs = 0
            self.sliderRate = 100/(totTime/(liveRate/1000))
            
            date_string = datetime.datetime.now().strftime("%Y%m%d")
            base_dir = os.path.join(self.user_cfg['raw_data_dir'], date_string, self.user_cfg['unitRef'])
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            freespace = shutil.disk_usage(base_dir)[2]
            if spaceneeded > freespace:
                dlg = wx.MessageDialog(parent=None,message="There is not enough disk space for the requested duration.",
                                       caption="Warning!", style=wx.OK|wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                dlg.Destroy()
                self.rec.SetValue(False)
                return
            prev_expt_list = [name for name in os.listdir(base_dir) if name.startswith('session')]
            file_count = len(prev_expt_list)+1
            sess_string = '%s%03d' % ('session', file_count)
            self.sess_dir = os.path.join(base_dir, sess_string)
            if not os.path.exists(self.sess_dir):
                os.makedirs(self.sess_dir)
            # clara.read_metadata
            self.meta,ruamelFile = clara.metadata_template()
            for ndx, s in enumerate(self.camStrList):
                
                camset = {'serial':self.user_cfg[s]['serial'],
                      'ismaster':self.user_cfg[s]['ismaster'],
                      'crop':self.user_cfg[s]['crop'],
                      'exposure': self.user_cfg[s]['exposure'],
                      'framerate': self.user_cfg[s]['framerate'],
                      'bin': self.user_cfg[s]['bin'],
                      'nickname': self.user_cfg[s]['nickname']}
                self.meta[s]=camset
            
            self.meta['unitRef']=self.user_cfg['unitRef']
            self.meta['ID']=self.expt_id.GetValue()
            self.meta['placeholderA']='info'
            self.meta['placeholderB']='info'
            self.meta['Designer']='name'
            self.meta['Stim']='none'
            self.meta['StartTime']=datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            self.meta['Collection']='info'
            self.meta['config_path']=self.user_cfg['config_path']
            self.meta['trainingsetindex']=self.user_cfg['trainingsetindex']
            self.meta['shuffle']=self.user_cfg['shuffle']
            
            meta_name = '%s_%s_%s_metadata.yaml' % (date_string, self.user_cfg['unitRef'], sess_string)
            self.metapath = os.path.join(self.sess_dir,meta_name)
            
            for ndx, s in enumerate(self.camStrList):
                camID = str(self.user_cfg[s]['serial'])
                self.camq[camID].put('recordPrep')
                name_base = '%s_%s_%s_%s' % (date_string, self.user_cfg['unitRef'], sess_string, self.user_cfg[s]['nickname'])
                path_base = os.path.join(self.sess_dir,name_base)
                self.camq[camID].put(path_base)
                self.camq_p2read[camID].get()
                
            if self.rtdlc.GetValue():
                self.dlcq.put('recordPrep')
                event_base = '%s_%s_%s' % (date_string, self.user_cfg['unitRef'], sess_string)
                self.dlcq.put(os.path.join(self.sess_dir,event_base))
                self.dlc2p.get()
                
            if self.mini_scope.GetValue():
                self.msq.put('recordPrep')
                event_base = '%s_%s_%s' % (date_string, self.user_cfg['unitRef'], sess_string)
                self.msq.put(os.path.join(self.sess_dir,event_base))
                self.ms2p.get()
                
            self.rtdlc.Enable(False)
            self.set_crop.Enable(False)
            self.minRec.Enable(False)
            self.secRec.Enable(False)
            self.run_expt.Enable(False)
            self.expt_id.Enable(False)
            self.update_settings.Enable(False)
            
            if not self.recTimer.IsRunning():
                self.camaq.value = 1
                self.startAq()
                self.recTimer.Start(liveRate)
            self.rec.SetLabel('Stop')
            self.play.SetLabel('Abort')
        else:
            self.meta['duration (s)']=round(self.meta['duration (s)']*(self.sliderTabs/100))
            clara.write_metadata(self.meta, self.metapath)
            if self.recTimer.IsRunning():
                self.recTimer.Stop()
            self.stopAq()
            time.sleep(2)
            
            ok2move = False
            try:
                if not self.mv.is_alive():
                    self.mv.terminate()   
                    ok2move = True
            except:
                ok2move = True
            if self.play == event.GetEventObject():
                ok2move = False
            if ok2move:
                self.mv = clara.moveVids()
                self.mv.start()
            
            self.slider.SetValue(0)
            self.rec.SetLabel('Record')
            self.play.SetLabel('Play')
            
            if self.mini_scope.GetValue():
                self.msq.put('Stop')
            
            self.rtdlc.Enable(True)
            self.set_crop.Enable(True)
            self.minRec.Enable(True)
            self.secRec.Enable(True)
            self.run_expt.Enable(True)
            self.expt_id.Enable(True)
            self.update_settings.Enable(True)
    
    def initThreads(self):
        self.camq = dict()
        self.camq_p2read = dict()
        self.cam = list()
        for ndx, camID in enumerate(self.camIDlsit):
            self.camq[camID] = Queue()
            self.camq_p2read[camID] = Queue()
            self.cam.append(spin.multiCam_DLC_Cam(self.camq[camID], self.camq_p2read[camID],
                                               self.array[ndx], self.dlc, camID, self.camIDlsit,
                                               self.frmDims, self.dlc_frmct, self.camaq,
                                               self.frmaq, self.array4feed[ndx], self.frmGrab[ndx]))
            self.cam[ndx].start()
            
        self.camq[self.masterID].put('InitM')
        self.camq_p2read[self.masterID].get()
        for s in self.slist:
            self.camq[s].put('InitS')
            self.camq_p2read[s].get()
            
    def deinitThreads(self):
        for n, camID in enumerate(self.camIDlsit):
            self.camq[camID].put('Release')
            self.camq_p2read[camID].get()
            self.camq[camID].close()
            self.camq_p2read[camID].close()
            self.cam[n].terminate()
            
    def startAq(self):
        self.camaq.value = 1
        if self.rec.GetValue():
            if self.mini_scope.GetValue():
                self.msq.put('Start')
        if self.rtdlc.GetValue():
            self.dlcq.put('Start')
        self.camq[self.masterID].put('Start')
        for s in self.slist:
            self.camq[s].put('Start')
        self.camq[self.masterID].put('TrigOff')
        
    def stopAq(self):
        
        self.camaq.value = 0
        for s in self.slist:
            self.camq[s].put('Stop')
            self.camq_p2read[s].get()
        self.camq[self.masterID].put('Stop')
        self.camq_p2read[self.masterID].get()
        
    def updateSettings(self, event):
        self.user_cfg = clara.read_config()
        self.aqW = list()
        self.aqH = list()
        self.recSet = list()
        for n, camID in enumerate(self.camIDlsit):
            # try:
            self.camq[camID].put('updateSettings')
            self.camq_p2read[camID].get()
            if self.crop.GetValue():
                self.camq[camID].put('crop')
            else:
                self.camq[camID].put('full')
        
            self.recSet.append(self.camq_p2read[camID].get())
            self.aqW.append(self.camq_p2read[camID].get())
            self.aqH.append(self.camq_p2read[camID].get())
            # except:
            #     print('\nTrying to fix.  Please wait...\n')
            #     self.deinitThreads()
            #     self.camReset(event)
            #     self.initThreads()
            #     self.camq[camID].put('updateSettings')
            #     self.camq_p2read[camID].get()
            #     if self.crop.GetValue():
            #         self.camq[camID].put('crop')
            #     else:
            #         self.camq[camID].put('full')
            
            #     self.recSet.append(self.camq_p2read[camID].get())
            #     self.aqW.append(self.camq_p2read[camID].get())
            #     self.aqH.append(self.camq_p2read[camID].get())
                
    def initCams(self, event):
        if self.init.GetValue() == True:
            self.Enable(False)
            
            self.initThreads()
            self.updateSettings(event)
            
            self.Bind(wx.EVT_TIMER, self.vidPlayer, self.liveTimer)
            
            self.camaq.value = 1
            self.startAq()
            time.sleep(1)
            self.camaq.value = 0
            self.stopAq()
            self.x1 = list()
            self.x2 = list()
            self.y1 = list()
            self.y2 = list()
            self.h = list()
            self.w = list()
            self.dispSize = list()
            for ndx, im in enumerate(self.im):
                self.frame[ndx] = np.zeros(self.shape, dtype='ubyte')
                self.frameBuff[ndx][0:] = np.frombuffer(self.array4feed[ndx].get_obj(), self.dtype, self.size)
                if self.crop.GetValue():
                    self.h.append(self.croproi[ndx][3])
                    self.w.append(self.croproi[ndx][1])
                    self.y1.append(self.croproi[ndx][2])
                    self.x1.append(self.croproi[ndx][0])
                    self.set_crop.Enable(False)
                else:
                    self.h.append(self.frmDims[1])
                    self.w.append(self.frmDims[3])
                    self.y1.append(self.frmDims[0])
                    self.x1.append(self.frmDims[2])
                    self.set_crop.Enable(True)
                
                self.dispSize.append(self.h[ndx]*self.w[ndx])
                self.y2.append(self.y1[ndx]+self.h[ndx])
                self.x2.append(self.x1[ndx]+self.w[ndx])
                
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.h[ndx], self.w[ndx]])
                self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx]] = frame
                im.set_data(self.frame[ndx])
                
                    
                if not self.croproi[ndx][0] == 0:
                    self.croprec[ndx].set_alpha(0.6)

                            
            self.init.SetLabel('Release')
            self.rtdlc.Enable(True)
            self.play.Enable(True)
            self.rec.Enable(True)
            self.minRec.Enable(True)
            self.secRec.Enable(True)
            self.update_settings.Enable(True)
            self.crop.Enable(False)
            if self.user_cfg['unitRef'] == 'unit05':
                self.mini_scope.Enable(True)
                self.mini_scope.SetValue(True)
                self.miniScope(event)
            self.reset.Enable(False)
            self.Enable(True)
            self.figure.canvas.draw()
        else:
            self.init.SetLabel('Enable')
            
            for ndx, im in enumerate(self.im):
                self.frame[ndx] = np.zeros(self.shape, dtype='ubyte')
                im.set_data(self.frame[ndx])
                self.croprec[ndx].set_alpha(0)
                self.pLoc[ndx].set_alpha(0)

            self.figure.canvas.draw()
            
            self.rtdlc.Enable(False)
            self.set_crop.Enable(False)
            self.play.Enable(False)
            self.rec.Enable(False)
            self.minRec.Enable(False)
            self.secRec.Enable(False)
            self.crop.Enable(True)
            self.mini_scope.Enable(False)
            self.reset.Enable(True)
            self.mini_scope.SetValue(False)
            self.update_settings.Enable(False)
            self.deinitThreads()
                
    def dlcChecked(self, event):
        if self.rtdlc.GetValue():
            self.Enable(False)
            
            self.dlcq = Queue()
            self.dlc2p = Queue()
            autopellet = self.auto_pellet.GetValue()
            autostim = self.auto_stim.GetValue()
            self.rtThread = rtdlc.multiCam_RT(self.dlcq, self.dlc2p, self.array,
                                           self.dlc, self.camaq,
                                           autopellet, autostim, self.pX,
                                           self.pY, self.frmaq, self.recSet[0],
                                           self.bipolar.GetValue())
            self.rtThread.start()
            self.dlcq.put('initdlc')
            self.dlc2p.get()
            if self.com_ctrl.GetValue():
                self.ser.close()
            else:
                self.com_ctrl.SetValue(True)
                self.com_ctrl.Enable(False)
            self.dlcq.put('initSerial')
            
            self.run_expt.Enable(True)
            self.expt_id.Enable(True)
            self.pause_dlc.Enable(True)
            self.auto_pellet.Enable(False)
            self.auto_stim.Enable(False)
            self.pause_dlc.SetLabel('Pause DLC')
            self.pause_dlc.SetValue(False)
            self.Enable(True)
        else:
            self.dlcq.put('stopSerial')
            if self.com_ctrl.GetValue():
                self.comInit(event)
                self.com_ctrl.Enable(True)
            
            self.dlcq.close()
            self.dlc2p.close()
            self.rtThread.terminate()
            
            self.run_expt.Enable(False)
            self.expt_id.Enable(False)
            self.pause_dlc.Enable(False)
            self.auto_pellet.Enable(True)
            self.auto_stim.Enable(True)
            
    def pauseDLC(self, event):
        if self.pause_dlc.GetValue():
            self.dlcq.put('pause')
            self.pause_dlc.SetLabel('Resume DLC')
        else:
            self.dlcq.put('resume')
            self.pause_dlc.SetLabel('Pause DLC')

    def miniScope(self, event):
        if self.mini_scope.GetValue():
            self.msq = Queue()
            self.ms2p = Queue()
            self.msThread = mscam.CLARA_MS(self.msq, self.ms2p, self.camaq, self.frmaq)
            self.msThread.start()
            self.ms2p.get()
        else:
            self.msq.close()
            self.ms2p.close()
            self.msThread.terminate()
        
    def quitButton(self, event):
        """
        Quits the GUI
        """
        print('Close event called')
        if self.rtdlc.GetValue():
            self.rtdlc.SetValue(False)
            self.dlcChecked(event)
        if self.play.GetValue():
            self.play.SetValue(False)
            self.liveFeed(event)
        if self.rec.GetValue():
            self.rec.SetValue(False)
            self.recordCam(event)
        if self.init.GetValue():
            self.init.SetValue(False)
            self.initCams(event)
        if self.com_ctrl.GetValue():
            self.com_ctrl.SetValue(False)
            self.comInit(event)
        
        try:
            if not self.mv.is_alive():
                self.mv.terminate()
            else:
                print('File transfer in progress...\n')
                print('Do not record again until transfer completes.\n')
        except:
            pass
        
        try:
            if self.compressThread.is_alive():
                dlg = wx.MessageDialog(parent=None,message="Pausing until previous compression completes!",
                                       caption="Warning!", style=wx.OK|wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                dlg.Destroy()
                while self.compressThread.is_alive():
                    time.sleep(10)
            
            self.compressThread.terminate()   
        except:
            pass
        
        if self.mini_scope.GetValue():
            self.mini_scope.SetValue(False)
            self.miniScope(event)
        self.statusbar.SetStatusText("")
        self.Destroy()
    
def show():
    app = wx.App()
    MainFrame(None).Show()
    app.MainLoop()

if __name__ == '__main__':
    
    show()
