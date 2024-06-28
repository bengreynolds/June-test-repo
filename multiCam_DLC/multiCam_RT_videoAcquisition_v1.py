"""
CLARA toolbox
https://github.com/wryanw/CLARA
W Williamson, wallace.williamson@ucdenver.edu

"""


from __future__ import print_function
from multiprocessing import Array, Queue, Value
import wx
import wx.lib.dialogs
import os
import numpy as np
import time, datetime
import ctypes
from matplotlib.figure import Figure
import matplotlib.patches as patches
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
import multiCam_DLC_PySpin_v1 as spin
import multiCam_DLC_utils_v2 as clara
import arduinoCtrl_v1 as arduino
import compressVideos_v3 as compressVideos
import shutil
from pathlib import Path

# ###########################################################################
# Class for GUI MainFrame
# ###########################################################################
class ImagePanel(wx.Panel):

    def __init__(self, parent, gui_size, axesCt, **kwargs):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)
            
        self.figure = Figure()
        self.axes = list()
        if axesCt <= 3:
            if gui_size[0] > gui_size[1]:
                rowCt = 1
                colCt = axesCt
            else:
                colCt = 1
                rowCt = axesCt
            
        else:
            if gui_size[0] > gui_size[1]:
                rowCt = 2
                colCt = np.ceil(axesCt/2)
            else:
                colCt = 2
                rowCt = np.ceil(axesCt/2)
        a = 0
        for r in range(int(rowCt)):
            for c in range(int(colCt)):
                self.axes.append(self.figure.add_subplot(rowCt, colCt, a+1, frameon=True))
                self.axes[a].set_position([c*1/colCt+0.005,r*1/rowCt+0.005,1/colCt-0.01,1/rowCt-0.01])
                
        
                self.axes[a].xaxis.set_visible(False)
                self.axes[a].yaxis.set_visible(False)
                a+=1
            
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
        self.mlist = list()
        for s in self.camStrList:
            if not self.user_cfg[s]['ismaster']:
                self.slist.append(str(self.user_cfg[s]['serial']))
            else:
                self.mlist.append(str(self.user_cfg[s]['serial']))
        
        self.camCt = len(self.camStrList)
        
        self.gui_size = (800,1750)
        if screenW > screenH:
            self.gui_size = (1750,650)
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = 'RT Video Acquisition',
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
        self.image_panel = ImagePanel(topSplitter,self.gui_size, self.camCt)
        self.widget_panel = WidgetPanel(topSplitter)
        if self.guiDim == 0:
            topSplitter.SplitVertically(self.image_panel, self.widget_panel,sashPosition=int(self.gui_size[0]*0.75))
        else:
            topSplitter.SplitHorizontally(self.image_panel, self.widget_panel,sashPosition=int(self.gui_size[1]*0.75))
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
        self.init = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Initialize", size=(bw,-1))
        camsizer.Add(self.init, pos=(vpos,0), span=(1,3), flag=wx.ALL, border=wSpace)
        self.init.Bind(wx.EVT_TOGGLEBUTTON, self.initCams)
        
        self.crop = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Crop")
        camsizer.Add(self.crop, pos=(vpos,3), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.crop.SetValue(1)
        
        self.update_settings = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Update Settings", size=(bw*2, -1))
        camsizer.Add(self.update_settings, pos=(vpos,6), span=(1,6), flag=wx.ALL, border=wSpace)
        self.update_settings.Bind(wx.EVT_BUTTON, self.updateSettings)
        self.update_settings.Enable(False)
        
        vpos+=1
        self.set_pellet_pos = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Pellet", size=(bw, -1))
        camsizer.Add(self.set_pellet_pos, pos=(vpos,0), span=(0,3), flag=wx.TOP | wx.BOTTOM, border=3)
        self.set_pellet_pos.Bind(wx.EVT_TOGGLEBUTTON, self.setCrop)
        self.set_pellet_pos.Enable(False)
        
        
        self.set_roi = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Hand ROI", size=(bw, -1))
        camsizer.Add(self.set_roi, pos=(vpos,3), span=(0,3), flag=wx.TOP, border=0)
        self.set_roi.Bind(wx.EVT_TOGGLEBUTTON, self.setCrop)
        self.set_roi.Enable(False)
        
        self.set_crop = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Set Crop ROI", size=(bw*2, -1))
        camsizer.Add(self.set_crop, pos=(vpos,6), span=(0,6), flag=wx.TOP, border=0)
        self.set_crop.Bind(wx.EVT_TOGGLEBUTTON, self.setCrop)
        self.set_crop.Enable(False)
        
        vpos+=1
        self.play = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Live", size=(bw, -1))
        camsizer.Add(self.play, pos=(vpos,0), span=(1,3), flag=wx.ALL, border=wSpace)
        self.play.Bind(wx.EVT_TOGGLEBUTTON, self.liveFeed)
        self.play.Enable(False)
        
        self.rec = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Record", size=(bw, -1))
        camsizer.Add(self.rec, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.rec.Bind(wx.EVT_TOGGLEBUTTON, self.recordCam)
        self.rec.Enable(False)
        
        self.minRec = wx.SpinCtrl(self.widget_panel, value='20', size=(50, -1))
        self.minRec.Enable(False)
        min_text = wx.StaticText(self.widget_panel, label='M:')
        camsizer.Add(self.minRec, pos=(vpos,7), span=(1,2), flag=wx.ALL, border=wSpace)
        camsizer.Add(min_text, pos=(vpos,6), span=(1,1), flag=wx.TOP, border=5)
        
        self.set_stim = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Stim ROI", size=(bw, -1))
        camsizer.Add(self.set_stim, pos=(vpos,9), span=(0,3), flag=wx.TOP, border=0)
        self.set_stim.Bind(wx.EVT_TOGGLEBUTTON, self.setCrop)
        self.set_stim.Enable(False)
        
        camsize = 5
        vpos+=camsize
        bsizer.Add(camsizer, 1, wx.EXPAND | wx.ALL, 5)
        wSpacer.Add(bsizer, pos=(0, 0), span=(camsize,3),flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=wSpace)
        # wSpacer.Add(bsizer, pos=(0, 0), span=(vpos,3),flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=5)

        serctrlbox = wx.StaticBox(self.widget_panel, label="Serial Control")
        sbsizer = wx.StaticBoxSizer(serctrlbox, wx.HORIZONTAL)
        sersizer = wx.GridBagSizer(5, 5)
        
        vpos = 0
        
        self.load_pellet = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Feed", size=(bw, -1))
        sersizer.Add(self.load_pellet, pos=(vpos,0), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.load_pellet.Bind(wx.EVT_BUTTON, self.comFun)
        
        self.load_cone = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Load", size=(bw, -1))
        sersizer.Add(self.load_cone, pos=(vpos,3), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.load_cone.Bind(wx.EVT_BUTTON, self.comFun)
        
        self.trig_shift = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Shift", size=(bw, -1))
        sersizer.Add(self.trig_shift, pos=(vpos,6), span=(1,3), flag=wx.LEFT, border=wSpace)
        self.trig_shift.Bind(wx.EVT_BUTTON, self.comFun)
        
        self.trig_release = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Release", size=(bw, -1))
        sersizer.Add(self.trig_release, pos=(vpos,9), span=(1,3), flag=wx.LEFT, border=wSpace)
        self.trig_release.Bind(wx.EVT_BUTTON, self.comFun)
        
        vpos+=1
        
        self.jump_mag = wx.SpinCtrl(self.widget_panel, value=str(self.user_cfg['jumpMag']), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Jump (mm):')
        sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.jump_mag, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.jump_mag.SetMax(10)
        self.jump_mag.SetMin(0)
        self.jump_mag.SetValue(str(self.user_cfg['jumpMag']))
        self.jump_mag.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        self.step_to = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Step To", size=(bw, -1))
        sersizer.Add(self.step_to, pos=(vpos,6), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.step_to.Bind(wx.EVT_BUTTON, self.comFun)

        self.step_away = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Away", size=(bw, -1))
        sersizer.Add(self.step_away, pos=(vpos,9), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.step_away.Bind(wx.EVT_BUTTON, self.comFun)

        vpos+=1
        
        self.set_zero = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Set Zero", size=(bw, -1))
        sersizer.Add(self.set_zero, pos=(vpos,0), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.set_zero.Bind(wx.EVT_BUTTON, self.comFun)

        self.play_toneA = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Play A", size=(bw, -1))
        sersizer.Add(self.play_toneA, pos=(vpos,3), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.play_toneA.Bind(wx.EVT_BUTTON, self.comFun)

        self.play_toneB = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Play B", size=(bw, -1))
        sersizer.Add(self.play_toneB, pos=(vpos,6), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.play_toneB.Bind(wx.EVT_BUTTON, self.comFun)

        self.play_toneC = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Play C", size=(bw, -1))
        sersizer.Add(self.play_toneC, pos=(vpos,9), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.play_toneC.Bind(wx.EVT_BUTTON, self.comFun)

        vpos+=1
        
        self.tone_freqA = wx.SpinCtrl(self.widget_panel, value=str(self.user_cfg['toneFreqA']), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Freq A:')
        sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.tone_freqA, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.tone_freqA.SetMax(5500)
        self.tone_freqA.SetMin(100)
        self.tone_freqA.SetValue(str(self.user_cfg['toneFreqA']))
        self.tone_freqA.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        self.tone_dur = wx.SpinCtrl(self.widget_panel, value=str(self.user_cfg['toneDur']), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Dur (ms):')
        sersizer.Add(min_text, pos=(vpos,6), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.tone_dur, pos=(vpos,9), span=(1,3), flag=wx.ALL, border=wSpace)
        self.tone_dur.SetMax(5000)
        self.tone_dur.SetMin(10)
        self.tone_dur.SetValue(str(self.user_cfg['toneDur']))
        self.tone_dur.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        vpos+=1
        
        self.tone_freqB = wx.SpinCtrl(self.widget_panel, value=str(self.user_cfg['toneFreqB']), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Freq B:')
        sersizer.Add(min_text, pos=(vpos,0), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.tone_freqB, pos=(vpos,3), span=(1,3), flag=wx.ALL, border=wSpace)
        self.tone_freqB.SetMax(5500)
        self.tone_freqB.SetMin(100)
        self.tone_freqB.SetValue(str(self.user_cfg['toneFreqB']))
        self.tone_freqB.Bind(wx.EVT_SPINCTRL, self.comFun)

        self.tone_freqC = wx.SpinCtrl(self.widget_panel, value=str(self.user_cfg['toneFreqC']), size=(bw, -1))
        min_text = wx.StaticText(self.widget_panel, label='Freq C:')
        sersizer.Add(min_text, pos=(vpos,6), span=(1,3), flag=wx.TOP, border=wSpace)
        sersizer.Add(self.tone_freqC, pos=(vpos,9), span=(1,3), flag=wx.ALL, border=wSpace)
        self.tone_freqC.SetMax(5500)
        self.tone_freqC.SetMin(100)
        self.tone_freqC.SetValue(str(self.user_cfg['toneFreqC']))
        self.tone_freqC.Bind(wx.EVT_SPINCTRL, self.comFun)
        
        sersize = vpos
        vpos = camsize
        sbsizer.Add(sersizer, 1, wx.EXPAND | wx.ALL, 5)
        wSpacer.Add(sbsizer, pos=(vpos, 0), span=(sersize,3),flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=wSpace)
        self.serHlist = [self.load_pellet, self.play_toneA, self.play_toneB, self.load_cone,
                         self.trig_release, self.trig_shift, self.tone_freqA,
                         self.tone_freqB, self.tone_freqC, self.tone_dur, self.play_toneC,
                         self.jump_mag,self.step_to,self.step_away,self.set_zero]
        for h in self.serHlist:
            h.Enable(False)
        
        wSpace = 10
        vpos+=sersize
        
        self.slider = wx.Slider(self.widget_panel, -1, 0, 0, 100,size=(300, -1), style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        wSpacer.Add(self.slider, pos=(vpos,0), span=(0,3), flag=wx.LEFT, border=wSpace)
        self.slider.Enable(False)
        
        vpos+=1
        
        self.expt_id = wx.TextCtrl(self.widget_panel, id=wx.ID_ANY, value="SessionRef")
        wSpacer.Add(self.expt_id, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        
        start_text = wx.StaticText(self.widget_panel, label='Protocols:')
        wSpacer.Add(start_text, pos=(vpos,1), span=(0,1), flag=wx.LEFT, border=wSpace)
        
        usrdatadir = os.path.dirname(os.path.realpath(__file__))
        self.protoDir = os.path.join(usrdatadir, 'Protocols')
        protocol_list = [name for name in os.listdir(self.protoDir) if name.endswith('.yaml')]
        protocol_list = [name[:-5] for name in protocol_list]
        if not len(protocol_list):
            protocol_list = ['None']
        else:
            protocol_list = ['Protocol']+protocol_list
        self.protocol = wx.Choice(self.widget_panel, size=(100, -1), id=wx.ID_ANY, choices=protocol_list)
        wSpacer.Add(self.protocol, pos=(vpos,2), span=(0,1), flag=wx.ALL, border=wSpace)
        self.protocol.SetSelection(0)

        vpos+=2
        start_text = wx.StaticText(self.widget_panel, label='Automate:')
        wSpacer.Add(start_text, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        
        self.auto_pellet = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Pellet")
        wSpacer.Add(self.auto_pellet, pos=(vpos,1), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.auto_pellet.SetValue(1)
        
        self.auto_stim = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Stimulus")
        wSpacer.Add(self.auto_stim, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.auto_stim.SetValue(0)
        
        vpos+=3
        self.compress_vid = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Compress Vids")
        wSpacer.Add(self.compress_vid, pos=(vpos,0), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.compress_vid.Bind(wx.EVT_BUTTON, self.compressVid)

        self.quit = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Quit")
        wSpacer.Add(self.quit, pos=(vpos,2), span=(0,1), flag=wx.LEFT, border=wSpace)
        self.quit.Bind(wx.EVT_BUTTON, self.quitButton)
        self.Bind(wx.EVT_CLOSE, self.quitButton)

        self.widget_panel.SetSizer(wSpacer)
        wSpacer.Fit(self.widget_panel)
        self.widget_panel.Layout()
        
        self.disable4cam = [self.minRec, self.update_settings,
                            self.expt_id, self.set_pellet_pos, self.set_roi]
        
        self.onWhenCamEnabled = [self.play, self.rec, self.minRec,
                                 self.update_settings, self.set_pellet_pos, self.set_roi]

        self.liveTimer = wx.Timer(self, wx.ID_ANY)
        self.recTimer = wx.Timer(self, wx.ID_ANY)
        
        self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        self.figure.canvas.draw()

        self.pellet_x = self.user_cfg['pelletXY'][0]
        self.pellet_y = self.user_cfg['pelletXY'][1]
        
        self.is_shifted = Value(ctypes.c_byte, 0)
        self.roi = np.asarray(self.user_cfg['roiXWYH'], int)
        self.stimroi = np.asarray(self.user_cfg['stimXWYH'], int)
        self.failCt = 0
        
        self.currAxis = 0
        self.x1 = 0
        self.y1 = 0
        self.im = list()
        
        
        self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        
        self.im = list()
        self.frmDims = [0,270,0,360]
        self.camIDlsit = list()
        self.dlc = Value(ctypes.c_byte, 0)
        self.camaq = Value(ctypes.c_byte, 0)
        self.frmaq = Value(ctypes.c_int, 0)
        self.com = Value(ctypes.c_int, 0)
        self.pLoc = list()
        self.croprec = list()
        self.croproi = list()
        self.frame = list()
        self.frameBuff = list()
        self.dtype = 'uint8'
        self.frmGrab = list()
        self.size = self.frmDims[1]*self.frmDims[3]
        self.shape = [self.frmDims[1], self.frmDims[3]]
        frame = np.zeros(self.shape, dtype='ubyte')
        frameBuff = np.zeros(self.size, dtype='ubyte')
        self.markerSize = 6
        self.cropPts = list()    
        self.array4feed = list()
        self.roirec = list()
        self.stimrec = list()
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
            
            circle = [patches.Circle((-10, -10), radius=5, fc=[0.8,0,0], alpha=0.0)]
            self.pLoc.append(self.axes[ndx].add_patch(circle[0]))
            
            cpt = self.roi
            rec = [patches.Rectangle((cpt[0],cpt[2]), cpt[1], cpt[3], fill=False, ec = [0.25,0.75,0.25], linewidth=2, linestyle='-',alpha=0.0)]
            self.roirec.append(self.axes[ndx].add_patch(rec[0]))
            
            cpt = self.stimroi
            rec = [patches.Rectangle((cpt[0],cpt[2]), cpt[1], cpt[3], fill=False, ec = [0.5,0.5,0.5], linewidth=2, linestyle='-',alpha=0.0)]
            self.stimrec.append(self.axes[ndx].add_patch(rec[0]))
            
            cpt = self.croproi[ndx]
            self.cropPts.append(cpt)
            rec = [patches.Rectangle((cpt[0],cpt[2]), cpt[1], cpt[3], fill=False, ec = [0.25,0.25,0.75], linewidth=2, linestyle='-',alpha=0.0)]
            self.croprec.append(self.axes[ndx].add_patch(rec[0]))
            
            
            if self.user_cfg['axesRef'] == s:
                self.pelletAxes = self.axes[ndx]
                self.pLoc[ndx].set_center([self.pellet_x,self.pellet_y])
            if self.user_cfg['stimAxes'] == s:
                self.stimAxes = self.axes[ndx]
        
        self.figure.canvas.draw()
        
        self.alpha = 0.8
        
        self.canvas.mpl_connect('button_press_event', self.onClick)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyPressed)
        
        
    def comFun(self, event):
      # case 'A': //servoMax
      # case 'B': //servoMin
      # case 'C': //servoBaseVal
      # case 'D': // Set tone duration (ms)
      # case 'F': // Set tone frequency
      # case 'T': // Play tone 
      # case 'E': // No solenoid
      # case 'I': // Solenoid in
      # case 'O': // Solenoid out
      # case 'U': // Solenoids neutral
      # case 'Y': // Trigger solenoid
      # case 'P': // Get proximity reading
      # case 'L': // Load pellets into reservoir
      # case 'R': // Drop elevator to reveal pellet
      # case 'Q': // Raise elevator to load a single pellet
      
        if self.com.value < 0:
            return
        waitval = 0
        while not self.com.value == 0:
            time.sleep(1)
            waitval+=1
            if waitval > 10:
                break
        evobj = event.GetEventObject()
        if self.load_pellet == evobj:
            self.com.value = 1
        elif self.play_toneA == evobj:
            self.com.value = 3
        elif self.play_toneB == evobj:
            self.com.value = 33
        elif self.play_toneC == evobj:
            self.com.value = 333
        elif self.load_cone == evobj:
            self.com.value = 4
        elif self.trig_release == evobj:
            self.com.value = 5
        elif self.trig_shift == evobj:
            self.com.value = 6
        elif self.tone_freqA == evobj:
            self.user_cfg['toneFreqA'] = int(self.tone_freqA.GetValue())
            clara.write_config(self.user_cfg)
            time.sleep(1)
            self.com.value = 8
        elif self.tone_freqB == evobj:
            self.user_cfg['toneFreqB'] = int(self.tone_freqB.GetValue())
            clara.write_config(self.user_cfg)
            time.sleep(1)
            self.com.value = 9
        elif self.tone_freqC == evobj:
            self.user_cfg['toneFreqC'] = int(self.tone_freqC.GetValue())
            clara.write_config(self.user_cfg)
            time.sleep(1)
            self.com.value = 10
        elif self.tone_dur == evobj:
            self.user_cfg['toneDur'] = int(self.tone_dur.GetValue())
            clara.write_config(self.user_cfg)
            time.sleep(1)
            self.com.value = 11
        elif self.jump_mag == evobj:
            self.user_cfg = clara.read_config()
            newPos = self.jump_mag.GetValue()
            prevMag = self.user_cfg['jumpMag']
            self.user_cfg['shiftMag'] = prevMag-newPos
            self.user_cfg['jumpMag'] = newPos
            clara.write_config(self.user_cfg)
            time.sleep(1)
            self.com.value = 12
        elif self.step_to == evobj:
            self.com.value = 13
        elif self.step_away == evobj:
            self.com.value = 14
        elif self.set_zero == evobj:
            self.user_cfg['jumpMag'] = 0
            clara.write_config(self.user_cfg)
            
        
    def setCrop(self, event):
        self.widget_panel.Enable(False)
        
    def OnKeyPressed(self, event):
        # print(event.GetModifiers())
        # print(event.GetKeyCode())
        x = 0
        y = 0
        if event.GetKeyCode() == wx.WXK_RETURN or event.GetKeyCode() == wx.WXK_NUMPAD_ENTER:
            if self.set_pellet_pos.GetValue():
                self.user_cfg['pelletXY'][0] = self.pellet_x
                self.user_cfg['pelletXY'][1] = self.pellet_y
            elif self.set_roi.GetValue():
                self.user_cfg['roiXWYH'] = np.ndarray.tolist(self.roi)
            elif self.set_stim.GetValue():
                self.user_cfg['stimXWYH'] = np.ndarray.tolist(self.stimroi)
            elif self.set_crop.GetValue():
                ndx = self.axes.index(self.cropAxes)
                s = self.camStrList[ndx]
                self.user_cfg[s]['crop'] = np.ndarray.tolist(self.croproi[ndx])
        
            clara.write_config(self.user_cfg)
            self.set_pellet_pos.SetValue(False)
            self.set_roi.SetValue(False)
            self.set_stim.SetValue(False)
            self.set_crop.SetValue(False)
            self.widget_panel.Enable(True)
            self.play.SetFocus()
        elif self.set_pellet_pos.GetValue() or self.set_roi.GetValue() or self.set_crop.GetValue() or self.set_stim.GetValue():
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
                elif self.set_crop.GetValue():
                    ndx = self.axes.index(self.stimAxes)
                    self.stimroi[ndx][0] = 0
                    self.stimroi[ndx][2] = 0
                    self.stimrec[ndx].set_alpha(0)
                    clara.write_config(self.user_cfg)
                    self.set_stim.SetValue(False)
                    self.widget_panel.Enable(True)
                    self.play.SetFocus()
                    self.figure.canvas.draw()
        else:
            event.Skip()
            
        if self.set_pellet_pos.GetValue():
            self.pellet_x+=x
            self.pellet_y+=y
            self.drawROI()
        elif self.set_roi.GetValue():
            self.roi[0]+=x
            self.roi[2]+=y
            self.drawROI()
        elif self.set_stim.GetValue():
            self.stimroi[0]+=x
            self.stimroi[2]+=y
            self.drawROI()
        elif self.set_crop.GetValue():
            ndx = self.axes.index(self.cropAxes)
            self.croproi[ndx][0]+=x
            self.croproi[ndx][2]+=y
            self.drawROI()
            
            
        if self.set_crop.GetValue():
            ndx = self.axes.index(self.cropAxes)
            self.croproi[ndx][0]+=x
            self.croproi[ndx][2]+=y
            self.drawROI()
            
    def drawROI(self):
        ndx = self.axes.index(self.pelletAxes)
        if self.set_pellet_pos.GetValue():
            self.pLoc[ndx].set_center([self.pellet_x,self.pellet_y])
            self.pLoc[ndx].set_alpha(0.6)
        elif self.set_roi.GetValue():
            self.roirec[ndx].set_x(self.roi[0])
            self.roirec[ndx].set_y(self.roi[2])
            self.roirec[ndx].set_width(self.roi[1])
            self.roirec[ndx].set_height(self.roi[3])
            self.roirec[ndx].set_alpha(0.6)
        elif self.set_stim.GetValue():
            ndx = self.axes.index(self.stimAxes)
            self.stimrec[ndx].set_x(self.stimroi[0])
            self.stimrec[ndx].set_y(self.stimroi[2])
            self.stimrec[ndx].set_width(self.stimroi[1])
            self.stimrec[ndx].set_height(self.stimroi[3])
            self.stimrec[ndx].set_alpha(0.6)
        elif self.set_crop.GetValue():
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
        if self.set_pellet_pos.GetValue():
            if self.stimAxes == event.inaxes:
                print('Stimulus camera must not be the pellet-detecting camera')
                self.set_pellet_pos.SetValue(False)
                self.widget_panel.Enable(True)
                return
            ndx = self.axes.index(event.inaxes)
            self.pelletAxes = event.inaxes
            self.user_cfg['axesRef'] = self.camStrList[ndx]
            self.pellet_x = int(event.xdata)
            self.pellet_y = int(event.ydata)
        elif self.set_roi.GetValue():
            if self.stimAxes == event.inaxes:
                print('Stimulus camera must not be the pellet-detecting camera')
                self.set_roi.SetValue(False)
                self.widget_panel.Enable(True)
                return
            ndx = self.axes.index(event.inaxes)
            self.pelletAxes = event.inaxes
            self.user_cfg['axesRef'] = self.camStrList[ndx]
            self.roi = np.asarray(self.user_cfg['roiXWYH'], int)
            roi_x = event.xdata
            roi_y = event.ydata
            self.roi = np.asarray([roi_x-self.roi[1]/2,self.roi[1],roi_y-self.roi[3]/2,self.roi[3]], int)
        elif self.set_stim.GetValue():
            if self.pelletAxes == event.inaxes:
                print('Stimulus camera must not be the pellet-detecting camera')
                self.set_stim.SetValue(False)
                self.widget_panel.Enable(True)
                return
            ndx = self.axes.index(event.inaxes)
            self.stimAxes = event.inaxes
            self.user_cfg['stimAxes'] = self.camStrList[ndx]
            self.stimroi = np.asarray(self.user_cfg['stimXWYH'], int)
            roi_x = event.xdata
            roi_y = event.ydata
            self.stimroi = np.asarray([roi_x-self.stimroi[1]/2,self.stimroi[1],roi_y-self.stimroi[3]/2,self.stimroi[3]], int)
        elif self.set_crop.GetValue():
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
                if not self.pellet_x == 0:
                    if not self.roi[0] == 0:
                        self.pellet_timing = time.time()
                        self.pellet_status = 2
                self.camaq.value = 1
                self.startAq()
                self.liveTimer.Start(150)
                self.play.SetLabel('Stop')
            
            for h in self.disable4cam:
                h.Enable(False)
        else:
            if self.liveTimer.IsRunning():
                self.liveTimer.Stop()
            self.stopAq()
            time.sleep(2)
            self.play.SetLabel('Live')
            
            for h in self.disable4cam:
                h.Enable(True)
        
    def pelletHandler(self, pim, roi):
        # events    0 - release pellet
        #           1 - load pellet
        #           2 - waiting to lose it
        if self.com.value < 0:
            return
        objDetected = False
        # print(pim)
        if pim > 50:
            objDetected = True
        if self.is_shifted.value == 1:
            self.is_shifted.value = 2
            self.shift_timing = time.time()
        elif self.is_shifted.value == 2:
            if (time.time()-self.shift_timing) > 2:
                if pim < 50:
                    self.com.value = 5
                    time.sleep(3)
                    return
                    
        if self.is_shifted.value == 0:
            deliverPellet = False
            if self.pellet_status == 1:
                if objDetected:
                    self.pellet_status = 2
                    self.pellet_timing = time.time()
                    self.failCt = 0
                elif (time.time()-self.pellet_timing) > 10:
                    self.failCt+=1
                    if self.failCt > 3:
                        self.failCt = 0
                        beepList = [1,1,1]
                        self.auto_pellet.SetValue(0)
                        self.pellet_timing = time.time()
                        self.pellet_status = 2
                        for d in beepList: 
                            duration = d  # seconds
                            freq = 940  # Hz
                            os.system('play -nq -t alsa synth {} sine {}'.format(duration, freq))
                            time.sleep(d)
                    else:
                        deliverPellet = True
                        
            elif self.pellet_status == 2:
                if not objDetected:
                    if (time.time()-self.pellet_timing) > 3:
                        if roi < 75:
                            deliverPellet = True
                else:
                    self.pellet_timing = time.time()
            
            if deliverPellet:
                print('delivery attempt')
                self.com.value = 1
                # while self.com.value > 0:
                #     time.sleep(0.01)
                self.pellet_status = 1
                self.pellet_timing = time.time()
            
    def vidPlayer(self, event):
        if self.camaq.value == 2:
            return
        for ndx, im in enumerate(self.im):
            if self.frmGrab[ndx].value == 1:
                self.frameBuff[ndx][0:] = np.frombuffer(self.array4feed[ndx].get_obj(), self.dtype, self.size)
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.aqH[ndx], self.aqW[ndx]])
                self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx]] = frame
                im.set_data(self.frame[ndx])
                if self.auto_pellet.GetValue():
                    if not self.pellet_x == 0:
                        if not self.roi[0] == 0:
                            if self.pelletAxes == self.axes[ndx]:
                                span = 6
                                cpt = np.asarray([self.pellet_x-span,span*2+1,self.pellet_y-span,span*2+1], int)
                                pim = self.frame[ndx][cpt[2]:cpt[2]+cpt[3],cpt[0]:cpt[0]+cpt[1]]
                                cpt = self.roi
                                roi = self.frame[ndx][cpt[2]:cpt[2]+cpt[3],cpt[0]:cpt[0]+cpt[1]]
                                self.pelletHandler(np.mean(pim[:]),np.mean(roi[:]))
                                
                self.frmGrab[ndx].value = 0
                
        self.figure.canvas.draw()
        
        
    def autoCapture(self, event):
        self.sliderTabs+=self.sliderRate
        msg = '-'
        if (self.sliderTabs > self.slider.GetMax()) and not (msg == 'fail'):
            self.rec.SetValue(False)
            self.recordCam(event)
            self.slider.SetValue(0)
        else:
            self.slider.SetValue(round(self.sliderTabs))
            self.vidPlayer(event)
        
    def recordCam(self, event):
        if self.rec.GetValue():
            
            liveRate = 250
            self.Bind(wx.EVT_TIMER, self.autoCapture, self.recTimer)
            if int(self.minRec.GetValue()) == 0:
                return
            totTime = int(self.minRec.GetValue())*60
            self.proto_str = self.protocol.GetStringSelection()
            for ndx, s in enumerate(self.camStrList):
                camID = str(self.user_cfg[s]['serial'])
                self.camq[camID].put('recordPrep')
                if not self.proto_str == 'Protocol':
                    proto_name = os.path.join(self.protoDir, self.proto_str + '.yaml')
                    self.camq[camID].put(proto_name)
                    msg = self.camq_p2read[camID].get()
                    if msg < 0:
                        print('Protocol loading error')
                        self.rec.SetValue(False)
                        return
                else:
                    self.camq[camID].put('none')
                    self.camq_p2read[camID].get()
            
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
            maxSess = 0;
            for p in prev_expt_list:
                sessNum = int(p[-3:])
                if sessNum > maxSess:
                    maxSess = sessNum
            comp_dir = os.path.join(self.user_cfg['compressed_video_dir'], date_string, self.user_cfg['unitRef'])
            if os.path.exists(comp_dir):
                prev_expt_list = [name for name in os.listdir(comp_dir) if name.startswith('session')]
                for p in prev_expt_list:
                    sessNum = int(p[-3:])
                    if sessNum > maxSess:
                        maxSess = sessNum
            file_count = maxSess+1
            sess_string = '%s%03d' % ('session', file_count)
            self.sess_dir = os.path.join(base_dir, sess_string)
            if not os.path.exists(self.sess_dir):
                os.makedirs(self.sess_dir)
            self.meta,ruamelFile = clara.metadata_template()
            
            self.meta['duration (s)']=totTime
            self.meta['ID']=self.expt_id.GetValue()
            self.meta['placeholderA']='info'
            self.meta['placeholderB']='info'
            self.meta['Designer']='name'
            self.meta['Stim']=self.proto_str
            self.meta['StartTime']=datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            self.meta['Collection']='info'
            meta_name = '%s_%s_%s_metadata.yaml' % (date_string, self.user_cfg['unitRef'], sess_string)
            self.metapath = os.path.join(self.sess_dir,meta_name)
            usrdatadir = os.path.dirname(os.path.realpath(__file__))
            _, user = os.path.split(Path.home())
            configname = os.path.join(usrdatadir, '%s_userdata.yaml' % user)
            copyname = '%s_%s_%s_userdata_copy.yaml' % (date_string, self.user_cfg['unitRef'], sess_string)
            shutil.copyfile(configname,os.path.join(self.sess_dir,copyname))
            if not self.proto_str == 'Protocol':
                copyname = '%s_%s_%s_protocol.yaml' % (date_string, self.user_cfg['unitRef'], sess_string)
                protopath = Path(proto_name)
                shutil.copyfile(protopath,os.path.join(self.sess_dir,copyname))
            
            for ndx, s in enumerate(self.camStrList):
                camID = str(self.user_cfg[s]['serial'])
                name_base = '%s_%s_%s_%s' % (date_string, self.user_cfg['unitRef'], sess_string, self.user_cfg[s]['nickname'])
                path_base = os.path.join(self.sess_dir,name_base)
                self.camq[camID].put(path_base)
                self.camq_p2read[camID].get()
            
               
            for h in self.disable4cam:
                h.Enable(False)
            
            self.shift_timing = time.time()
            if not self.recTimer.IsRunning():
                if self.auto_pellet.GetValue():
                    if not self.pellet_x == 0:
                        if not self.roi[0] == 0:
                            self.pellet_timing = time.time()
                            self.pellet_status = 2
                
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
            
            for h in self.disable4cam:
                h.Enable(True)
    
    def initThreads(self):
        self.camq = dict()
        self.camq_p2read = dict()
        self.cam = list()
        for ndx, camID in enumerate(self.camIDlsit):
            self.camq[camID] = Queue()
            self.camq_p2read[camID] = Queue()
            self.cam.append(spin.multiCam_DLC_Cam(self.camq[camID], self.camq_p2read[camID],
                                               camID, self.camIDlsit,
                                               self.frmDims, self.camaq,
                                               self.frmaq, self.array4feed[ndx], self.frmGrab[ndx],
                                               self.com))
            self.cam[ndx].start()
            
        for m in self.mlist:
            self.camq[m].put('InitM')
            self.camq_p2read[m].get()
        for s in self.slist:
            self.camq[s].put('InitS')
            self.camq_p2read[s].get()
        
        self.ardq = Queue()
        self.ardq_p2read = Queue()
        self.ard = arduino.arduinoCtrl(self.ardq, self.ardq_p2read, self.frmaq, self.com, self.is_shifted)
        self.ard.start()
        self.ardq_p2read.get()
        
    def deinitThreads(self):
        for n, camID in enumerate(self.camIDlsit):
            self.camq[camID].put('Release')
            self.camq_p2read[camID].get()
            self.camq[camID].close()
            self.camq_p2read[camID].close()
            self.cam[n].terminate()
        if self.com.value >= 0:
            self.ardq.put('Release')
            self.ardq_p2read.get()
            self.ardq.close()
            self.ardq_p2read.close()
            self.ard.terminate()
            
    def startAq(self):
        for m in self.mlist:
            self.camq[m].put('Start')
        for s in self.slist:
            self.camq[s].put('Start')
        for m in self.mlist:
            self.camq[m].put('TrigOff')
        
    def stopAq(self):
        
        self.camaq.value = 0
        for s in self.slist:
            self.camq[s].put('Stop')
            self.camq_p2read[s].get()
        for m in self.mlist:
            self.camq[m].put('Stop')
            self.camq_p2read[m].get()
        
    def updateSettings(self, event):
        self.user_cfg = clara.read_config()
        self.aqW = list()
        self.aqH = list()
        self.recSet = list()
        for n, camID in enumerate(self.camIDlsit):
            try:
                self.camq[camID].put('updateSettings')
                self.camq_p2read[camID].get(timeout=1)
                if self.auto_stim.GetValue():
                    self.camq[camID].put('roi')
                elif self.crop.GetValue():
                    self.camq[camID].put('crop')
                else:
                    self.camq[camID].put('full')
            
                self.recSet.append(self.camq_p2read[camID].get(timeout=4))
                aqW = self.camq_p2read[camID].get(timeout=1)
                self.aqW.append(int(aqW))
                aqH = self.camq_p2read[camID].get(timeout=1)
                self.aqH.append(int(aqH))
                
            except:
                print('\nTrying to fix.  Please wait...\n')
                self.deinitThreads()
                self.camReset(event)
                self.initThreads()
                self.camq[camID].put('updateSettings')
                self.camq_p2read[camID].get()
                if self.auto_stim.GetValue():
                    self.camq[camID].put('roi')
                elif self.crop.GetValue():
                    self.camq[camID].put('crop')
                else:
                    self.camq[camID].put('full')
            
                self.recSet.append(self.camq_p2read[camID].get())
                aqW = self.camq_p2read[camID].get()
                self.aqW.append(int(aqW))
                aqH = self.camq_p2read[camID].get()
                self.aqH.append(int(aqH))
                
                
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
                if self.auto_stim.GetValue() and self.stimAxes == self.axes[ndx]:
                    self.h.append(self.stimroi[3])
                    self.w.append(self.stimroi[1])
                    self.y1.append(self.stimroi[2])
                    self.x1.append(self.stimroi[0])
                    self.set_stim.Enable(False)
                    self.set_crop.Enable(False)
                elif self.crop.GetValue():
                    self.h.append(self.croproi[ndx][3])
                    self.w.append(self.croproi[ndx][1])
                    self.y1.append(self.croproi[ndx][2])
                    self.x1.append(self.croproi[ndx][0])
                    self.set_crop.Enable(False)
                    self.set_stim.Enable(True)
                else:
                    self.h.append(self.frmDims[1])
                    self.w.append(self.frmDims[3])
                    self.y1.append(self.frmDims[0])
                    self.x1.append(self.frmDims[2])
                    self.set_crop.Enable(True)
                    self.set_stim.Enable(True)
                
                self.dispSize.append(self.aqH[ndx]*self.aqW[ndx])
                self.y2.append(self.y1[ndx]+self.aqH[ndx])
                self.x2.append(self.x1[ndx]+self.aqW[ndx])
                
                frame = self.frameBuff[ndx][0:self.dispSize[ndx]].reshape([self.aqH[ndx], self.aqW[ndx]])
                self.frame[ndx][self.y1[ndx]:self.y2[ndx],self.x1[ndx]:self.x2[ndx]] = frame
                im.set_data(self.frame[ndx])
                
                    
                if not self.croproi[ndx][0] == 0:
                    self.croprec[ndx].set_alpha(0.6)

                if not self.pellet_x == 0:
                    if not self.roi[0] == 0:
                        if self.pelletAxes == self.axes[ndx]:
                            self.pLoc[ndx].set_alpha(0.6)
                            self.roirec[ndx].set_alpha(0.6)

                if not self.stimroi[0] == 0:
                    if self.stimAxes == self.axes[ndx]:
                        self.stimrec[ndx].set_alpha(0.6)
            
            self.init.SetLabel('Release')
            self.crop.Enable(False)
            self.auto_stim.Enable(False)
            
            for h in self.onWhenCamEnabled:
                h.Enable(True)
            
            if not self.com.value < 0:
                self.com.value = 8
                while self.com.value > 0:
                    time.sleep(0.01)
                self.com.value = 9
                while self.com.value > 0:
                    time.sleep(0.01)
                self.com.value = 10
                while self.com.value > 0:
                    time.sleep(0.01)
                self.com.value = 11
                while self.com.value > 0:
                    time.sleep(0.01)
                self.com.value = 0
                
                for h in self.serHlist:
                    h.Enable(True)
            self.Enable(True)
            self.figure.canvas.draw()
        else:
            if self.play.GetValue():
                self.play.SetValue(False)
                self.liveFeed(event)
            if self.rec.GetValue():
                self.rec.SetValue(False)
                self.recordCam(event)
            self.init.SetLabel('Enable')
            for h in self.serHlist:
                h.Enable(False)
            for ndx, im in enumerate(self.im):
                self.frame[ndx] = np.zeros(self.shape, dtype='ubyte')
                im.set_data(self.frame[ndx])
                self.croprec[ndx].set_alpha(0)
                self.pLoc[ndx].set_alpha(0)
                self.roirec[ndx].set_alpha(0)
                self.stimrec[ndx].set_alpha(0)
            self.figure.canvas.draw()
            
            self.crop.Enable(True)
            self.auto_stim.Enable(True)
            self.set_crop.Enable(False)
            self.set_stim.Enable(False)
            for h in self.onWhenCamEnabled:
                h.Enable(False)
            
            self.deinitThreads()
        
    def quitButton(self, event):
        """
        Quits the GUI
        """
        print('Close event called')
        if self.play.GetValue():
            self.play.SetValue(False)
            self.liveFeed(event)
        if self.rec.GetValue():
            self.rec.SetValue(False)
            self.recordCam(event)
        if self.init.GetValue():
            self.init.SetValue(False)
            self.initCams(event)
        
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
        
        self.statusbar.SetStatusText("")
        self.Destroy()
    
def show():
    app = wx.App()
    MainFrame(None).Show()
    app.MainLoop()

if __name__ == '__main__':
    
    show()
