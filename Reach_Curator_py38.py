"""
CLARA toolbox
https://github.com/wryanw/CLARA
W Williamson, wallace.williamson@ucdenver.edu

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
from scipy.signal import savgol_coeffs, butter, filtfilt
import yaml




# ###########################################################################
# Class for GUI MainFrame
# ###########################################################################
class ImagePanel(wx.Panel):

    def __init__(self, parent, gui_size, axesCt, **kwargs):
        h=np.amax(gui_size)/4
        w=np.amax(gui_size)/4
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER,size=(h,w))

        self.figure = Figure()
        self.axes = list()
        for a in range(axesCt):
            if gui_size[0] > gui_size[1]:
                self.axes.append(self.figure.add_subplot(1, axesCt+2, a+1, frameon=False))
                self.axes[a].set_position([a*1/axesCt+0.005,0.15,1/axesCt-0.01,1-0.26])
            else:
                self.axes.append(self.figure.add_subplot(axesCt, 1, a+1, frameon=False))
                self.axes[a].set_position([0.005,a*1/axesCt+0.005,1-0.01,1/axesCt-0.01])
            
            self.axes[a].xaxis.set_visible(False)
            self.axes[a].yaxis.set_visible(False)
        
        self.axC = self.figure.add_subplot(1, axesCt+2, a+2, frameon=True)
        self.axC.set_position([0.005,0.005,0.99,0.15])
        self.axC.xaxis.set_visible(False)
        self.axC.yaxis.set_visible(False)
        
        self.axD = self.figure.add_subplot(1, axesCt+2, a+3, frameon=True)
        self.axD.set_position([0.005,0.9,0.99,0.1])
        self.axD.xaxis.set_visible(False)
        self.axD.yaxis.set_visible(False)
        self.axD.set_ylim([0,30])
        self.axD.set_ylim([0,100])
        
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.SetSizer(self.sizer)
        self.Fit()
        
    def remewAxes(self):
        for a in self.axes:
            a.remove()
        axesCt = len(self.axes)
        self.axes = list()
        for a in range(axesCt):
            self.axes.append(self.figure.add_subplot(1, axesCt+2, a+1, frameon=False))
            self.axes[a].set_position([a*1/axesCt+0.005,0.15,1/axesCt-0.01,1-0.26])
            
            self.axes[a].xaxis.set_visible(False)
            self.axes[a].yaxis.set_visible(False)
        
        # self.axC.remove()
        self.axC = self.figure.add_subplot(1, axesCt+2, a+2, frameon=True)
        self.axC.set_position([0.005,0.005,0.99,0.15])
        self.axC.xaxis.set_visible(False)
        self.axC.yaxis.set_visible(False)
        # self.axD.remove()
        self.axD = self.figure.add_subplot(1, axesCt+2, a+3, frameon=True)
        self.axD.set_position([0.005,0.9,0.99,0.1])
        self.axD.xaxis.set_visible(False)
        self.axD.yaxis.set_visible(False)
        self.axD.set_ylim([0,30])
        self.axD.set_ylim([0,100])
        
    def getfigure(self):
        """
        Returns the figure, axes and canvas
        """
        return(self.figure,self.axes,self.canvas,self.axC,self.axD)
    
    def cmap_map(self, function, cmap):
        """ Applies function (which should operate on vectors of shape 3: [r, g, b]), on colormap cmap.
        This routine will break any discontinuous points in a colormap.
        """
        cdict = cmap._segmentdata
        step_dict = {}
        # Firt get the list of points where the segments start or end
        for key in ('red', 'green', 'blue'):
            step_dict[key] = list(map(lambda x: x[0], cdict[key]))
        step_list = sum(step_dict.values(), [])
        step_list = np.array(list(set(step_list)))
        # Then compute the LUT, and apply the function to the LUT
        reduced_cmap = lambda step : np.array(cmap(step)[0:3])
        old_LUT = np.array(list(map(reduced_cmap, step_list)))
        new_LUT = np.array(list(map(function, old_LUT)))
        # Now try to make a minimal segment definition of the new LUT
        cdict = {}
        for i, key in enumerate(['red','green','blue']):
            this_cdict = {}
            for j, step in enumerate(step_list):
                if step in step_dict[key]:
                    this_cdict[step] = new_LUT[j, i]
                elif new_LUT[j,i] != old_LUT[j, i]:
                    this_cdict[step] = new_LUT[j, i]
            colorvector = list(map(lambda x: x + (x[1], ), this_cdict.items()))
            colorvector.sort()
            cdict[key] = colorvector
    
        return mcolors.LinearSegmentedColormap('colormap',cdict,1024)
    
    def getColorIndices(self,img,bodyparts):
        """
        Returns the colormaps ticks and . The order of ticks labels is reversed.
        """
        norm = mcolors.Normalize(vmin=np.min(img), vmax=np.max(img))
        ticks = np.linspace(np.min(img),np.max(img),len(bodyparts))[::-1]
        return norm, ticks

class ScrollPanel(SP.ScrolledPanel):
    def __init__(self, parent):
        SP.ScrolledPanel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)
        self.SetupScrolling(scroll_x=True, scroll_y=False, scrollToTop=False, scrollIntoView=False)
        self.Layout()

    def on_focus(self,event):
        pass

    def addRadioButtons(self, choices, guiDim):
        """
        Adds radio buttons for each bodypart on the right panel
        """
        if guiDim == 0:
            style=wx.RA_SPECIFY_COLS
            self.choiceBox = wx.BoxSizer(wx.HORIZONTAL)
        else:
            style=wx.RA_SPECIFY_ROWS
            self.choiceBox = wx.BoxSizer(wx.VERTICAL)
        
        buttSpace = 5
        
        self.fieldradiobox = list()
        if isinstance(choices,list):
            choices.append(' ')
            self.fieldradiobox.append(wx.RadioBox(self,label='Select action category',
                                        style=style,choices=choices))
            self.fieldradiobox[0].SetSelection(len(choices)-1)
        else:
            categories = list()
            catkeys = choices.keys()
            for cat in catkeys:
                categories.append(cat)
            self.fieldradiobox.append(wx.RadioBox(self,label='Category',
                                        style=style,choices=categories))
            for cat in categories:
                parts = choices[cat]
                self.fieldradiobox.append(wx.RadioBox(self,label=cat + ' Part',
                                        style=style,choices=parts))
        for rad in self.fieldradiobox:
            self.choiceBox.Add(rad, 0, wx.ALL|wx.ALIGN_LEFT, buttSpace)
            rad.Enable(False)
                
        self.SetSizerAndFit(self.choiceBox)
        self.Layout()
        
        return self.fieldradiobox

    def replaceRadio(self):
        self.choiceBox.Clear(True)

class LabelsPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER)
        self.Layout()
    
    def on_focus(self,event):
        pass

    def addButtons(self, guiDim):
        """
        Adds radio buttons for each bodypart on the right panel
        """
        if guiDim == 0:
            self.labelBox = wx.BoxSizer(wx.HORIZONTAL)
        else:
            self.labelBox = wx.BoxSizer(wx.VERTICAL)
        
        buttSpace = 5
        
        self.place_event = wx.Button(self, size=(100, -1), id=wx.ID_ANY, label="Place Reach")
        self.labelBox.Add(self.place_event, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.place_event.Enable(False)
        
        self.remove_event = wx.Button(self, size=(100, -1), id=wx.ID_ANY, label="Remove Reach")
        self.labelBox.Add(self.remove_event, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.remove_event.Enable(False)
        
        self.bad_tracking = wx.Button(self, size=(100, -1), id=wx.ID_ANY, label="Bad Tracking")
        self.labelBox.Add(self.bad_tracking, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.bad_tracking.Enable(False)
        
        self.labelBox.AddStretchSpacer(1)
        
        text = wx.StaticText(self, label='Find:')
        self.labelBox.Add(text, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        
        self.fBox = wx.Choice(self, id=wx.ID_ANY, choices = ['Labeled Frame','Reach'])
        self.fBox.SetSelection(0)
        self.labelBox.Add(self.fBox, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.fBox.Enable(False)
        
        self.fPrev = wx.Button(self, size=(30, -1), id=wx.ID_ANY, label="<")
        self.labelBox.Add(self.fPrev, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.fPrev.Enable(False)
        self.fNext = wx.Button(self, size=(30, -1), id=wx.ID_ANY, label=">")
        self.labelBox.Add(self.fNext, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.fNext.Enable(False)
        
        self.SetSizerAndFit(self.labelBox)
        self.Layout()
        
        return(self.fBox,self.fPrev,self.fNext,self.place_event,self.bad_tracking,self.remove_event)

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
        self.gui_size = (800,2000)
        if screenW > screenH:
            self.gui_size = (2000,800)
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = 'CLARA DLC Video Explorer',
                            size = wx.Size(self.gui_size), pos = wx.DefaultPosition, style = wx.RESIZE_BORDER|wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
        self.statsusbar = self.CreateStatusBar()
        self.statsusbar.SetStatusText("")

        self.SetSizeHints(wx.Size(self.gui_size)) #  This sets the minimum size of the GUI. It can scale now!
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyPressed)
        
###################################################################################################################################################
# Spliting the frame into top and bottom panels. Bottom panels contains the widgets. The top panel is for showing images and plotting!
        self.guiDim = 0
        if screenH > screenW:
            self.guiDim = 1
        topSplitter = wx.SplitterWindow(self)
        vSplitterA = wx.SplitterWindow(topSplitter)
        vSplitter = wx.SplitterWindow(vSplitterA)
        self.image_panel = ImagePanel(vSplitterA,self.gui_size, 2)
        self.choice_panel = ScrollPanel(vSplitter)
        self.label_panel = LabelsPanel(vSplitter)
        self.widget_panel = WidgetPanel(topSplitter)
        if self.guiDim == 0:
            vSplitter.SplitVertically(self.choice_panel,self.label_panel, sashPosition=self.gui_size[0]*0.5)
            vSplitter.SetSashGravity(0.5)
            vSplitterA.SplitHorizontally(self.image_panel,vSplitter, sashPosition=self.gui_size[1]*0.5)
            vSplitterA.SetSashGravity(0.5)
            topSplitter.SplitVertically(vSplitterA, self.widget_panel,sashPosition=self.gui_size[0]*0.8)#0.9
            topSplitter.SetSashGravity(0.5)
        else:
            vSplitter.SplitVertically(self.image_panel,self.choice_panel, sashPosition=self.gui_size[0]*0.5)
            vSplitter.SetSashGravity(0.5)
            vSplitter.SplitVertically(self.image_panel,self.label_panel, sashPosition=self.gui_size[0]*0.5)
            vSplitter.SetSashGravity(0.5)
            topSplitter.SplitHorizontally(vSplitter, self.widget_panel,sashPosition=self.gui_size[1]*0.8)#0.9
        topSplitter.SetSashGravity(0.5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

###################################################################################################################################################
# Add Buttons to the WidgetPanel and bind them to their respective functions.
        
        self.labelselect = self.choice_panel.addRadioButtons(['none','success','reach failure','grasp failure','retrieval failure'],self.guiDim)
        self.fBox,self.fPrev,self.fNext,self.place_event,self.bad_tracking,self.remove_event = self.label_panel.addButtons(self.guiDim)
        self.fPrev.Bind(wx.EVT_BUTTON, self.jumpFrame)
        self.fNext.Bind(wx.EVT_BUTTON, self.jumpFrame)
        self.place_event.Bind(wx.EVT_BUTTON, self.placeEvent)
        self.bad_tracking.Bind(wx.EVT_BUTTON, self.badTracking)
        self.remove_event.Bind(wx.EVT_BUTTON, self.removeEvent)
        
        widgetSize = 7
        widgetsizer = wx.WrapSizer(orient=wx.HORIZONTAL)
        
        self.load_vids = wx.Button(self.widget_panel, size=(150, -1), id=wx.ID_ANY, label="Load Videos")
        widgetsizer.Add(self.load_vids, 1, wx.ALL, widgetSize)
        self.load_vids.Bind(wx.EVT_BUTTON, self.loadVids)
        self.load_vids.Enable(False)
        
        self.load_config = wx.Button(self.widget_panel, size=(150, -1), id=wx.ID_ANY, label="Load Config File")
        widgetsizer.Add(self.load_config, 1, wx.ALL, widgetSize)
        self.load_config.Bind(wx.EVT_BUTTON, self.loadConfig)
        widgetsizer.AddStretchSpacer(1)
        
        text = wx.StaticText(self.widget_panel, label='Curation file:')
        widgetsizer.Add(text, 0, wx.ALL, widgetSize)
        
        self.user_dir = os.path.join(str(Path.home()),'Documents','Curators')
        if not os.path.exists(self.user_dir):
            os.makedirs(self.user_dir)
        userlist = glob.glob(os.path.join(self.user_dir,'*.yaml'))
        userlist = [Path(i).stem for i in userlist]
        userlist.append('new curation')
        self.annosess_list = wx.Choice(self.widget_panel, size=(150, -1), id=wx.ID_ANY, choices=userlist)
        widgetsizer.Add(self.annosess_list, 1, wx.ALL, widgetSize)
        self.annosess_list.SetSelection(0)
        
        widgetsizer.AddStretchSpacer(1)
        
        self.show_tracking = wx.CheckBox(self.widget_panel, id=wx.ID_ANY,label = 'Load Labels')
        widgetsizer.Add(self.show_tracking, 0, wx.ALL, widgetSize)
        self.show_tracking.Bind(wx.EVT_CHECKBOX, self.loadAnnotations)
        
        self.grab_files = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Grab Files")
        widgetsizer.Add(self.grab_files, 1, wx.ALL, widgetSize)
        self.grab_files.Bind(wx.EVT_BUTTON, self.grabFiles)
        self.grab_files.Enable(False)
        
        self.discard_files = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Discard")
        widgetsizer.Add(self.discard_files, 1, wx.ALL, widgetSize)
        self.discard_files.Bind(wx.EVT_BUTTON, self.discardFiles)
        
        
#        self.use_syn = wx.CheckBox(self.widget_panel, id=wx.ID_ANY, label="Access Synology")
#        widgetsizer.Add(self.use_syn, 1, wx.ALL, widgetSize)

        self.slider = wx.Slider(self.widget_panel, -1, 0, 0, 100,size=(300, -1), style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        widgetsizer.Add(self.slider, 2, wx.ALL, widgetSize)
        self.slider.Bind(wx.EVT_SLIDER, self.OnSliderScroll)
        self.slider.Enable(False)
        
        self.play = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Play")
        widgetsizer.Add(self.play , 1, wx.ALL, widgetSize*1.25)
        self.play.Bind(wx.EVT_TOGGLEBUTTON, self.fwrdPlay)
        self.play.Enable(False)

        widgetsizer.AddStretchSpacer(1)
        
        self.grab_frame = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Save Frame")
        widgetsizer.Add(self.grab_frame, 1, wx.ALL , widgetSize)
        self.grab_frame.Bind(wx.EVT_BUTTON, self.grabFrame)
        self.grab_frame.Enable(False)
        
        widgetsizer.AddStretchSpacer(1)
        
        self.save = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Make Demo")
        widgetsizer.Add(self.save , 1, wx.ALL , widgetSize)
        self.save.Bind(wx.EVT_BUTTON, self.makeDemoVid)
        self.save.Enable(False)

#        Making radio selection for vid speed
        self.speedOps = [-10,-5,-1,1,5,10]
        viewopts = ['-900','-200','-20 ','20', '200','900']
        choices = [l for l in viewopts]
        self.speedbox = wx.RadioBox(self.widget_panel,label='Playback speed (fps)', majorDimension=1, style=wx.RA_SPECIFY_ROWS,choices=choices)
        widgetsizer.Add(self.speedbox, 1, wx.ALL, widgetSize)
        self.speedbox.Bind(wx.EVT_RADIOBOX, self.playSpeed)
        self.speedbox.SetSelection(3)
        self.speedbox.Enable(False)
        
        self.start_frames_sizer = wx.BoxSizer(wx.VERTICAL)
        self.end_frames_sizer = wx.BoxSizer(wx.VERTICAL)

        self.startFrame = wx.SpinCtrl(self.widget_panel, value='0', size=(150, -1))#,style=wx.SP_VERTICAL)
        self.startFrame.Enable(False)
        self.start_frames_sizer.Add(self.startFrame, 1, wx.EXPAND|wx.ALIGN_LEFT, widgetSize)
        self.startFrame.Bind(wx.EVT_SPINCTRL, self.updateSlider)
        start_text = wx.StaticText(self.widget_panel, label='Start Frame Index')
        self.start_frames_sizer.Add(start_text, 1, wx.EXPAND|wx.ALIGN_LEFT, widgetSize)
         
        self.endFrame = wx.SpinCtrl(self.widget_panel, value='1', size=(150, -1))#, min=1, max=120)
        self.endFrame.Enable(False)
        self.end_frames_sizer.Add(self.endFrame, 1, wx.EXPAND|wx.ALIGN_LEFT, widgetSize)
        self.endFrame.Bind(wx.EVT_SPINCTRL, self.updateSlider)
        end_text = wx.StaticText(self.widget_panel, label='Frames Remaining')
        self.end_frames_sizer.Add(end_text, 1, wx.EXPAND|wx.ALIGN_LEFT, widgetSize)
        
        widgetsizer.Add(self.start_frames_sizer, 1, wx.ALL, widgetSize)
        widgetsizer.AddStretchSpacer(1)
        widgetsizer.Add(self.end_frames_sizer, 1, wx.ALL, widgetSize)
        
        widgetsizer.AddStretchSpacer(1)
        
        
        self.quit = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Quit")
        widgetsizer.Add(self.quit , 1, wx.ALL, widgetSize)
        self.quit.Bind(wx.EVT_BUTTON, self.quitButton)
        self.Bind(wx.EVT_CLOSE, self.quitButton)
        
        widgetsizer.Add(self, 1, wx.EXPAND)
        self.widget_panel.SetSizer(widgetsizer)
        widgetsizer.Fit(self.widget_panel)
        self.widget_panel.Layout()
        
        self.timer = wx.Timer(self, wx.ID_ANY)
        self.videos = list()
        self.shuffle = 1
        self.trainingsetindex = 0
        self.currAxis = 0
        self.vid = list()
        self.videoList = list()
        self.move_event = False
        self.scroll_frm = False
        self.clicked_in_axes = False
        self.click_x = 0
        self.adv_single = False
        self.temp_folder = os.path.join(self.user_dir,'temp_files')
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        
        self.figure,self.axes,self.canvas,self.axC,self.axD = self.image_panel.getfigure()
        self.canvas.mpl_connect('button_release_event', self.onButtonRelease)
        self.canvas.mpl_connect('button_press_event', self.onClick)
        self.canvas.mpl_connect('motion_notify_event', self.onMove)
        
            
    def config_template(self):
        """
        Creates a template for config.yaml file. This specific order is preserved while saving as yaml file.
        """
        yaml_str = """\
# Curation settings
    user name:
    session list:
    behaviors (add/remove/change):
    events (only add):
    results directory:
    raw data directory:
    \n
# DLC settings used
    frontCrop:
    sideCrop:
    topCrop:
    bodyparts:
    \n
    """
        ruamelFile = ruamel.yaml.YAML()
        cfg_file = ruamelFile.load(yaml_str)
        return cfg_file, ruamelFile
    
    def grabFiles(self, event):
        for s in self.sesslist:
            fpts = s.split('_')
            fp = os.path.join(self.rawdatadir,fpts[0],fpts[1],fpts[2])
            all_files = glob.glob(os.path.join(fp, '*'))
            print(s)
            dest_dir = os.path.join(self.temp_folder,fpts[0],fpts[1],fpts[2])
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            for f in all_files:
                mname = PurePath(f).name
                mdest = os.path.join(dest_dir,mname)
                if not os.path.isfile(mdest):
                    shutil.copyfile(f,mdest)
                else:
                    try:
                        szA = os.path.getsize(mdest)
                        szB = os.path.getsize(f)
                        if not szA == szB:
                            shutil.copyfile(f,mdest)
                    except:
                        shutil.copyfile(f,mdest)
        print('done')
        
    def discardFiles(self, event):
        date_list = [name for name in os.listdir(self.temp_folder)]
        for f in date_list:
            date_dir = os.path.join(self.temp_folder, f)
            unit_list = [name for name in os.listdir(date_dir)]
            for u in unit_list:
                unit_dir = os.path.join(date_dir,u)
                sess_list = [name for name in os.listdir(unit_dir)]
                for s in sess_list:
                    sess_dir = os.path.join(unit_dir,s)
                    all_files = os.path.join(sess_dir, '*')
                    for a in all_files:
                        os.remove(a)
        for f in date_list:
            date_dir = os.path.join(self.temp_folder, f)
            unit_list = [name for name in os.listdir(date_dir)]
            for u in unit_list:
                sess_list = [name for name in os.listdir(unit_dir)]
                for s in sess_list:
                    sess_dir = os.path.join(unit_dir,s)
                    os.rmdir(sess_dir)
                    
        for f in date_list:
            date_dir = os.path.join(self.temp_folder, f)
            unit_list = [name for name in os.listdir(date_dir)]
            for u in unit_list:
                unit_dir = os.path.join(date_dir,u)
                os.rmdir(unit_dir)
        for f in date_list:
            date_dir = os.path.join(self.temp_folder, f)
            os.rmdir(date_dir)
        
    def read_config(self):
        """
        Reads structured config file

        """
        cfg = 'none'
        usrdatadir = os.path.dirname(os.path.realpath(__file__))
        configname = os.path.join(usrdatadir, 'userdata.yaml')
        ruamelFile = ruamel.yaml.YAML()
        path = Path(configname)
        with open(path, 'r') as f:
            cfg = ruamelFile.load(f)
            
        return(cfg)
    
    def loadConfig(self, event):
        self.load_vids.Enable(False)
        self.grab_files.Enable(False)
        self.experimenter = self.annosess_list.GetStringSelection()
        cfgpath = os.path.join(self.user_dir, '%s.yaml' % self.experimenter)
        ruamelFile = ruamel.yaml.YAML()
        path = Path(cfgpath)
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.cfg = ruamelFile.load(f)
            if self.cfg['results directory'] == 'path\for\saving\anotations':
                print('Change the yaml file fields!')
            else:
                self.annodir = self.cfg['results directory']
                if not os.path.exists(os.path.split(self.annodir)[0]):
                    print('Parent directory not found')
                else:
                    if not os.path.exists(self.annodir):
                        os.makedirs(self.annodir)
                    self.annocat = self.cfg['behaviors (add/remove/change)']
                    self.events = self.cfg['events (only add)']
                    self.sesslist = self.cfg['session list']
                    self.rawdatadir = self.cfg['raw data directory']
                    for s in self.sesslist:
                        fpts = s.split('_')
                        fp = os.path.join(self.rawdatadir,fpts[0],fpts[1],fpts[2])
                        if not os.path.exists(fp):
                            print('Raw data directory not found')
                            print(fp)
                            return
                    self.load_vids.Enable(True)
                    self.grab_files.Enable(True)
                    cppos = self.choice_panel.GetPosition()
                    cprect = self.choice_panel.GetRect()
                    cpsize = self.choice_panel.GetSize()
                    self.choice_panel.replaceRadio()
                    self.labelselect = self.choice_panel.addRadioButtons(self.annocat,self.guiDim)
                    self.choice_panel.SetPosition(cppos)
                    self.choice_panel.SetRect(cprect)
                    self.choice_panel.SetSize(cpsize)
                    for rad in self.labelselect:
                        rad.Bind(wx.EVT_RADIOBOX, self.resetFocus)
                    
        else:
            self.canvas.mpl_disconnect(self.onClick)
            dlgP = wx.TextEntryDialog(self, 'Enter curation name')
            result = dlgP.ShowModal()
            dlgP.Destroy()
            self.canvas.mpl_connect('button_press_event', self.onClick)
            self.move_event = False
            self.scroll_frm = False
            if result == wx.ID_OK:
                self.experimenter = dlgP.GetValue()
            
            self.cfg,ruamelFile = self.config_template()
            self.cfg['user name'] = 'your name'
            self.cfg['session list'] = ['date_unit_session','date_unit_session']
            self.cfg['behaviors (add/remove/change)'] = ['grabbed', 'dropped', 'stalled', 'missed', 'none']
            self.cfg['events (only add)'] = ['reachInit','reachMax','reachEnd','stim']
            resultdir = os.path.join(self.user_dir,self.experimenter)
            if not os.path.exists(resultdir):
                os.makedirs(resultdir)
            self.cfg['results directory'] = resultdir
            self.cfg['raw data directory'] = r'//synology/WHSynology/BIOElectricsLab/RAW_DATA/AutomatedBehavior'
            self.cfg['frontCrop']=[115, 200, 70, 200]
            self.cfg['sideCrop']=[160, 200, 70, 200]
            self.cfg['topCrop']=[160, 200, 50, 200]
            bpset = {'Hand':['Flat','Spread','Grab'],
                     'Pellet':['Free','InHand'],
                     'Other':['Tongue','Mouth']}
            self.cfg['bodyparts']=bpset
            self.write_config()
            wx.MessageBox('Success! ...now, change the yaml file fields.', 'Info',
                          wx.OK | wx.ICON_INFORMATION)
    
    def write_config(self):
        cfgpath = os.path.join(self.user_dir, '%s.yaml' % self.experimenter)
        with open(cfgpath, 'w') as cf:
            ruamelFile = ruamel.yaml.YAML()
            cfg_file,ruamelFile = self.config_template()
            for key in self.cfg.keys():
                cfg_file[key]=self.cfg[key]
            
            ruamelFile.dump(cfg_file, cf)
        
        userlist = glob.glob(os.path.join(self.user_dir,'*.yaml'))
        userlist = [Path(i).stem for i in userlist]
        userlist.append('new curation')
        self.annosess_list.SetItems(userlist)
        self.annosess_list.SetStringSelection(self.experimenter)


    def OnKeyPressed(self, event):
        
#        print(event.GetKeyCode())
#        print(wx.WXK_RETURN)
        
        if self.play.IsEnabled() == True:
            if event.GetKeyCode() == wx.WXK_UP:
                if self.play.GetValue() == True:
                    self.play.SetValue(False)
                    self.fwrdPlay(event)
                self.slider.SetValue(self.slider.GetValue()+1)
                self.OnSliderScroll(event)
            elif event.GetKeyCode() == wx.WXK_DOWN:
                if self.play.GetValue() == True:
                    self.play.SetValue(False)
                    self.fwrdPlay(event)
                self.slider.SetValue(self.slider.GetValue()-1)
                self.OnSliderScroll(event)
            elif event.GetKeyCode() == wx.WXK_LEFT:
                if self.speedbox.GetSelection() > 0:
                    self.speedbox.SetSelection(self.speedbox.GetSelection()-1)
                    self.playSpeed(event)
            elif event.GetKeyCode() == wx.WXK_RIGHT:
                if self.speedbox.GetSelection() < (self.speedbox.GetCount()-1):
                    self.speedbox.SetSelection(self.speedbox.GetSelection()+1)
                    self.playSpeed(event)
            elif event.GetKeyCode() == wx.WXK_SPACE:
                if self.play.GetValue() == True:
                    self.play.SetValue(False)
                else:   
                    self.play.SetValue(True)
                self.fwrdPlay(event)
            elif event.GetKeyCode() == wx.WXK_RETURN or event.GetKeyCode() == wx.WXK_NUMPAD_ENTER:
                self.resetFocus(event)
            else:
                event.Skip()
        else:
            event.Skip()

    def fwrdPlay(self, event):
        if self.play.GetValue() == True:
            if not self.timer.IsRunning():
                self.timer.Start(50)
            self.play.SetLabel('Stop')
            if self.playSkip == 1:
                self.adv_single = True
        else:
            if self.timer.IsRunning():
                self.timer.Stop()
            self.play.SetLabel('Play')
        self.adv_single = False
        self.figure.canvas.flush_events()
        
    def playSpeed(self, event):
        wasRunning = False
        if self.timer.IsRunning():
            wasRunning = True
            self.timer.Stop()
        self.playSkip = self.speedOps[self.speedbox.GetSelection()]
        if self.playSkip != 1:
            self.adv_single = False
        self.slider.SetPageSize(pow(5,(self.speedbox.GetSelection()-1)))
        self.play.SetFocus()
        if wasRunning:
            self.timer.Start(50)
        
    def loadVids(self, event):
        if self.show_tracking.GetValue():
            self.show_tracking.SetValue(False)
            self.loadAnnotations(None)
        if len(self.vid) > 0:
            self.image_panel.remewAxes()
            self.figure,self.axes,self.canvas,self.axC,self.axD = self.image_panel.getfigure()
            for vid in self.vid:
                vid.release()
        
#        for hax in self.axes:
#            hax.clear()
            
#            for artist in hax.lines + plt.gca().collections:
#                artist.remove()
        
        
        
        self.figure.canvas.draw()
        self.axbackground = list()
        for a in self.axes:
            a.set_animated(True)
            self.axbackground.append(self.figure.canvas.copy_from_bbox(a.bbox))
        self.axDbackground = self.figure.canvas.copy_from_bbox(self.axD.bbox)
        
        self.canvas.mpl_disconnect(self.onClick)
        dlg = wx.SingleChoiceDialog(self, "Select session",'The Caption',self.sesslist,wx.CHOICEDLG_STYLE)
        result = dlg.ShowModal()
        self.canvas.mpl_connect('button_press_event', self.onClick)
        dlg.Destroy()
        self.move_event = False
        self.scroll_frm = False
        if result == wx.ID_OK:
            self.sessStr = dlg.GetStringSelection()
        else:
            return
        fpts = self.sessStr.split('_')
        
        self.videoSrc = os.path.join(self.temp_folder,fpts[0],fpts[1],fpts[2])
        avi_list = os.path.join(self.videoSrc, '*_264.mp4')
        self.videoList = glob.glob(avi_list)
        if len(self.videoList) != 2:
            self.videoSrc = os.path.join(self.rawdatadir,fpts[0],fpts[1],fpts[2])
            avi_list = os.path.join(self.videoSrc, '*_264.mp4')
            self.videoList = glob.glob(avi_list)
            if len(self.videoList) != 2:
                print('Not enough videos found!')
                return
        self.currFrame = 0
        
        # self.bodyparts = self.cfg['bodyparts']
        # if isinstance(self.bodyparts,list):
        #     parts = self.bodyparts
        # else:
        #     parts = list()
        #     self.categories = list()
        #     for cat in self.bodyparts.keys():
        #         self.categories.append(cat)
        #     for key in self.categories:
        #         for ptname in self.bodyparts[key]:
        #             parts.append(ptname)
        # self.bodyparts = parts
        self.bodyparts = ['Hand', 'Pellet']
        self.vid = list()
        self.im = list()
        
        
        self.videos = list()
        
        self.user_cfg = self.read_config()
        key_list = list()
        for cat in self.user_cfg.keys():
            key_list.append(cat)
        videoOrder = list()
        for key in key_list:
            if 'cam' in key:
                videoOrder.append(self.user_cfg[key]['nickname'])
        for key in videoOrder:
            for video in self.videoList:
                if key in video:
                    self.videos.append(video)
                    break
        
        # self.videos = list()
        
        # videoOrder = ['side','front','top']
        # for key in videoOrder:
        #     for video in self.videoList:
        #         if key in video:
        #             self.videos.append(video)
        self.frameList = list()
        self.cropPts = list()
        self.numberFrmList = list()
        self.colormap = plt.get_cmap('jet')
        plt.show(block=False)
        self.colormap = self.colormap.reversed()
        self.colormapT = self.image_panel.cmap_map(lambda x: x*0.75, self.colormap)
        self.markerSize = 4
        self.alpha = 0.6
        
        self.act_sel = 3
        self.sys_timer = [0,0,0]
        
        self.im = list()
        self.im = list()
        self.circle = list()
        self.croprec = list()
        self.pLoc = list()
        self.camt = list()
#        with open('objs.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
#            pickle.dump([self.videos,self.sessStr,videoOrder], f)
#        return
        self.tmstpList = list()
        maxfrmlist = list()
        for vndx, video in enumerate(self.videos):
            
            video_source = Path(video).resolve()
            self.vid.append(cv2.VideoCapture(str(video_source)))
            self.vid[vndx].set(1,self.currFrame)
            ret, frame = self.vid[vndx].read()
            if 'unit00' in video:
                cpt = self.cfg[videoOrder[vndx]+'Crop']
            else:
                cpt = [0, 360, 0, 270]
            self.cropPts.append(cpt)
            self.im.append(self.axes[vndx].imshow(frame))
            self.frameList.append(frame)
            self.numberFrames = int(self.vid[vndx].get(cv2.CAP_PROP_FRAME_COUNT))
            print(self.numberFrames)
            self.numberFrmList.append(self.numberFrames)
            
            fpts = self.sessStr.split('_')
            videoSrc, vidName = os.path.split(video)
            tfile = os.path.join(videoSrc, self.sessStr+'_'+videoOrder[vndx]+'_timestamps.txt')
            tmstp = list()
            if os.path.isfile(tfile):
                with open(tfile) as fp:
                    try:
                        for line in fp:
                            frmspace = int(line)
                            tmstp.append(frmspace)
                    except:
                        pass
            else:
                print('no timestamps found')
                self.videoList = list()
                return
            
            tmstp = np.asarray(tmstp)
            tmstp = np.cumsum(np.round(tmstp/np.percentile(tmstp,10)))
            tmstp = np.asarray(tmstp,dtype=int)
            self.tmstpList.append(tmstp)
            maxfrmlist.append(tmstp[-1])
            frmdiff = self.tmstpList[vndx][-1]-len(self.tmstpList[vndx])
            if frmdiff > 0:
                print('frames were dropped for:')
                print(vidName)
            


            self.norm,self.colorIndex = self.image_panel.getColorIndices(frame,self.bodyparts)
            
            self.points = [0,0,1.0]
            circleH = list()
            for bpndx, bp in enumerate(self.bodyparts):
                color = self.colormap(self.norm(self.colorIndex[bpndx]))
                circle = [patches.Circle((self.points[0], self.points[1]), radius=self.markerSize,
                                         linewidth=4, fc = color, alpha=0.0,edgecolor=[0,0,0])]
                circleH.append(self.axes[vndx].add_patch(circle[0]))
            self.circle.append(circleH)
  
            croprec = [patches.Rectangle((cpt[0]+1,cpt[2]+1), cpt[1]-3, cpt[3]-3, fill=False,
                                         ec = [0.25,0.75,0.25], linewidth=2, linestyle='-',alpha=self.alpha)]
            self.croprec.append(self.axes[vndx].add_patch(croprec[0]))
            circle = [patches.Circle((0, 0), radius=5, linewidth = 4, fc=[1,1,1], alpha=0.0)]
            self.pLoc.append(self.axes[vndx].add_patch(circle[0]))
            croprec = [patches.Rectangle((cpt[0]+cpt[1]/2+24,cpt[2]+1), 50, cpt[3]-3, fill=False,
                                         ec = [0.75,0.25,0.25], linewidth=2, linestyle='-',alpha=self.alpha)]
            
            
        self.blankframe = np.zeros(np.shape(frame))
        self.numberFrames = max(maxfrmlist)
        self.frmlistrefs = np.arange(0,self.numberFrames)
        self.frmReadNdx = list()
        for mf in self.tmstpList:
            frmrd = np.arange(0,self.numberFrames)
            frmrd[:] = -1
            frmndxlist = np.arange(0,len(mf))
            frmrd[mf-1] = frmndxlist
            self.frmReadNdx.append(frmrd)
        
        frame_rate = self.getFrameRate(self.videos[0])
        cutoff_freq = 50  # Hz
        nyquist_freq = 0.5 * frame_rate
        normalized_cutoff_freq = cutoff_freq / nyquist_freq
        filter_order = 5
        # Create Butterworth filter coefficients
        self.b, self.a = butter(filter_order, normalized_cutoff_freq, btype='low', analog=False, output='ba')

        self.coeffs = self.getCoeffs()    
        
        # ylim = self.axes[vndx].get_ylim()
        # self.axes[vndx].set_ylim([ylim[1],ylim[0]])
        self.numberFrames = np.amin(self.numberFrmList)
        self.strwidth = int(np.ceil(np.log10(self.numberFrames)))
        self.rchct = 0
        self.loadEvents()

        # Set the values of slider and range of frames
        self.slider.SetMax(self.numberFrames-1)
        self.endFrame.SetMax(self.numberFrames-1)
        self.startFrame.SetMax(self.numberFrames-1)
        self.endFrame.SetValue(self.numberFrames-1)
        self.startFrame.SetValue(0)
        
        self.grab_frame.Enable(True)
        self.save.Enable(True)
        self.play.Enable(True)
        self.slider.Enable(True)
        self.speedbox.Enable(True)
        self.startFrame.Enable(True)
        self.endFrame.Enable(True)
        self.videoList = list()
        self.Bind(wx.EVT_TIMER, self.vidPlayer, self.timer)
        self.widget_panel.Layout()
        self.slider.SetValue(self.currFrame)
        self.playSpeed(event)
        self.OnSliderScroll(event)
        self.show_tracking.SetValue(True)
        self.loadAnnotations(None)
        
    def getCoeffs(self):
        # Savitzky-Golay Smoothing filter parameters
        window_length = 9
        poly_order = 3
        # Obtain Savitzky-Golay filter coefficients
        coeffs = savgol_coeffs(window_length, poly_order)
        
        return coeffs
    
    def get_vid_name_base(self, video_path):
        vid_dir, vid_name = os.path.split(video_path)
        vid_name, vid_ext = os.path.splitext(vid_name)
        txtparts = vid_name.split('_')
        vid_name_base = txtparts[0] + '_' + txtparts[1] + '_' + txtparts[2]
        return vid_name_base, vid_dir
    
    def getFrameRate(self, video_path):
        frame_rate = None
        # Extract relevant information from video_path
        vid_name_base, vid_dir = self.get_vid_name_base(video_path)
        frame_rate_file = os.path.join(vid_dir, vid_name_base + '_userdata_copy.yaml')
        if os.path.isfile(frame_rate_file):
            # Read frame rate from userdata_copy.yaml
            with open(frame_rate_file, 'r') as file:
                yaml_content = file.read()
            if 'framerate' in yaml_content:
                frame_rate_string = yaml_content.split('framerate:')[1].split()[0]
                frame_rate = int(''.join(filter(str.isdigit, frame_rate_string)))
        return frame_rate
    
    def loadEvents(self):
        self.axC.remove()
        axesCt = len(self.axes)
        a = axesCt-1
        self.axC = self.figure.add_subplot(1, axesCt+2, a+2, frameon=True)
        self.axC.set_position([0.005,0.005,0.99,0.15])
        self.axC.xaxis.set_visible(False)
        self.axC.yaxis.set_visible(False)
        self.figure.canvas.draw()
        
        self.axCbackground = self.figure.canvas.copy_from_bbox(self.axC.bbox)
        self.place_event.Enable(False)
        for lab in self.labelselect:
            lab.Enable(False)
        self.bad_tracking.Enable(False)
        self.remove_event.Enable(False)
        
        self.fPrev.Enable(False)
        self.fNext.Enable(False)
        self.fBox.Enable(False)
        
        minorTicks = [i for i in range(0,self.numberFrames)]
        minorY = np.zeros(np.shape(minorTicks))+0.9
        self.tickHa = self.axC.plot(minorTicks,minorY,c=[0,0,0],linestyle='none',marker='|')
        self.tickHb = self.axC.plot(minorTicks,minorY,c=[0,0,0],linestyle='none',marker='|',
                      markevery=10,markersize=20)
        self.frmref = self.axC.plot([0,0],[0,1],c=[0,0,0])
        self.frmref[0].set_xdata([0,0])
        self.frmrefT = self.axC.text(0.1,0.65,'0')
        
        # annotag = os.path.split(os.path.split(self.temp_folder)[0])[0] + os.sep + 'ANALYZED_DATA' + os.sep + 'ReachEvents'
        # efile = self.sessStr+'_reachEvents.txt'
        # efile = annotag + os.sep + efile
        # if not os.path.isfile(efile):
        # annotag = os.path.split(self.rawdatadir)[0] + os.sep + 'ReachEvents'
        annotag = os.path.split(self.videos[0])[0]
        efile = self.sessStr+'_Ordered_Reach_Events.txt'
        efile = annotag + os.sep + efile
        self.eventListN = list()
        self.eventListF = list()
        self.eventClass = list()
        self.resultsPath = os.path.join(self.annodir,self.sessStr+'_'+self.experimenter+'.xlsx')
        print(self.resultsPath)
        
        rows = []
        data = np.zeros([len(rows),len(self.events)],dtype='uint32')
        self.annoTable = pd.DataFrame(data,rows,self.events)
        
        if os.path.isfile(self.resultsPath):
            self.annoTable = pd.read_excel(self.resultsPath)
            for ndx,nom in enumerate(np.asarray(self.annoTable.loc[:,'reachEnd'])):
                if nom > 0:
                    self.eventListF.append(nom)
                    # self.eventListN.append('reachEnd_'+self.annoTable.at[ndx,'end_category'])
                    self.eventListN.append('reachEnd_'+self.annoTable.at[ndx,'behaviors'])
                    self.eventClass.append(0)
            for nom in np.asarray(self.annoTable.loc[:,'reachInit']):
                if nom > 0:
                    self.eventListF.append(nom)
                    self.eventListN.append('reachInit')
                    self.eventClass.append(0)
            for nom in np.asarray(self.annoTable.loc[:,'reachMax']):
                if nom > 0:
                    self.eventListF.append(nom)
                    self.eventListN.append('reachMax')
                    self.eventClass.append(0)
            for nom in np.asarray(self.annoTable.loc[:,'pellet_delivery']):
                if nom > 0 and not nom in self.eventListF:
                    self.eventListF.append(nom)
                    self.eventListN.append('pellet_delivery')
                    self.eventClass.append(1)
            self.eventListF = np.asarray(self.eventListF)
        else:
            rec_efile = os.path.join(self.videoSrc, '*events.txt')
            rec_efile = glob.glob(rec_efile)
            pellet_frames = list()
            if len(rec_efile):
                rec_efile = rec_efile[0]
                if not len(rec_efile):
                    print('no acquisition events found')
                    self.videoList = list()
                elif os.path.isfile(rec_efile):
                    with open(rec_efile) as fp:
                        for line in fp:
                            if len(line.split('\t')) == 2:
                                eName,eFrame = line.split('\t')
                                if eName == 'pellet_delivery':
                                    self.eventListN.append(eName)
                                    self.eventListF.append(int(eFrame))
                                    self.eventClass.append(1)
                                    pellet_frames.append(int(eFrame))
                                elif eName == 'reach_detected':
                                    self.eventListN.append('stim')
                                    self.eventListF.append(int(eFrame))
                                    self.eventClass.append(1)
                                
            else:
                print('no events file found')
                self.videoList = list()
                                    
            if os.path.isfile(efile):
                with open(efile) as fp:
                    self.rchct = 0
                    rchstarts = list()
                    for line in fp:
                        eName,eFrame = line.split('\t')
                        self.eventListN.append(eName)
                        self.eventListF.append(int(eFrame))
                        self.eventClass.append(0)
                        if eName == 'reachInit':
                            self.rchct+=1
                            rchstarts.append(int(eFrame))
                            
                
                        
                
                if not len(self.eventListN):
                    print('mouse did not reach')
                    self.videoList = list()
                    return
                self.eventListF = np.asarray(self.eventListF)
                
                if self.rchct == 0:
                    print('mouse did not reach')
                else:
                    rchstarts.append(self.numberFrames)
                    rchstarts = np.asarray(rchstarts)
                    rows = np.arange(0,self.rchct)
                    
                    data = np.zeros([len(rows),len(self.events)],dtype='uint32')
                    
                    self.annoTable = pd.DataFrame(data,rows,self.events);
                    # anno = ['none' for i in range(self.rchct)]
                    # self.annoTable['end_category'] = anno
                    anno = ['none' for i in range(self.rchct)]
                    self.annoTable['behaviors'] = anno
                    
                    for r in range(self.rchct):
                        for f in range(rchstarts[r],rchstarts[r+1]):
                            if f in self.eventListF:
                                e = self.eventListN[np.argmax(self.eventListF == f)]
                                
                                if 'reachInit' in e and len(pellet_frames):
                                    pf = self.closest_less_than_numpy(np.asarray(pellet_frames), f)
                                    self.annoTable.at[r,'pellet_delivery'] = int(pf)
                                    self.annoTable.at[r,'reachInit'] = int(f)
                                elif 'reachEnd' in e:
                                    re = e.split('_')[1]
                                    self.annoTable.at[r,'behaviors'] = re
                                    self.annoTable.at[r,'reachEnd'] = round(f)
                                else:
                                    if not e == 'pellet_delivery':
                                        self.annoTable.at[r,e] = round(f)
                    self.saveDataSet()
            else:
                print('no post-hoc event file found')
                self.videoList = list()
                # return
        
        self.eventListN = [self.eventListN[i] for i in np.argsort(self.eventListF)]
        self.eventClass = [self.eventClass[i] for i in np.argsort(self.eventListF)]
        self.eventListF = np.sort(self.eventListF)
        eventListUniqA = list()
        for n in self.eventListN:
            eventListUniqA.append(n)
        for n in self.events:
            eventListUniqA.append(n)
        eventListUniqA = np.ndarray.tolist(np.unique(eventListUniqA))
        eventListUniq = ['all reach events']
        eventListUniq.extend(eventListUniqA)
        self.fBox.SetItems(eventListUniq)
        self.fBox.SetSelection(0)
        self.fPrev.Enable(True)
        self.fNext.Enable(True)
        self.fBox.Enable(True)
        
        self.place_event.Enable(True)
        for lab in self.labelselect:
            lab.Enable(True)
        self.bad_tracking.Enable(True)
        self.remove_event.Enable(True)
        
        
        self.eventH = list()
        self.eventT = list()
        self.annoT = list()
        for endx, e in enumerate(self.eventListN):
            ex = self.eventListF[endx]
            if self.eventClass[endx] == 0:
                self.eventH.append(self.axC.plot([ex,ex],[0,0.5],c='b',linewidth=6))
            else:
                self.eventH.append(self.axC.plot([ex,ex],[0,0.5],c='r',linewidth=6))
            
            self.eventT.append(self.axC.text(ex+0.2,0.1,e))
            if 'reachEnd' in e:
                val = self.eventListF[endx]
                col = self.annoTable.loc[:,'reachEnd']
                row = np.argmax(np.asarray(col) == val)
                ec = self.annoTable.at[row,'behaviors']
                self.annoT.append(self.axC.text(ex+0.2,0.3,ec))
            else:
                self.annoT.append(self.axC.text(ex+0.2,0.3,' '))
            
#        self.time0 = 0
#        self.axC.set_xlim([self.time0-31,self.time0+30])
        
    def closest_less_than_numpy(self, arr, y):
        mask = arr <= y
        closest_values = arr[mask]
        
        if len(closest_values) == 0:
            return None
        
        closest_x = closest_values[np.argmin(np.abs(closest_values - y))]
        return closest_x
        
    def jumpFrame(self, event):
        self.Disable
        newFrame = self.currFrame
        nc = self.fBox.GetString(self.fBox.GetSelection())
        
        if nc == 'all reach events':
            subFrmList = self.eventListF
        else:
            subndx = [i for i in range(len(self.eventListN)) if self.eventListN[i] == nc]
            subFrmList = self.eventListF[subndx]
        if not len(subFrmList):
            print('This event did not occur')
            return
        if self.fNext == event.GetEventObject():
            newFrame = subFrmList[np.argmax(subFrmList > self.currFrame)]
            print(newFrame)
        else:
            ud = np.flipud(subFrmList)
            newFrame = ud[np.argmax(self.currFrame > ud)]

        if newFrame >= self.numberFrames:
            print(self.numberFrames)
            newFrame = self.currFrame
        self.Enable
        print(newFrame)
        self.slider.SetValue(newFrame)
        self.OnSliderScroll(event)
        
    def onClick(self,event):
        if event.inaxes == self.axC:
            self.clicked_in_axes = True
            self.scroll_frm = True
            self.move_event = False
            x1 = event.xdata
            self.click_x = x1
            if round(x1) in self.eventListF:
                self.event_ndx = np.argmax(self.eventListF == round(x1))
                self.move_event = True
                label = self.eventListN[self.event_ndx]
                if 'reachEnd' in label:
                    label = 'reachEnd'
                col = np.asarray(self.annoTable.loc[:,label])
                self.row = np.argmax(col == round(x1))
                if event.button != 1:
                    self.scroll_frm = False
            
    def onMove(self,event):
        if event.inaxes == self.axC and self.clicked_in_axes:
            x1 = event.xdata
            if self.scroll_frm:
                frmadj = self.click_x-x1
                newFrame = self.currFrame+frmadj
                testA = newFrame <= self.numberFrames and newFrame > 0
                testB = round(newFrame) != self.currFrame
                if testA and testB:
                    newFrame = round(newFrame)
                    if self.move_event:
                        self.eventH[self.event_ndx][0].set_xdata(newFrame)
                        self.eventT[self.event_ndx].set_x(newFrame+0.2)
                        label = self.eventListN[self.event_ndx]
                        if 'reachEnd' in label:
                            self.annoT[self.event_ndx].set_x(newFrame+0.2)
                    self.slider.SetValue(newFrame)
                    self.OnSliderScroll(event)
            elif self.move_event:
                self.figure.canvas.restore_region(self.axCbackground)
                self.eventH[self.event_ndx][0].set_xdata(x1)
                self.eventT[self.event_ndx].set_x(x1+0.2)
                label = self.eventListN[self.event_ndx]
                if 'reachEnd' in label:
                    self.annoT[self.event_ndx].set_x(x1+0.2)
                self.axC.draw_artist(self.frmref[0])
                self.axC.draw_artist(self.frmrefT)
                self.axC.draw_artist(self.tickHa[0])
                self.axC.draw_artist(self.tickHb[0])
                for hndx,hx in enumerate(self.eventListF):
                    if hx > (self.time0-33) and hx < (self.time0+32):
                        self.axC.draw_artist(self.eventH[hndx][0])
                        self.axC.draw_artist(self.eventT[hndx])
                        self.axC.draw_artist(self.annoT[hndx])
                self.figure.canvas.blit(self.axC.bbox)
                

            
    def onButtonRelease(self, event):
        if self.clicked_in_axes:
            if self.move_event and self.scroll_frm:
                self.eventListF[self.event_ndx] = self.currFrame
            elif self.move_event and event.inaxes == self.axC:
                x1 = round(event.xdata)
                self.eventListF[self.event_ndx] = x1
                self.eventH[self.event_ndx][0].set_xdata(x1)
                self.eventT[self.event_ndx].set_x(x1+0.2)
            if self.move_event:
                val = self.eventListF[self.event_ndx]
                label = self.eventListN[self.event_ndx]
                if 'reachEnd' in label:
                    self.annoT[self.event_ndx].set_x(val+0.2)
                    label = 'reachEnd'
                self.annoTable.at[self.row,label] = val
                self.saveDataSet()
            self.move_event = False
            self.scroll_frm = False
            self.clicked_in_axes = False
            self.OnSliderScroll(event)
        
    def saveDataSet(self):
        """
        Saves the final dataframe
        """
        # self.annoTable.to_excel(self.resultsPath,index=False)
        try:
            self.annoTable.to_excel(self.resultsPath,index=False)
        except:
            wx.MessageBox('Unable to save excel file! --Is it currently open?', 'Info',
                          wx.OK | wx.ICON_INFORMATION)
            
    def placeEvent(self, event):
        subFrmList = self.eventListF
        nextlabeledfrm = subFrmList[np.argmax(subFrmList > self.currFrame)]
        event_ndx = np.argmax(self.eventListF == nextlabeledfrm)
        label = self.eventListN[event_ndx]
        if label == 'reachInit':
            colnames = self.annoTable.keys()
            startfrm = self.currFrame
            newrow = {a:startfrm+n*5 for n,a in enumerate(colnames)}
            newrow['behaviors'] = 'none'
            newrow['stim'] = 0
            # newrow['end_category'] = 'manualAnnotation'
            # with open('objs.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
            #     pickle.dump([self.annoTable,newrow], f)
            # newrow = pd.Series(data=newrow,name='x')
            
            self.annoTable = self.annoTable.append(newrow,ignore_index=True)
            self.annoTable.reset_index(drop=True, inplace=True)
            self.saveDataSet()
            self.loadEvents()
            self.update(event)
            self.play.SetFocus()
        else:
            print('Reaches can only be added between existing reaches!')
        
            
        
    def removeEvent(self, event):
        self.Disable
        self.move_event = False
        self.scroll_frm = False
            
        if self.currFrame in self.eventListF:
            dlg = wx.MessageDialog(None, "Are you sure?",'Delete reach',wx.YES_NO | wx.ICON_QUESTION)
            result = dlg.ShowModal()
            dlg.Destroy()
            if result == wx.ID_YES:
                self.event_ndx = np.argmax(self.eventListF == self.currFrame)
                self.move_event = True
                label = self.eventListN[self.event_ndx]
                if 'reachEnd' in label:
                    label = 'reachEnd'
                col = np.asarray(self.annoTable.loc[:,label])
                row = np.argmax(col == self.currFrame)
                self.annoTable.drop([row],axis=0,inplace=True)
                self.annoTable.reset_index(drop=True,inplace=True)
                self.saveDataSet()
                self.loadEvents()
                self.OnSliderScroll(event)
        else:
            print('Current frame must be at an event')
        self.Enable
        self.move_event = False
        self.scroll_frm = False
            
        
    def badTracking(self, event):
        badpath = os.path.join(self.rawdatadir,'BAD_TRACKING.txt')
        f = open(badpath, 'a')
        f.write('%s\t%d\n' % (self.sessStr,self.currFrame+1))
        f.close()
        
    def extract_tracking_data(self, dlc_seg):
        
        coordinates = ['x', 'y', 'likelihood']
        columns = pd.MultiIndex.from_product([self.bodyparts, coordinates], names=['parts', 'coordinates'])
        self.filt_df = list()
        
        for i, video_path in enumerate(self.videos):
            df = self.df_list[i]
            coordinates = ['x', 'y', 'likelihood']
            columns = pd.MultiIndex.from_product([self.bodyparts, coordinates], names=['parts', 'coordinates'])
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
            
            p2keep[1] = 1
            p2keep[-1] = 1
            p2keep_p[1] = 1
            p2keep_p[-1] = 1
            
            low_confidence_indices = p2keep < 0.9  # confidence threshold
            interp_counts = sum(low_confidence_indices)
            low_confidence_indices_p = p2keep_p < 0.9  # confidence threshold
            interp_counts_p = sum(low_confidence_indices_p)
            
            # Linearly interpolate low-confidence values if enough high-confidence values are identified
            if (interp_counts >= frm_count - 2):
                x2keep = np.zeros((frm_count,))
                y2keep = np.zeros((frm_count,))
            else:
                # Interpolation
                x2keep = np.interp(full_frm_ref, full_frm_ref[~low_confidence_indices],
                                              x2keep[~low_confidence_indices])
                y2keep = np.interp(full_frm_ref, full_frm_ref[~low_confidence_indices],
                                              y2keep[~low_confidence_indices])
            
            if (interp_counts_p >= frm_count - 2):
                x2keep_p = np.zeros((frm_count,))
                y2keep_p = np.zeros((frm_count,))
            else:
                # Interpolation
                x2keep_p = np.interp(full_frm_ref, full_frm_ref[~low_confidence_indices_p],
                                              x2keep_p[~low_confidence_indices_p])
                y2keep_p = np.interp(full_frm_ref, full_frm_ref[~low_confidence_indices_p],
                                              y2keep_p[~low_confidence_indices_p])
            
            x2keep[np.where(np.isnan(x2keep))] = 0
            x2keep = filtfilt(self.b, self.a, x2keep)
            y2keep[np.where(np.isnan(y2keep))] = 0
            y2keep = filtfilt(self.b, self.a, y2keep)
            
            x2keep_p[np.where(np.isnan(x2keep_p))] = 0
            x2keep_p = filtfilt(self.b, self.a, x2keep_p)
            y2keep_p[np.where(np.isnan(y2keep_p))] = 0
            y2keep_p = filtfilt(self.b, self.a, y2keep_p)
            
            # For the second video (columns: x, x likelihood)
            newdf.loc[np.arange(len(df)), ('Hand', 'x')] = x2keep
            newdf.loc[np.arange(len(df)), ('Hand', 'y')] = y2keep
            newdf.loc[np.arange(len(df)), ('Hand', 'likelihood')] = p2keep
            newdf.loc[np.arange(len(df)), ('Pellet', 'x')] = x2keep_p
            newdf.loc[np.arange(len(df)), ('Pellet', 'y')] = y2keep_p
            newdf.loc[np.arange(len(df)), ('Pellet', 'likelihood')] = p2keep_p
            self.filt_df.append(newdf)
      
        
    def loadAnnotations(self, event):
        if self.show_tracking.GetValue():
            videoSrc = self.videos[0]
            vidDir, vidName = os.path.split(videoSrc)
            vidName, vidExt = os.path.splitext(vidName)
            onlyfiles = [f for f in os.listdir(vidDir) if os.path.isfile(os.path.join(vidDir, f))]
            h5files = [h for h in onlyfiles if '0.h5' in h]
            h5parts = [(m.split('DLC')[1]) for m in h5files]
            
            if not len(h5parts):
                self.show_tracking.SetValue(0)
                print('No annotations found')
                return
            h5unique = [h5parts[0]]
            for h in h5parts:
                found = False
                for u in h5unique:
                    if u == h:
                        found = True
                if not found:
                    h5unique.append(h)
            # if len(h5unique) > 1:
            #     dlgE = wx.SingleChoiceDialog(self, "Select the analysis to use:",'The Caption',h5unique,wx.CHOICEDLG_STYLE)
            #     if dlgE.ShowModal() == wx.ID_OK:
            #         h5tag = dlgE.GetStringSelection()
            #     else:
            #         dlgE.Destroy()
            #         return
            # else:
            #     h5tag = h5unique[0]
            # scorer = 'DLC%s' % os.path.splitext(h5tag)[0]
            scorer = 'DLC_resnet50_Reach2PDec5shuffle1_1030000'
            h5list = ['%s%s.h5' % (j, scorer) for j in [os.path.splitext(v)[0] for v in self.videos]]
            self.df_likelihood = list()
            self.df_x = list()
            self.df_y = list()
            self.textH = list()
            self.df_list = list()
            self.df_len = list()
            for vndx, video in enumerate(self.videos):
                print(h5list[vndx])
                df = pd.read_hdf(h5list[vndx])
                self.df_list.append(df)
                self.df_len.append(len(df))
            
            self.extract_tracking_data(scorer)
            
            for vndx, video in enumerate(self.videos):
                df = self.filt_df[vndx]
                self.df_likelihood.append(np.empty((len(self.bodyparts),self.numberFrmList[vndx])))
                self.df_x.append(np.empty((len(self.bodyparts),self.numberFrmList[vndx])))
                self.df_y.append(np.empty((len(self.bodyparts),self.numberFrmList[vndx])))
                for bpindex, bp in enumerate(self.bodyparts):
                    self.df_likelihood[vndx][bpindex,:]=df[bp]['likelihood'].values
                    self.df_x[vndx][bpindex,:]=df[bp]['x'].values
                    self.df_y[vndx][bpindex,:]=df[bp]['y'].values
                    if vndx == 0:
                        color = self.colormapT(self.norm(self.colorIndex[bpindex]))
                        x = 1/(len(self.bodyparts)+1)*(bpindex+1)
                        self.textH.append(self.axD.text(x,0.5,bp,color=color,fontsize=16,
                                                        horizontalalignment='center',verticalalignment='center',
                                                        transform=self.axD.transAxes,fontweight='bold'))
                
                # bpindexP = self.bodyparts.index('Free')
                # pellet_test = np.where(self.df_likelihood[vndx][bpindexP,:] > 0.99)
                # cpt = self.cropPts[vndx]
                # zeroPx = np.median(self.df_x[vndx][bpindexP,pellet_test])+cpt[0]
                # zeroPy = np.median(self.df_y[vndx][bpindexP,pellet_test])+cpt[2]
                # self.pLoc[vndx].set_center([zeroPx,zeroPy])
                
#                self.pLoc[vndx].set_alpha(self.alpha)
                self.pLoc[vndx].set_alpha(0.0)
#            self.figure.canvas.draw()
            for a in self.textH:
                self.axC.draw_artist(a)
            self.figure.canvas.blit(self.axD.bbox)
            self.update(None)
        else:
            self.bad_tracking.Enable(False)
            for ndx, _ in enumerate(self.axes):
                self.pLoc[ndx].set_alpha(0)
                for bp in range(len(self.bodyparts)):
                    self.circle[ndx][bp].set_alpha(0.0)
        
    def quitButton(self, event):
        """
        Quits the GUI
        """
        
        print('Close event called')
        self.canvas.mpl_disconnect(self.onClick)
        self.canvas.mpl_disconnect(self.onButtonRelease)
        self.canvas.mpl_disconnect(self.onMove)
        self.statsusbar.SetStatusText("")
        self.Destroy()
    
    def vidPlayer(self, event):
        deltaF = (self.playSkip)
        newFrame = self.currFrame+deltaF
        endVal = self.endFrame.GetValue()
        if (newFrame < 0) or (deltaF > endVal):
            if self.timer.IsRunning():
                self.timer.Stop()
                self.play.SetValue(False)
        else:
            self.slider.SetValue(newFrame)
            self.OnSliderScroll(event)
        
    def updateSlider(self,event):
        self.slider.SetValue(self.startFrame.GetValue())
        self.OnSliderScroll(event)
    
    def OnSliderScroll(self, event):
        """
        Slider to scroll through the video
        """
        self.currFrame = self.slider.GetValue()
        self.endFrame.SetMax(self.numberFrames-self.currFrame)
        if self.endFrame.GetValue() > (self.numberFrames-self.currFrame):
            self.endFrame.SetValue(self.numberFrames-self.currFrame)
        else:
            self.endFrame.SetValue(self.numberFrames-self.currFrame-1)
            
        self.startFrame.SetValue(self.currFrame)
        self.update(event)
    
    def resetFocus(self, event):
        if self.labelselect[0] == event.GetEventObject():
            initArr = np.asarray(self.annoTable.loc[:,'reachInit'])
            prevInit = self.closest_less_than_numpy(initArr,self.currFrame)
            if prevInit == None:
                print('Must be within a reach')
                return
            thisReach = np.where(initArr == prevInit)[0][0]
            thisEnd = self.annoTable.loc[thisReach,'reachEnd']
            if self.currFrame >= prevInit and self.currFrame <= thisEnd:
                val = self.labelselect[0].GetString(self.labelselect[0].GetSelection())
                self.annoTable.at[thisReach,'behaviors'] = val
                self.annoT[thisReach].set_text(val)
                self.saveDataSet()
            else:
                print('Must be within a reach')
        self.saveDataSet()
        self.loadEvents()
        self.update(event)
        self.play.SetFocus()
        
    def update(self,event):
        """
        Updates the image with the current slider index
        """
        
        for ndx, im in enumerate(self.im):
            
            self.figure.canvas.restore_region(self.axbackground[ndx])
            vidfrm = self.frmReadNdx[ndx][self.currFrame]
            ret = False
            if self.show_tracking.GetValue():
                for c in self.circle[ndx]:
                    c.set_alpha(0.0)
            if vidfrm >= 0:
                if not self.adv_single:
                    self.vid[ndx].set(1,vidfrm)
                ret, frame = self.vid[ndx].read()
                
                if self.show_tracking.GetValue():
                    if isinstance(self.cfg['bodyparts'],list):
                        parts = self.bodyparts
                        for ptname in parts:
                            bpndx = self.bodyparts.index(ptname)
                            bp_test = self.df_likelihood[ndx][bpndx,vidfrm]
                            if bp_test > 0.9:
                                self.drawCirc(ndx,bpndx, vidfrm)
                    
            if ret and np.size(frame) > 1:
                frame = frame
            else:
                frame = self.blankframe
            im.set_data(frame)
            self.axes[ndx].draw_artist(im)
            self.axes[ndx].draw_artist(self.croprec[ndx])
            
            
        self.figure.canvas.restore_region(self.axCbackground)
        self.time0 = self.currFrame
        
        initArr = np.asarray(self.annoTable.loc[:,'reachInit'])
        prevInit = self.closest_less_than_numpy(initArr,self.time0)
        self.labelselect[0].SetSelection(len(self.annocat)-1)
        if not prevInit == None:
            thisReach = np.where(initArr == prevInit)[0][0]
            thisEnd = self.annoTable.loc[thisReach,'reachEnd']
            if self.time0 >= prevInit and self.time0 <= thisEnd:
                bstr = self.annoTable.at[thisReach,'behaviors']
                val = self.labelselect[0].FindString(bstr)
                if not val == -1:
                    self.labelselect[0].SetSelection(val)
        
        self.axC.set_xlim([self.time0-31,self.time0+30])
        self.frmref[0].set_xdata([self.time0,self.time0])
        self.frmrefT.set_x(self.time0)
        self.frmrefT.set_text('%d' % self.time0)
        
        self.axC.draw_artist(self.frmref[0])
        self.axC.draw_artist(self.frmrefT)
        self.axC.draw_artist(self.tickHa[0])
        self.axC.draw_artist(self.tickHb[0])
        for hndx,hx in enumerate(self.eventListF):
            if hx > (self.time0-33) and hx < (self.time0+32):
                self.axC.draw_artist(self.eventH[hndx][0])
                self.axC.draw_artist(self.eventT[hndx])
                self.axC.draw_artist(self.annoT[hndx])
            
        self.figure.canvas.blit(self.axC.bbox)
        for ndx, a in enumerate(self.axes):
            if self.show_tracking.GetValue():
                for c in self.circle[ndx]:
                    a.draw_artist(c)
            self.figure.canvas.blit(a.bbox)
        

            

            
#        self.figure.canvas.draw()
        
#        self.figure.canvas.flush_events()
        
    def drawCirc(self, ndx, bpndx, vidfrm):
        self.points = [int(self.df_x[ndx][bpndx,vidfrm]),int(self.df_y[ndx][bpndx,vidfrm]),1.0]
        cpt = self.cropPts[ndx]
        self.points[0] = self.points[0]+cpt[0]
        self.points[1] = self.points[1]+cpt[2]
        self.circle[ndx][bpndx].set_center(self.points)
        self.circle[ndx][bpndx].set_alpha(self.alpha)
            
    def grabFrame(self,event):
        self.experimenter = self.annosess_list.GetStringSelection()
        startDir = os.path.join(str(Path.home()),'Documents')
        grabDir = os.path.join(startDir,self.experimenter,'SavedFrames')
        if not os.path.exists(grabDir):
                os.makedirs(grabDir)
            
        for ndx, hax in enumerate(self.axes):
            baseName = os.path.splitext(os.path.split(self.videos[ndx])[1])[0]
            imgName = baseName+'_frm'+str(self.currFrame).zfill(int(np.ceil(np.log10(self.numberFrames)))) + '.png'
            imgPath = os.path.join(grabDir,imgName)
            if not os.path.isfile(imgPath):
                cv2.imwrite(imgPath, cv2.cvtColor(self.frameList[ndx], cv2.COLOR_RGB2BGR))
    
    def makeDemoVid(self,event):
        writer = FFMpegWriter(fps=2)
        dateStr = datetime.datetime.now().strftime("%Y%m%d%H%M")
        base_dir = '/home/bioelectrics/Documents/DemoVids'
        savePath = os.path.join(base_dir,dateStr+"vidExp.mp4")
        with writer.saving(self.figure, savePath):
            while True:
                deltaF = (self.playSkip)
                newFrame = self.currFrame+deltaF
                endVal = self.endFrame.GetValue()
                if (newFrame < 0) or (deltaF > endVal):
                    break
                writer.grab_frame()
                self.vidPlayer(event)
    
def show():
    app = wx.App()
    MainFrame(None).Show()
    app.MainLoop()
    
if __name__ == '__main__':    
    show()