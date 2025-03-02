"""
CLARA toolbox
https://github.com/wryanw/CLARA
W Williamson, wallace.williamson@ucdenver.edu

"""

from __future__ import print_function
import wx
import wx.lib.dialogs
import wx.lib.scrolledpanel as SP
import cv2
import csv
import os
from pathlib import PurePath
import glob
import numpy as np
from pathlib import Path
import pandas as pd
from skimage.util import img_as_ubyte
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.colors as mcolors
import matplotlib.patches as patches
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
import multiCam_DLC_utils_v2 as clara
from matplotlib.animation import FFMpegWriter
import datetime
# ###########################################################################
# Class for GUI MainFrame
# ###########################################################################

numCams = 2;

class ImagePanel(wx.Panel):

    def __init__(self, parent, gui_size, axesCt, **kwargs):
        h=int(np.amax(gui_size)/4)
        w=int(np.amax(gui_size)/4)
        wx.Panel.__init__(self, parent, -1,style=wx.SUNKEN_BORDER,size=(h,w))

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

    def addRadioButtons(self, bodyparts, guiDim):
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
        
        choices = bodyparts
        self.fieldradiobox = list()
        if isinstance(choices,list):
            self.fieldradiobox.append(wx.RadioBox(self,label='Select a bodypart to label',
                                        style=style,choices=choices))
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
        
        return self.fieldradiobox, self.choiceBox

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
        
        self.label_frames = wx.ToggleButton(self, id=wx.ID_ANY, label="Label")
        self.labelBox.Add(self.label_frames, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.label_frames.Enable(False)
        
        
        self.stat = wx.Button(self, size=(50, -1), id=wx.ID_ANY, label="Stats")
        self.labelBox.Add(self.stat, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.stat.Enable(False)
        
        self.move_label = wx.ToggleButton(self, size=(50, -1), id=wx.ID_ANY, label="Move")
        self.labelBox.Add(self.move_label, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.move_label.Enable(False)
        
        self.omit_label = wx.Button(self, size=(50, -1), id=wx.ID_ANY, label="Omit")
        self.labelBox.Add(self.omit_label, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.omit_label.Enable(False)
        
        self.grab_labels = wx.Button(self, size=(50, -1), id=wx.ID_ANY, label="Grab")
        self.labelBox.Add(self.grab_labels, 0, wx.ALL|wx.ALIGN_CENTER, buttSpace)
        self.grab_labels.Enable(False)
        
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
        
        return(self.grab_labels,self.fBox,self.stat,self.label_frames,self.move_label,self.omit_label,
               self.fPrev,self.fNext)

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
        self.gui_size = (550,1800)
        if screenW > screenH:
            self.gui_size = (int(screenW*0.95),int(screenH*0.75))
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = 'CLARA DLC Video Explorer',
                            size = wx.Size(self.gui_size), pos = wx.DefaultPosition, style = wx.RESIZE_BORDER|wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText("")

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
        self.image_panel = ImagePanel(vSplitterA,self.gui_size, numCams)
        self.choice_panel = ScrollPanel(vSplitter)
        self.label_panel = LabelsPanel(vSplitter)
        self.widget_panel = WidgetPanel(topSplitter)
        if self.guiDim == 0:
            vSplitter.SplitVertically(self.choice_panel,self.label_panel, sashPosition=int(self.gui_size[0]*0.5))
            vSplitter.SetSashGravity(0.5)
            vSplitterA.SplitHorizontally(self.image_panel,vSplitter, sashPosition=int(self.gui_size[1]*0.75))
            vSplitterA.SetSashGravity(0.5)
            topSplitter.SplitVertically(vSplitterA, self.widget_panel,sashPosition=int(self.gui_size[0]*0.8))#0.9
            topSplitter.SetSashGravity(0.5)
        else:
            vSplitter.SplitVertically(self.image_panel,self.choice_panel, sashPosition=int(self.gui_size[0]*0.5))
            vSplitter.SetSashGravity(0.5)
            vSplitter.SplitVertically(self.image_panel,self.label_panel, sashPosition=int(self.gui_size[0]*0.5))
            vSplitter.SetSashGravity(0.5)
            topSplitter.SplitHorizontally(vSplitter, self.widget_panel,sashPosition=int(self.gui_size[1]*0.9))#0.9
        topSplitter.SetSashGravity(0.5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(sizer)

###################################################################################################################################################
# Add Buttons to the WidgetPanel and bind them to their respective functions.
        
        self.labelselect, self.choice_box = self.choice_panel.addRadioButtons(['none'],self.guiDim)
        self.grab_labels,self.fBox,self.stat,self.label_frames,self.move_label,self.omit_label,self.fPrev,self.fNext = self.label_panel.addButtons(self.guiDim)
        self.grab_labels.Bind(wx.EVT_BUTTON, self.chooseFrame)
        self.label_frames.Bind(wx.EVT_TOGGLEBUTTON, self.labelFrames)
        self.omit_label.Bind(wx.EVT_BUTTON, self.omitLabel)
        self.fPrev.Bind(wx.EVT_BUTTON, self.jumpFrame)
        self.fNext.Bind(wx.EVT_BUTTON, self.jumpFrame)
        self.stat.Bind(wx.EVT_BUTTON, self.showStats)
        
        widgetSize = 7
        widgetsizer = wx.WrapSizer(orient=wx.HORIZONTAL)
        
        self.load_vids = wx.Button(self.widget_panel, size=(150, -1), id=wx.ID_ANY, label="Load Videos")
        widgetsizer.Add(self.load_vids, 1, wx.ALL, widgetSize)
        self.load_vids.Bind(wx.EVT_BUTTON, self.loadVids)
        self.load_vids.Enable(False)
        
        widgetsizer.AddStretchSpacer(1)
        
        self.new_config = wx.Button(self.widget_panel, size=(150, -1), id=wx.ID_ANY, label="New Training Set")
        widgetsizer.Add(self.new_config, 1, wx.ALL, widgetSize)
        self.new_config.Bind(wx.EVT_BUTTON, self.newConfig)
        
        text = wx.StaticText(self.widget_panel, label='User:')
        widgetsizer.Add(text, 0, wx.ALL, widgetSize)
        userlist = ['Sole']
        self.users = wx.Choice(self.widget_panel, size=(100, -1), id=wx.ID_ANY, choices=userlist)
        widgetsizer.Add(self.users, 1, wx.ALL, widgetSize)
        self.users.SetSelection(0)
        
        widgetsizer.AddStretchSpacer(1)
        
        self.load_config = wx.Button(self.widget_panel, size=(150, -1), id=wx.ID_ANY, label="Load Config File")
        widgetsizer.Add(self.load_config, 1, wx.ALL, widgetSize)
        self.load_config.Bind(wx.EVT_BUTTON, self.loadConfig)
        
        self.show_tracking = wx.CheckBox(self.widget_panel, id=wx.ID_ANY,label = 'Load Analysis Labels')
        widgetsizer.Add(self.show_tracking, 0, wx.ALL, widgetSize)
        self.show_tracking.Bind(wx.EVT_CHECKBOX, self.loadAnnotations)
        
        
        self.slider = wx.Slider(self.widget_panel, -1, 0, 0, 100,size=(300, -1), style=wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS )
        widgetsizer.Add(self.slider, 2, wx.ALL, widgetSize)
        self.slider.Bind(wx.EVT_SLIDER, self.OnSliderScroll)
        self.slider.Enable(False)
        
        self.play = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Play")
        widgetsizer.Add(self.play , 1, wx.ALL, int(widgetSize*1.25))
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
        self.speedOps = [-50,-10,-1,1,10,50]
        viewopts = ['-500','-100','-10 ','10  ','100 ','500']
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
        self.startFrame.Bind(wx.EVT_SPINCTRL, self.updateSlider)
        end_text = wx.StaticText(self.widget_panel, label='Frames Remaining')
        self.end_frames_sizer.Add(end_text, 1, wx.EXPAND|wx.ALIGN_LEFT, widgetSize)
        
        widgetsizer.Add(self.start_frames_sizer, 1, wx.ALL, widgetSize)
        widgetsizer.AddStretchSpacer(1)
        widgetsizer.Add(self.end_frames_sizer, 1, wx.ALL, widgetSize)
        
        self.train = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Train")
        widgetsizer.Add(self.train , 1, wx.ALL, widgetSize)
        self.train.Bind(wx.EVT_BUTTON, self.trainNetwork)
        
        widgetsizer.AddStretchSpacer(1)
        
        self.anal = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Analyze")
        widgetsizer.Add(self.anal, 1, wx.ALL, widgetSize)
        self.anal.Bind(wx.EVT_BUTTON, self.analyzeVids)
        
        widgetsizer.AddStretchSpacer(1)
        
        self.quit = wx.Button(self.widget_panel, id=wx.ID_ANY, label="Quit")
        widgetsizer.Add(self.quit , 1, wx.ALL, widgetSize)
        self.quit.Bind(wx.EVT_BUTTON, self.quitButton)
        self.Bind(wx.EVT_CLOSE, self.quitButton)
        
        #Make Review Button
        self.review = wx.ToggleButton(self.widget_panel, id=wx.ID_ANY, label="Review Mode")
        widgetsizer.Add(self.review , 1, wx.ALL, widgetSize)
        self.review.Bind(wx.EVT_TOGGLEBUTTON, self.reviewMode)
        
        widgetsizer.AddStretchSpacer(1)
        
        widgetsizer.Add(self, 1, wx.EXPAND)
        self.widget_panel.SetSizer(widgetsizer)
        widgetsizer.Fit(self.widget_panel)
        self.widget_panel.Layout()
        
        self.timer = wx.Timer(self, wx.ID_ANY)
        self.videos = list()
        self.shuffle = 1
        self.trainingsetindex = 0
        self.currAxis = 0
        self.x1 = 0
        self.y1 = 0
        self.vid = list()
        self.videoList = list()
        self.auto_grab = False
        self.rev = False
        
        
        
        usrdatadir = os.path.dirname(os.path.realpath(__file__))
        _, user = os.path.split(Path.home())
        self.usrdatapath = os.path.join(usrdatadir, '%s_userdata.txt' % user)
        if os.path.isfile(self.usrdatapath):
            usrdata = open(self.usrdatapath, 'r')
            self.config_path = usrdata.readline()
            usrdata.close()
            self.load_vids.Enable(True)
            self.statusbar.SetStatusText('Current config: %s' % self.config_path)
            
    def movePts(self, mag):
        bp = self.labelselect[0].GetString(self.labelselect[0].GetSelection())
        for ndx, hax in enumerate(self.axes):
            if self.currAxis == hax:
                self.x1 = self.x1+mag[0]
                self.y1 = self.y1+mag[1]
                if self.rev:
                    self.dataFrame.loc[self.currFrame][self.scorer, bp, 'x' ] = self.x1
                    self.dataFrame.loc[self.currFrame][self.scorer, bp, 'y' ] = self.y1
                else:                
                    self.dataFrame[ndx].loc[self.relativeimagenames[self.currFrame]][self.scorer, bp, 'x' ] = self.x1
                    self.dataFrame[ndx].loc[self.relativeimagenames[self.currFrame]][self.scorer, bp, 'y' ] = self.y1
        self.update(None)
        
    def OnKeyPressed(self, event):
        
#        print(event.GetKeyCode())
#        print(wx.WXK_RETURN)
        
        if self.play.IsEnabled() == True or self.rev:
            if event.GetKeyCode() == wx.WXK_UP:
                if self.move_label.GetValue():
                    self.movePts([0, -1])
                else:
                    if self.play.GetValue() == True:
                        self.play.SetValue(False)
                        self.fwrdPlay(event=None)
                    self.slider.SetValue(self.slider.GetValue()+1)
                    self.OnSliderScroll(event)
            elif event.GetKeyCode() == wx.WXK_DOWN:
                if self.move_label.GetValue():
                    self.movePts([0, 1])
                else:
                    if self.play.GetValue() == True:
                        self.play.SetValue(False)
                        self.fwrdPlay(event=None)
                    self.slider.SetValue(self.slider.GetValue()-1)
                    self.OnSliderScroll(event)
            elif event.GetKeyCode() == wx.WXK_LEFT:
                if self.move_label.GetValue():
                    self.movePts([-1, 0])
                elif self.speedbox.GetSelection() > 0:
                    self.speedbox.SetSelection(self.speedbox.GetSelection()-1)
                    self.playSpeed(event=None)
            elif event.GetKeyCode() == wx.WXK_RIGHT:
                if self.move_label.GetValue():
                    self.movePts([1, 0])
                elif self.speedbox.GetSelection() < (self.speedbox.GetCount()-1):
                    self.speedbox.SetSelection(self.speedbox.GetSelection()+1)
                    self.playSpeed(event=None)
            elif event.GetKeyCode() == wx.WXK_SPACE:
                self.move_label.SetValue(0)
                if self.play.GetValue() == True:
                    self.play.SetValue(False)
                else:   
                    self.play.SetValue(True)
                self.fwrdPlay(event=None)
            elif self.move_label.GetValue():
                self.move_label.SetValue(0)
        else:
            event.Skip()

    def fwrdPlay(self, event):
        if self.play.GetValue() == True:
            if not self.timer.IsRunning():
                self.timer.Start(100)
            self.play.SetLabel('Stop')
        else:
            if self.timer.IsRunning():
                self.timer.Stop()
            self.play.SetLabel('Play')
        
    def playSpeed(self, event):
        wasRunning = False
        if self.timer.IsRunning():
            wasRunning = True
            self.timer.Stop()
        self.playSkip = self.speedOps[self.speedbox.GetSelection()]
        self.slider.SetPageSize(pow(5,(self.speedbox.GetSelection()-1)))
        self.play.SetFocus()
        if wasRunning:
            self.timer.Start(100)
            
    def newConfig(self, event):
        
        dlgP = wx.TextEntryDialog(self, 'Enter a project name')
        if dlgP.ShowModal() == wx.ID_OK:
            project = dlgP.GetValue()
            dlgP.Destroy()
            startDir = os.path.join(str(Path.home()),'Documents')
            dlgD = wx.DirDialog(self, 'Choose a project directory',startDir)
            if dlgD.ShowModal() == wx.ID_OK:
                working_directory = os.path.join(dlgD.GetPath())
                dlgD.Destroy()
                dlgV = wx.FileDialog(self, 'Select a starting video')
#                    wildcard = "Avi files (*.avi)|*.avi"
                wildcard = "Mp4 files (*264.mp4)|*264.mp4"
                dlgV.SetWildcard(wildcard)
                dlgV.SetDirectory(startDir)
                startDir = r'Y:\ChristieLab\Data\JetsonAutoTrainer'
                dlgV.SetDirectory(startDir)
                if dlgV.ShowModal() == wx.ID_OK:
                    videoSrc = dlgV.GetPath()
                    vidDir, vidName = os.path.split(videoSrc)
                    vidName, vidExt = os.path.splitext(vidName)
                    # print(vidDir)
                    # print(vidName)
                    # print(vidExt)
                    # print(os.listdir(vidDir))
                    # self.videoList = [os.path.join(vidDir,vidName+vidExt)]
                    self.videoList = list()
                    for vidfile in os.listdir(vidDir):
                        if vidfile.endswith('264'+vidExt):
                            # vidParts = vidName.split('_')[0:3]
                            vidParts = vidfile.split('_')[0:3]
                            vidBase = '_'.join(vidParts)
                            if vidBase in vidfile and vidExt in vidfile:
                                print(os.path.join(vidDir,vidfile))
                                self.videoList.append(os.path.join(vidDir,vidfile))
                    print(len(self.videoList))
                    if len(self.videoList) == numCams:
                        self.config_path = clara.create_CLARA_project(self.videoList, project,'christie', working_directory)
                        usrdatadir = os.path.dirname(os.path.realpath(__file__))
                        _, user = os.path.split(Path.home())
                        usrdatapath = os.path.join(usrdatadir, '%s_userdata.txt' % user)
                        usrdata = open(usrdatapath, 'w')
                        usrdata.write(self.config_path)
                        self.statusbar.SetStatusText('Current config: %s' % self.config_path)
                        self.load_vids.Enable(True)
                        self.loadVids(event=None)
                    else:
                        print('Not enough videos found!')
                else:
                    dlgV.Destroy()
            else:
                dlgD.Destroy()
        else:
            dlgP.Destroy()
        
    def loadConfig(self, event):
        wildcard = "Config files (*.yaml)|*.yaml"
        dlg = wx.FileDialog(self, "Select a config file.")
        dlg.SetWildcard(wildcard)
        startDir = os.path.join(str(Path.home()),'Documents')
        dlg.SetDirectory(startDir)
        
        if dlg.ShowModal() == wx.ID_OK:
            self.config_path = dlg.GetPath()
            self.load_vids.Enable(True)
            usrdatadir = os.path.dirname(os.path.realpath(__file__))
            _, user = os.path.split(Path.home())
            usrdatapath = os.path.join(usrdatadir, '%s_userdata.txt' % user)
            usrdata = open(usrdatapath, 'w')
            usrdata.write(self.config_path)
            self.statusbar.SetStatusText('Current config: %s' % self.config_path)
            usrdata.close()
        else:
            dlg.Destroy()
        
        
    def loadVids(self, event):
        if self.show_tracking.GetValue():
            self.show_tracking.SetValue(False)
            self.loadAnnotations(None)
        if self.label_frames.GetValue() == True:
            self.label_frames.SetValue(False)
            self.labelFrames(None)
        if len(self.vid) > 0:
            for vid in self.vid:
                vid.release()
        
        self.figure,self.axes,self.canvas = self.image_panel.getfigure()
        if len(self.axes[0].get_children()) > 0:
            for hax in self.axes:
                hax.clear()
            self.figure.canvas.draw()
            
# =============================================================================
#        self.videos = ['/home/wrw/Documents/20190817/unit03/session002/20190827_unit03_session002_frontCam-0000.mp4',
#            '/home/wrw/Documents/20190817/unit03/session002/20190827_unit03_session002_sideCam-0000.mp4',
#            '/home/wrw/Documents/20190817/unit03/session002/20190827_unit03_session002_topCam-0000.mp4']
#        self.videoList = self.videos
#        self.config_path='/home/bioelectrics/Documents/CLARA_RT_DLC-WRW-2019-07-10/config.yaml'
# =============================================================================
        
        if not len(self.videoList):
            dlgV = wx.FileDialog(self, 'Select a video')
#            wildcard = "Avi files (*.avi)|*.avi"
            wildcard = "Mp4 files (*264.mp4)|*264.mp4"
            dlgV.SetWildcard(wildcard)
            startDir = r'Z:\Data\LocoMouse'
            dlgV.SetDirectory(startDir)
            if dlgV.ShowModal() == wx.ID_OK:
                videoSrc = dlgV.GetPath()
                vidDir, vidName = os.path.split(videoSrc)
                vidName, vidExt = os.path.splitext(vidName)
                # print(vidDir)
                # print(vidName)
                # print(vidExt)
                # print(os.listdir(vidDir))
                # self.videoList = [os.path.join(vidDir,vidName+vidExt)]
                self.videoList = list()
                for vidfile in os.listdir(vidDir):
                    
                    if vidfile.endswith('264'+vidExt):
                        # vidParts = vidName.split('_')[0:3]
                        vidParts = vidfile.split('_')[0:3]
                        vidBase = '_'.join(vidParts)
                        if vidBase in vidfile:
                            self.videoList.append(os.path.join(vidDir,vidfile))
                if len(self.videoList) != numCams:
                    print('Not enough videos found!')
                    return
            else:
                dlgV.Destroy()
                return
        else:
            vidDir = os.path.split(self.videoList[0])[0]
        
        self.cfg = clara.read_dlc_config(self.config_path)
        self.currFrame = 0
        self.bodyparts = self.cfg['bodyparts']
        # checks for unique bodyparts
        if len(self.bodyparts)!=len(set(self.bodyparts)):
            print("Error - bodyparts must have unique labels! Please choose unique bodyparts in config.yaml file and try again.")

        cppos = self.choice_panel.GetPosition()
        cprect = self.choice_panel.GetRect()
        cpsize = self.choice_panel.GetSize()
        self.choice_panel.replaceRadio()
        self.labelselect, self.choice_box = self.choice_panel.addRadioButtons(self.bodyparts,self.guiDim)
        self.choice_panel.SetPosition(cppos)
        self.choice_panel.SetRect(cprect)
        self.choice_panel.SetSize(cpsize)
        # self.choice_panel.SetupScrolling()
        scroll_unit = self.choice_panel.GetScrollPixelsPerUnit()
        box_size = self.choice_box.GetSize()
        self.scroll_unit = box_size[0]/len(self.bodyparts)/scroll_unit[0]
        # print(self.scroll_unit)
        
                    
        for rad in self.labelselect:
            rad.Bind(wx.EVT_RADIOBOX, self.resetFocus)
        efile = 'none'
        if os.path.isfile(efile):
            self.eventListN = list()
            self.eventListF = list()
            with open(efile) as fp:
                for line in fp:
                    eName,eFrame = line.split('\t')
                    self.eventListN.append(eName)
                    self.eventListF.append(int(eFrame))
            eventListUniq = np.ndarray.tolist(np.unique(self.eventListN))
            self.eventListF = np.asarray(self.eventListF)
            self.fBox.SetItems(eventListUniq)
            self.fBox.SetSelection(0)
            self.fPrev.Enable(True)
            self.fNext.Enable(True)
            self.fBox.Enable(True)
        else:
            self.eventListN = []
            self.eventListF = []
            self.fPrev.Enable(False)
            self.fNext.Enable(False)
            self.fBox.Enable(False)

        if not len(self.eventListN):
            efile = os.path.join(vidDir, '*events.txt')
            # print(efile)
            efile = glob.glob(efile)
            # print(efile)
            if len(efile):
                efile = efile[0]
        if len(efile) and os.path.isfile(efile):
            self.eventListN = list()
            self.eventListF = list()
            with open(efile) as fp:
                for line in fp:
                    if len(line.split('\t')) == 2:
                        eName,eFrame = line.split('\t')
                        self.eventListN.append(eName)
                        self.eventListF.append(int(eFrame))
            eventListUniq = np.ndarray.tolist(np.unique(self.eventListN))
            self.eventListF = np.asarray(self.eventListF)
            self.fBox.SetItems(eventListUniq)
            self.fBox.SetSelection(0)
            self.fPrev.Enable(True)
            self.fNext.Enable(True)
            self.fBox.Enable(True)
        else:
            self.eventListN = []
            self.eventListF = []
            self.fPrev.Enable(False)
            self.fNext.Enable(False)
            self.fBox.Enable(False)
    
        self.colormap = plt.get_cmap(self.cfg['colormap'])
        self.colormap = self.colormap.reversed()
        self.markerSize = 3
        # self.alpha = self.cfg['alphavalue']
        self.alpha = 1
        self.iterationindex=self.cfg['iteration']
        
        self.vid = list()
        self.im = list()
        self.videos = list()
        
        self.user_cfg = clara.read_config()
        key_list = list()
        print(self.user_cfg)
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
        clara.add_CLARA_videos(self.config_path,self.videos)
        self.frameList = list()
        self.cropPts = list()
        self.numberFrmList = list()
        
        if isinstance(self.bodyparts,list):
            parts = self.bodyparts
        else:
            parts = list()
            self.categories = list()
            for cat in self.bodyparts.keys():
                self.categories.append(cat)
            for key in self.categories:
                for ptname in self.bodyparts[key]:
                    parts.append(ptname)
        self.bodyparts = parts
        self.act_sel = 3
        self.sys_timer = [0,0,0]
        
        self.im = list()
        self.circle = list()
        self.croprec = list()
        self.pLoc = list()
        for vndx, video in enumerate(self.videos):
            
            video_source = Path(video).resolve()
            self.vid.append(cv2.VideoCapture(str(video_source)))
            self.vid[vndx].set(1,self.currFrame)
            ret, frame = self.vid[vndx].read()
            frmW = self.vid[vndx].get(cv2.CAP_PROP_FRAME_WIDTH)
            frmH = self.vid[vndx].get(cv2.CAP_PROP_FRAME_HEIGHT)
            # cpt = self.user_cfg[videoOrder[vndx]+'Crop']
            cpt = [0,int(frmW),0,int(frmH)]
            self.cropPts.append(cpt)
            try:
                frame = img_as_ubyte(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            except:
                print('Frame reading error')
                return
            
#            frame = np.zeros(np.shape(frame))
#            cpt = self.cropPts[vndx]
#            frame = frame[cpt[2]:cpt[2]+cpt[3],cpt[0]:cpt[0]+cpt[1]]
            self.im.append(self.axes[vndx].imshow(frame))
            self.frameList.append(frame)
            self.numberFrames = int(self.vid[vndx].get(cv2.CAP_PROP_FRAME_COUNT))
            self.numberFrmList.append(self.numberFrames)
            
            self.norm,self.colorIndex = self.image_panel.getColorIndices(frame,self.bodyparts)
            self.points = [0,0,1.0]
            circleH = list()
            for bpndx, bp in enumerate(self.bodyparts):
                if bp == 'FRside':
                    color = [0,1,1]
                elif bp == 'HRside':
                    color = [1,0,1]
                else:
                    color = self.colormap(self.norm(self.colorIndex[bpndx]))
                circle = [patches.Circle((self.points[0], self.points[1]), radius=self.markerSize,
                                         linewidth=2, fc = color, alpha=0.0)]
                circleH.append(self.axes[vndx].add_patch(circle[0]))
            self.circle.append(circleH)
  
            croprec = [patches.Rectangle((cpt[0]+1,cpt[2]+1), cpt[1]-3, cpt[3]-3, fill=False,
                                         ec = [0.25,0.75,0.25], linewidth=2, linestyle='-',alpha=self.alpha)]
            self.croprec.append(self.axes[vndx].add_patch(croprec[0]))
            circle = [patches.Circle((0, 0), radius=5, linewidth = 2, fc=[1,1,1], alpha=0.0)]
            self.pLoc.append(self.axes[vndx].add_patch(circle[0]))
            croprec = [patches.Rectangle((cpt[0]+cpt[1]/2+24,cpt[2]+1), 50, cpt[3]-3, fill=False,
                                         ec = [0.75,0.25,0.25], linewidth=2, linestyle='-',alpha=self.alpha)]
#        ylim = self.axes[vndx].get_ylim()
#        self.axes[vndx].set_ylim([ylim[1],ylim[0]])
        print(f'Video: {self.vid}')
        self.numberFrames = int(self.vid[vndx].get(cv2.CAP_PROP_FRAME_COUNT))
        self.strwidth = int(np.ceil(np.log10(self.numberFrames)))
        self.statusbar.SetStatusText('Current video: %s' % video)
        # Set the values of slider and range of frames
        self.slider.SetMax(self.numberFrames-1)
        self.endFrame.SetMax(self.numberFrames-1)
        self.endFrame.SetValue(self.numberFrames-1)
        self.startFrame.SetValue(0)
        self.endFrame.Bind(wx.EVT_SPINCTRL,self.updateSlider)#wx.EVT_SPIN
        self.startFrame.Bind(wx.EVT_SPINCTRL,self.updateSlider)#wx.EVT_SPIN
        
        self.grab_frame.Enable(True)
        self.save.Enable(True)
        self.play.Enable(True)
        self.slider.Enable(True)
        self.speedbox.Enable(True)
        self.startFrame.Enable(True)
        self.endFrame.Enable(True)
        self.label_frames.Enable(True)
        self.newLabelCt = 0
        self.videoList = list()
        self.Bind(wx.EVT_TIMER, self.vidPlayer, self.timer)
        self.widget_panel.Layout()
        self.slider.SetValue(self.currFrame)
        self.playSpeed(event)
        self.OnSliderScroll(event=None)
        
        videoSrc = self.videos[0]
        vidDir, vidName = os.path.split(videoSrc)
        vidName, vidExt = os.path.splitext(vidName)
        onlyfiles = [f for f in os.listdir(vidDir) if os.path.isfile(os.path.join(vidDir, f))]
        h5files = [h for h in onlyfiles if '0.h5' in h]
        h5parts = [(m.split('DLC')[1]) for m in h5files]
        if len(h5parts):
            self.show_tracking.SetValue(True)
            self.loadAnnotations(None)
                
    def resetFocus(self, event):
        for rndx, rad in enumerate(self.labelselect[1:]):
            if rad == event.GetEventObject():
                self.labelselect[0].SetSelection(rndx)
                self.labelselect[rndx+1].SetSelection(event.GetSelection())
        self.update(None)
        self.play.SetFocus()
        
    

   
            
    def showStats(self, event):
        print(self.bodyparts)
        runTot = np.zeros((len(self.bodyparts),1))
        sumry = '---Subtotals---'
        for ndx,df in enumerate(self.dataFrame):
            datastats = df.count().values
            if ndx > 0:
                sumry+='\n'
            sumry+= '\n%s:\n' % os.path.split(self.videos[ndx])[1]
            for n,s in enumerate(range(0,len(datastats),2)):
                if n > 0:
                    sumry+=' - '
                runTot[n]+=datastats[s]
                sumry+='%s: %d' % (self.bodyparts[n],datastats[s])
                
        sumry+='\n\n---Total Counts---\n'
        for ndx, t in enumerate(runTot):
            if n > 0:
                sumry+=' - '
            sumry+='%s: %d' % (self.bodyparts[ndx],t)
            
        data_path = Path(self.config_path).parents[0] / 'labeled-data'
        f_list = [name for name in os.listdir(data_path)]
        runTot = np.zeros((len(self.bodyparts),1))
        for f in f_list:
            dataFiles = os.path.join(data_path, f, '*.h5')
            data_list = glob.glob(dataFiles)
            for d in data_list:
                if not len(d):
                    continue
                # print(d)
                statData = pd.read_hdf(d,'df_with_missing')
                datastats = statData.count().values
                for n,s in enumerate(range(0,len(datastats),2)):
                    runTot[n]+=datastats[s]
                    
        sumry+='\n\n---Grand Total Counts---\n'
        for ndx, t in enumerate(runTot):
            if n > 0:
                sumry+=' - '
            sumry+='%s: %d' % (self.bodyparts[ndx],t)
            
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, sumry, "Summary Stats")
        dlg.ShowModal()
        dlg.Destroy()
        
    def saveDataSet(self):
        """
        Saves the final dataframe
        """
        # print('Save disabled')
        self.Disable
        for ndx, dirs in enumerate(self.label_dirs):
            if self.rev:
                if dirs is not None:
                    self.dataFrame.sort_index(inplace=True)
                    self.dataFrame.to_csv(os.path.splitext(self.curr_h5)[0]+'.csv')
                    self.dataFrame.to_hdf(self.curr_h5,'df_with_missing',format='table', mode='w')
            else:
                self.dataFrame[ndx].sort_index(inplace=True)
                self.dataFrame[ndx].to_csv(os.path.join(dirs,"CollectedData_" + self.scorer + ".csv"))
                self.dataFrame[ndx].to_hdf(os.path.join(dirs,"CollectedData_" + self.scorer + '.h5'),'df_with_missing',format='table', mode='w')
        print('Data saved!')
        self.Enable
        
    def chooseFrame(self, event):
        self.auto_grab = True
        for ndx, hax in enumerate(self.axes):
            event.inaxes = hax
            for bp in self.bodyparts:
                bpndx = self.bodyparts.index(bp)
                bp_test = self.df_likelihood[ndx][bpndx,self.currFrame]
                if bp_test > 0.9:
                    self.labelselect[0].SetSelection(bpndx)
                    event.xdata = int(self.df_x[ndx][bpndx,self.currFrame])
                    event.ydata = int(self.df_y[ndx][bpndx,self.currFrame])
                    self.onClick(event)
        self.move_label.SetValue(0)
        self.update(None)
        self.auto_grab = False
        
    

       
    def omitLabel(self, event):
        for ndx, hax in enumerate(self.axes):
            event.inaxes = hax
            event.xdata = np.nan
            event.ydata = np.nan
            self.onClick(event)
        self.move_label.SetValue(0)
        
    def loadAnnotations(self, event):
        if self.show_tracking.GetValue():
            videoSrc = self.videos[0]
            vidDir, vidName = os.path.split(videoSrc)
            vidName, vidExt = os.path.splitext(vidName)
            onlyfiles = [f for f in os.listdir(vidDir) if os.path.isfile(os.path.join(vidDir, f))]
            h5files = [h for h in onlyfiles if '0.h5' in h]
            h5parts = [(m.split('DLC')[1]) for m in h5files]
            if not len(h5parts):
                print('No annotations found')
                self.grab_labels.Enable(False)
                for ndx, _ in enumerate(self.axes):
                    self.pLoc[ndx].set_alpha(0)
                    if not self.label_frames.GetValue():
                        for bp in range(len(self.bodyparts)):
                            self.circle[ndx][bp].set_alpha(0.0)
                return
            h5unique = [h5parts[0]]
            for h in h5parts:
                found = False
                for u in h5unique:
                    if u == h:
                        found = True
                if not found:
                    h5unique.append(h)
            if len(h5unique) > 1:
                dlgE = wx.SingleChoiceDialog(self, "Select the analysis to use:",'The Caption',h5unique,wx.CHOICEDLG_STYLE)
                if dlgE.ShowModal() == wx.ID_OK:
                    h5tag = dlgE.GetStringSelection()
                else:
                    dlgE.Destroy()
                    return
            else:
                h5tag = h5unique[0]
            scorer = 'DLC%s' % os.path.splitext(h5tag)[0]
            h5list = ['%s%s.h5' % (j, scorer) for j in [os.path.splitext(v)[0] for v in self.videos]]
            self.df_likelihood = list()
            self.df_x = list()
            self.df_y = list()
            self.textH = list()
            
            for vndx, video in enumerate(self.videos):
                Dataframe = pd.read_hdf(h5list[vndx])
                self.df_likelihood.append(np.empty((len(self.bodyparts),self.numberFrmList[vndx])))
                self.df_x.append(np.empty((len(self.bodyparts),self.numberFrmList[vndx])))
                self.df_y.append(np.empty((len(self.bodyparts),self.numberFrmList[vndx])))
                cpt = self.cropPts[vndx]
                self.bpInDf = Dataframe.columns.get_level_values(1)
                for bpindex, bp in enumerate(self.bodyparts):
                    if not bp in self.bpInDf:
                        continue
                    self.df_likelihood[vndx][bpindex,:]=Dataframe[scorer][bp]['likelihood'].values
                    self.df_x[vndx][bpindex,:]=Dataframe[scorer][bp]['x'].values
                    self.df_y[vndx][bpindex,:]=Dataframe[scorer][bp]['y'].values
                
                self.textH.append(self.axes[vndx].text(10,cpt[-1]-1,' ',color=[1,1,1],fontsize=8))
                
                # bpindexP = self.bodyparts.index('Free')
                # pellet_test = np.where(self.df_likelihood[vndx][bpindexP,:] > 0.99)
                # cpt = self.cropPts[vndx]
                # zeroPx = np.median(self.df_x[vndx][bpindexP,pellet_test])+cpt[0]
                # zeroPy = np.median(self.df_y[vndx][bpindexP,pellet_test])+cpt[2]
                # self.pLoc[vndx].set_center([zeroPx,zeroPy])
                # self.pLoc[vndx].set_alpha(self.alpha)
                self.pLoc[vndx].set_alpha(0.0)
            if self.label_frames.GetValue():
                self.grab_labels.Enable(True)
            self.update(None)
        else:
            self.grab_labels.Enable(False)
            for ndx, _ in enumerate(self.axes):
                self.pLoc[ndx].set_alpha(0)
                if not self.label_frames.GetValue():
                    for bp in range(len(self.bodyparts)):
                        self.circle[ndx][bp].set_alpha(0.0)
            self.update(None)
        
    def quitButton(self, event):
        """
        Quits the GUI
        """
        print('Close event called')
        self.statusbar.SetStatusText("")
        if self.label_frames.GetValue():
            self.saveDataSet()
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
            self.endFrame.SetValue(endVal-deltaF)
            self.slider.SetValue(newFrame)
            self.OnSliderScroll(event)
        
    def updateSlider(self,event):
        self.slider.SetValue(self.startFrame.GetValue())
        self.OnSliderScroll(event)
    
    def OnSliderScroll(self, event):
        """
        Slider to scroll through the video
        """
        if not self.rev:
            self.currFrame = self.slider.GetValue()
            self.endFrame.SetMax(self.numberFrames-self.currFrame)
            if self.endFrame.GetValue() > (self.numberFrames-self.currFrame):
                self.endFrame.SetValue(self.numberFrames-self.currFrame)
            if hasattr(event,'GetEventCategory'):
                if event.GetEventCategory() == 2 and not (self.endFrame == event.GetEventObject()):
                    self.endFrame.SetValue(self.numberFrames-self.currFrame-1)
                
            self.startFrame.SetValue(self.currFrame)
            if self.move_label.GetValue():
                self.move_label.SetValue(0)
        
        self.update(event)
        
    def labelFrames(self, event):
        """
        Show the DirDialog and ask the user to change the directory where machine labels are stored
        """
        self.move_label.SetValue(0)
        if self.label_frames.GetValue():
            if self.rev:
               dataFilePath = self.curr_h5
               if os.path.isfile(dataFilePath):
                   self.dataFrame.sort_index(inplace=True)
               # self.relativeimagenames = list()
               # self.relativeimagenames.append(self.currFrame)
               oldBodyParts = self.dataFrame.columns.get_level_values(1)
               # print(oldBodyParts)
               _, idx = np.unique(oldBodyParts, return_index=True)
               oldbodyparts2plot =  list(oldBodyParts[np.sort(idx)])
               self.new_bodyparts =  [x for x in self.bodyparts if x not in oldbodyparts2plot ]
               # Checking if user added a new label
               if self.new_bodyparts != []: # i.e. new labels
                   print('New body parts found!')
                   a = np.empty((len(self.currFrame),2,))
                   a[:] = np.nan
                   for bodypart in self.new_bodyparts:
                       index = pd.MultiIndex.from_product([[self.scorer], [bodypart], ['x', 'y']],names=['scorer', 'bodyparts', 'coords'])
                       frame = pd.DataFrame(a, columns = index, index = self.currFrame)
                       self.dataFrame = pd.concat([self.dataFrame, frame],axis=1)          
            else:
                self.Disable
                data_path = Path(self.config_path).parents[0] / 'labeled-data'
                self.label_dirs = [data_path/Path(i.stem) for i in [Path(vp) for vp in self.videos]]
                self.scorer = self.cfg['scorer']
                self.dataFrame = list()
                self.relativeimagenames = list()
                for frm in range(0,self.numberFrames):
                    img_name = 'img'+str(frm).zfill(int(np.ceil(np.log10(self.numberFrames)))) + '.png'
                    self.relativeimagenames.append(img_name)
                    
                for ndx, dirs in enumerate(self.label_dirs):
                    if not os.path.exists(dirs):
                        os.makedirs(dirs)
                    dataFilePath = os.path.join(dirs,'CollectedData_'+self.scorer+'.h5')
                     
                    if os.path.isfile(dataFilePath):
                     # Reading the existing dataset,if already present
                        dataFilePath = os.path.join(dirs,'CollectedData_'+self.scorer+'.h5')
                        self.dataFrame.append(pd.read_hdf(dataFilePath,'df_with_missing'))
                        self.dataFrame[ndx].sort_index(inplace=True)
                    else:
                        a = np.empty((len(self.relativeimagenames),2,))
                        a[:] = np.nan
                        df = None
                        for bodypart in self.bodyparts:
                            index = pd.MultiIndex.from_product([[self.scorer], [bodypart], ['x', 'y']],names=['scorer', 'bodyparts', 'coords'])
                            frame = pd.DataFrame(a, columns = index, index = self.relativeimagenames)
                            df = pd.concat([df, frame],axis=1)
                        self.dataFrame.append(df)
                              
            # Extracting the list of new labels
                    oldBodyParts = self.dataFrame[ndx].columns.get_level_values(1)
                    _, idx = np.unique(oldBodyParts, return_index=True)
                    oldbodyparts2plot =  list(oldBodyParts[np.sort(idx)])
                    self.new_bodyparts =  [x for x in self.bodyparts if x not in oldbodyparts2plot ]
                    # Checking if user added a new label
                    if self.new_bodyparts != []: # i.e. new labels
                        print('New body parts found!')
                        a = np.empty((len(self.relativeimagenames),2,))
                        a[:] = np.nan
                        for bodypart in self.new_bodyparts:
                            index = pd.MultiIndex.from_product([[self.scorer], [bodypart], ['x', 'y']],names=['scorer', 'bodyparts', 'coords'])
                            frame = pd.DataFrame(a, columns = index, index = self.relativeimagenames)
                            self.dataFrame[ndx] = pd.concat([self.dataFrame[ndx], frame],axis=1)           
                             
            self.cidClick = self.canvas.mpl_connect('button_press_event', self.onClick)    
            self.move_label.Enable(True)
            self.omit_label.Enable(True)
            for lab in self.labelselect:
                lab.Enable(True)
            self.stat.Enable(True)
            if self.show_tracking.GetValue():
                self.grab_labels.Enable(True)
                eventChoices = ['Labeled Frame']
                # if len(self.eventListF):
                #     eventChoices = eventChoices.extend(self.fBox.GetItems())
                self.fBox.SetItems(eventChoices)
                self.fBox.SetSelection(0)
                
            self.fPrev.Enable(True)
            self.fNext.Enable(True)
            self.fBox.Enable(True)
            # self.choice_panel.ScrollChildIntoView(self.labelselect[0])
            # self.scrollUnit = self.choice_panel.GetScrollPixelsPerUnit()
    
            self.Enable
            self.update(None)     
            
        else:
            self.move_label.Enable(False)
            self.omit_label.Enable(False)
            for lab in self.labelselect:
                lab.Enable(False)
            self.stat.Enable(False)
            if self.rev or not len(self.eventListF):
                self.fPrev.Enable(False)
                self.fNext.Enable(False)
                self.fBox.Enable(False)
        
            self.saveDataSet()
            self.grab_labels.Enable(False)
            self.update(None)     
                 
    def onClick(self, event):
        self.move_label.SetValue(0)
        if self.label_frames.GetValue():
            self.x1 = event.xdata
            self.y1 = event.ydata
            
            
            for ndx, hax in enumerate(self.axes):
                if self.rev:
                    if self.videoOrder[ndx] in self.image_path:
                        if event.inaxes == hax:
                            for bp in self.bodyparts:
                                x2 = self.dataFrame.loc[self.currFrame][self.scorer, bp, 'x' ]
                                y2 = self.dataFrame.loc[self.currFrame][self.scorer, bp, 'y' ]
                                xydist = np.sqrt((self.x1-x2)**2+(self.y1-y2)**2)
                                if xydist < 5 and not self.auto_grab:
                                    bpndx = self.bodyparts.index(bp)
                                    self.labelselect[0].SetSelection(bpndx)
                            bp = self.labelselect[0].GetString(self.labelselect[0].GetSelection())
                            
                            frame = cv2.imread(self.image_path)
                            if not os.path.isfile(self.image_path):
                                cv2.imwrite(self.image_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                            self.dataFrame.loc[self.currFrame][self.scorer, bp, 'x' ] = self.x1
                            self.dataFrame.loc[self.currFrame][self.scorer, bp, 'y' ] = self.y1
                            self.move_label.SetValue(1)
                            self.currAxis = hax
                            self.newLabelCt+=1
                            self.choice_panel.Scroll(int(self.scroll_unit*self.labelselect[0].GetSelection()),1)
                else:
                    if event.inaxes == hax:
                        for bp in self.bodyparts:
                            x2 = self.dataFrame[ndx].loc[self.relativeimagenames[self.currFrame]][self.scorer, bp, 'x' ]
                            y2 = self.dataFrame[ndx].loc[self.relativeimagenames[self.currFrame]][self.scorer, bp, 'y' ]
                            xydist = np.sqrt((self.x1-x2)**2+(self.y1-y2)**2)
                            if xydist < 5 and not self.auto_grab:
                                bpndx = self.bodyparts.index(bp)
                                self.labelselect[0].SetSelection(bpndx)
                        bp = self.labelselect[0].GetString(self.labelselect[0].GetSelection())
                        
                    
                        img_name = str(self.label_dirs[ndx]) +'/img'+str(self.currFrame).zfill(int(np.ceil(np.log10(self.numberFrames)))) + '.png'
                        if not os.path.isfile(img_name):
                            cv2.imwrite(img_name, cv2.cvtColor(self.frameList[ndx], cv2.COLOR_RGB2BGR))
                        self.dataFrame[ndx].loc[self.relativeimagenames[self.currFrame]][self.scorer, bp, 'x' ] = self.x1
                        self.dataFrame[ndx].loc[self.relativeimagenames[self.currFrame]][self.scorer, bp, 'y' ] = self.y1
                        self.move_label.SetValue(1)
                        self.currAxis = hax
                        self.newLabelCt+=1
                        # print(len(self.bodyparts))
                        self.choice_panel.Scroll(int(self.scroll_unit*self.labelselect[0].GetSelection()),1)
                        
            if self.newLabelCt > 30 and not self.auto_grab:
                self.saveDataSet()
                self.newLabelCt = 0    
            if not self.auto_grab:
                self.update(None)
        else:
            event.Skip()
            
    def reviewMode(self, event):
        if self.review.GetLabel() == 'Review Mode':
            self.rev = True
            # self.curr_labels_path = None
            self.curr_h5 = None
            self.label_dirs = None
            self.reviewFrame = 0

            self.cfg = clara.read_dlc_config(self.config_path)
            self.bodyparts = self.cfg['bodyparts']
            self.scorer = self.cfg['scorer']
            self.colormap = plt.get_cmap(self.cfg['colormap'])
            self.colormap = self.colormap.reversed()
            self.markerSize = 3
            self.alpha = 1
            self.newLabelCt = 0
            self.imFile = []
            self.h5list = []
            
            self.labelPath = os.path.join(os.path.dirname(self.config_path), "labeled-data")
            for root, dirs, files in os.walk(self.labelPath):
                for file in files:
                    if file.lower().endswith('.png'):
                        self.imFile.append(os.path.join(root,file))
                        self.h5list.append(os.path.join(root, "CollectedData_" + self.scorer + ".h5"))
            
            data = [{'h5': h5, 'img': img} for h5, img in zip(self.h5list, self.imFile)]
            self.revdf = pd.DataFrame(data)
            self.reviewCt = len(self.revdf)
            self.currFrame = self.revdf.iloc[self.reviewFrame]['img']
            # print(f'rev master Table: {self.revdf}')
            self.review.SetLabel("Disable")
                
            
            # from load_vids
            
            # clearing axes from previously loaded video (or review set)
            self.figure,self.axes,self.canvas = self.image_panel.getfigure()
            if len(self.axes[0].get_children()) > 0:
                for hax in self.axes:
                    hax.clear()
                self.figure.canvas.draw()
            
            # load config and get bodypart list
            self.user_cfg = clara.read_config()
            key_list = list()
            # print(self.user_cfg)
            for cat in self.user_cfg.keys():
                key_list.append(cat)
            self.videoOrder = list()
            for key in key_list:
                if 'cam' in key:
                    self.videoOrder.append(self.user_cfg[key]['nickname'])
      
            self.cropPts = list()
            if isinstance(self.bodyparts,list):
                parts = self.bodyparts
            else:
                parts = list()
                self.categories = list()
                for cat in self.bodyparts.keys():
                    self.categories.append(cat)
                for key in self.categories:
                    for ptname in self.bodyparts[key]:
                        parts.append(ptname)
            self.bodyparts = parts
         
            # prepare axes for update function
            self.im = list()
            self.circle = list()
            # self.imgList = list()
            # make list
            self.image_path = self.revdf.iloc[self.reviewFrame]['img']
            frame = cv2.imread(self.image_path)
            self.norm,self.colorIndex = self.image_panel.getColorIndices(frame, self.bodyparts)
                
            for vndx, vo in enumerate(self.videoOrder):
                # load first image for reference
                frmW = np.shape(frame)[1]
                frmH = np.shape(frame)[0]
                cpt = [0,int(frmW),0,int(frmH)]
                self.cropPts.append(cpt)
                if not vo in self.image_path:
                    frame = np.zeros(np.shape(frame))
                self.im.append(self.axes[vndx].imshow(frame)) # creates image object within axes
                
                self.points = [0,0,1.0]
                circleH = list()
                for bpndx, bp in enumerate(self.bodyparts):
                    if bp == 'FRside':
                        color = [0,1,1]
                    elif bp == 'HRside':
                        color = [1,0,1]
                    else:
                        color = self.colormap(self.norm(self.colorIndex[bpndx]))
                    circle = [patches.Circle((self.points[0], self.points[1]), radius=self.markerSize,
                                              linewidth=2, fc = color, alpha=0.0)]
                    circleH.append(self.axes[vndx].add_patch(circle[0]))
                self.circle.append(circleH)
      
                circle = [patches.Circle((0, 0), radius=5, linewidth = 2, fc=[1,1,1], alpha=0.0)]
                
            if len(self.bodyparts)!=len(set(self.bodyparts)):
                print("Error - bodyparts must have unique labels! Please choose unique bodyparts in config.yaml file and try again.")

            cppos = self.choice_panel.GetPosition()
            cprect = self.choice_panel.GetRect()
            cpsize = self.choice_panel.GetSize()
            self.choice_panel.replaceRadio()
            self.labelselect, self.choice_box = self.choice_panel.addRadioButtons(self.bodyparts,self.guiDim)
            self.choice_panel.SetPosition(cppos)
            self.choice_panel.SetRect(cprect)
            self.choice_panel.SetSize(cpsize)
            # self.choice_panel.SetupScrolling()
            scroll_unit = self.choice_panel.GetScrollPixelsPerUnit()
            box_size = self.choice_box.GetSize()
            self.scroll_unit = box_size[0]/len(self.bodyparts)/scroll_unit[0]
            # print(self.scroll_unit)
            for rad in self.labelselect:
                rad.Bind(wx.EVT_RADIOBOX, self.resetFocus)
            self.reviewFrm() #call to load h5, current image, and update plot
        else:
            self.move_label.Enable(False)
            self.omit_label.Enable(False)
            for lab in self.labelselect:
                lab.Enable(False)
            self.stat.Enable(False)
            if not self.rev: 
                self.fPrev.Enable(False)
                self.fNext.Enable(False)
                self.fBox.Enable(False)
            
            self.saveDataSet()
            self.grab_labels.Enable(False)
            # self.update(None)
            self.label_frames.SetValue(False)
            self.labelFrames(event = None)
            self.rev = False
            self.review.SetLabel("Review Mode")
                  
    def reviewFrm(self):
        # index into master table
        if (self.curr_h5 == None) or not (self.curr_h5 == self.revdf.iloc[self.reviewFrame]['h5']):
            if self.label_dirs is not None:
                self.saveDataSet()
            self.curr_h5 = self.revdf.iloc[self.reviewFrame]['h5']
            self.dataFrame = pd.read_hdf(Path(os.path.join(self.revdf.iloc[self.reviewFrame]['h5'])),'df_with_missing')
            self.label_dirs = [self.curr_h5, None] # or self.label_dirs = [None, self.curr]
            
            # print(self.revdf.iloc[self.reviewFrame]['h5'])
           
            self.label_frames.SetValue(False)
            self.labelFrames(event = None)
            self.label_frames.SetValue(True)
            self.labelFrames(event = None)
            # self.labelFrames(AcceleratorTable = None)
        self.image_path = self.revdf.iloc[self.reviewFrame]['img']
        self.currFrame = os.path.basename(self.image_path)
        # print(f'currframe: {self.currFrame}     im path: {self.image_path}')
        self.update(event = None)
            
    def update(self,event):
        """
        Updates the image with the current slider index
        """
        for ndx, im in enumerate(self.im):
            if not self.rev:
                self.vid[ndx].set(1,self.currFrame) 
                ret, frame = self.vid[ndx].read()
                frame = img_as_ubyte(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                cpt = self.cropPts[ndx]
                self.frameList[ndx] = frame[cpt[2]:cpt[2]+cpt[3],cpt[0]:cpt[0]+cpt[1]]
                im.set_data(frame)
            else:
                frame = cv2.imread(self.image_path)
                cpt = self.cropPts[ndx]
                if self.videoOrder[ndx] not in self.image_path:
                    frame = np.zeros(np.shape(frame))
                frame = frame[cpt[2]:cpt[2]+cpt[3],cpt[0]:cpt[0]+cpt[1]]
                im.set_data(frame)
            
            if self.show_tracking.GetValue() or self.label_frames.GetValue():
                for bp in self.bodyparts:
                    bpndx = self.bodyparts.index(bp)
                    self.circle[ndx][bpndx].set_alpha(0.0)
                
            if self.show_tracking.GetValue():
                message = ''
                if isinstance(self.cfg['bodyparts'],list):
                    parts = self.bodyparts
                    for ptname in parts:
                        if not ptname in self.bpInDf: #?
                            continue
                        bpndx = self.bodyparts.index(ptname)
                        bp_test = self.df_likelihood[ndx][bpndx,self.currFrame]
                        message+= '%s... %s\n' % (ptname,f'{bp_test:.6f}')
                        if bp_test > 0.9:
                            self.drawCirc(ndx,bpndx,False)
                else:
                    for key in self.categories:
                        testlist = list()
                        ndxlist = list()
                        for ptname in self.cfg['bodyparts'][key]:
                            bpndx = self.bodyparts.index(ptname)
                            ndxlist.append(bpndx)
                            bp_test = self.df_likelihood[ndx][bpndx,self.currFrame]
                            testlist.append(bp_test)
                            message+= '%s... %s\n' % (ptname,f'{bp_test:.6f}')
                            if key == 'Other' and bp_test > 0.9:
                                drawndx = ndxlist[np.argmax(testlist)]
                                self.drawCirc(ndx,drawndx,False)
                        if np.amax(testlist) > 0.9 and key != 'Other': 
                            drawndx = ndxlist[np.argmax(testlist)]
                            self.drawCirc(ndx,drawndx,False)
                        
                self.textH[ndx].set_text(message)
                
            if self.label_frames.GetValue():
                try:
                    for bpndx, bp in enumerate(self.bodyparts):
                        if not self.rev:
                            hxB = self.dataFrame[ndx].loc[self.relativeimagenames[self.currFrame]][self.scorer, bp, 'x' ]
                            hyB = self.dataFrame[ndx].loc[self.relativeimagenames[self.currFrame]][self.scorer, bp, 'y' ]
                            if not np.isnan(hxB):
                                cpt = self.cropPts[ndx]
                                self.points = [int(hxB), int(hyB), 1.0]
                                self.drawCirc(ndx,bpndx,True)
                        elif self.videoOrder[ndx] in self.image_path:
                            hxB = self.dataFrame.loc[self.currFrame][self.scorer, bp, 'x' ]
                            hyB = self.dataFrame.loc[self.currFrame][self.scorer, bp, 'y' ]
                            
                            if not np.isnan(hxB):
                                # print(f'BP: {bp}    X: {hxB}    Y: {hyB}')
                                cpt = self.cropPts[ndx]
                                self.points = [int(hxB), int(hyB), 1.0]
                                self.drawCirc(ndx,bpndx,True)
                except:
                    pass
                        
        self.figure.canvas.draw()
            
    def jumpFrame(self, event):
        self.Disable
        if self.rev and self.fPrev == event.GetEventObject():
            self.reviewFrame -= 1
            if self.reviewFrame < 0:
                self.reviewFrame = self.reviewCt-1
        elif self.rev:
            self.reviewFrame += 1
            if self.reviewFrame > self.reviewCt-1:
                self.reviewFrame = 0
        if self.rev:
            self.reviewFrm()
            newFrame = None #FLAG
        else:
            newFrame = self.currFrame
            nc = self.fBox.GetString(self.fBox.GetSelection())
            if nc == 'Labeled Frame':
                if self.fPrev == event.GetEventObject():
                    prevFrm = list()
                    for ndx in range(0,len(self.axes)):
                        df = np.where(np.asarray(self.dataFrame[ndx].count(1))[:self.currFrame-1] > 0)
                        if not len(df[0]):
                            prevFrm.append(self.currFrame-1)
                        else:
                            prevFrm.append(int(np.amax(df[0])))
                    newFrame = np.amax(prevFrm)
                else:
                    nextFrm = list()
                    for ndx in range(0,len(self.axes)):
                        df = np.where(np.asarray(self.dataFrame[ndx].count(1))[self.currFrame+1:] > 0)
                        if len(df[0]):
                            nextFrm.append(int(np.amin(df[0]))+self.currFrame+1)
                    if not len(nextFrm):
                        newFrame = self.currFrame+1
                    else:
                        newFrame = np.amin(nextFrm)
            else:
                if len(self.eventListN):
                    subndx = [i for i in range(len(self.eventListN)) if self.eventListN[i] == nc]
                    subFrmList = self.eventListF[subndx]
                    if self.fNext == event.GetEventObject():
                        newFrame = subFrmList[np.argmax(subFrmList > self.currFrame)]
                    else:
                        newFrame = subFrmList[np.argmax(subFrmList < self.currFrame)]
                else:
                    print('No Reaching Data Available')
            if newFrame >= self.numberFrames:
                newFrame = self.currFrame
        self.Enable
        if newFrame:
            self.slider.SetValue(newFrame)
            self.OnSliderScroll(event)
#        for ndx in range(0,len(self.axes)):
#            img_name = str(self.label_dirs[ndx]) +'/img'+str(self.currFrame).zfill(int(np.ceil(np.log10(self.numberFrames)))) + '.png'
#            cv2.imwrite(img_name, cv2.cvtColor(self.frameList[ndx], cv2.COLOR_RGB2BGR))   
    
    def drawCirc(self, ndx, bpndx, isfortraining):
        if not isfortraining:
            self.points = [int(self.df_x[ndx][bpndx,self.currFrame]),int(self.df_y[ndx][bpndx,self.currFrame]),1.0]
        cpt = self.cropPts[ndx]
        self.points[0] = self.points[0]+cpt[0]
        self.points[1] = self.points[1]+cpt[2]
        self.circle[ndx][bpndx].set_center(self.points)
        self.circle[ndx][bpndx].set_alpha(self.alpha)
        self.circle[ndx][bpndx].set_edgecolor([0,0,0])
        if isfortraining:
            self.circle[ndx][bpndx].set_edgecolor([1,1,1])
                    
    def trainNetwork(self,event):
        clara.create_training_dataset_CLARA(self.config_path,num_shuffles=1)
        
    def analyzeVids(self,event):
        for ndx,v in enumerate(self.videos):
            cpt = self.cropPts[ndx]
            crp = [cpt[0],cpt[0]+cpt[1],cpt[2],cpt[2]+cpt[3]]
            clara.analyze_videos_CLARA(self.config_path, [v], crp)
            
            
    def grabFrame(self,event):
        experimenter = self.users.GetStringSelection()
        startDir = os.path.join(str(Path.home()),'Documents')
        grabDir = os.path.join(startDir,experimenter,'SavedFrames')
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
        startDir = os.path.join(str(Path.home()),'Documents')
        base_dir = os.path.join(startDir,'DemoVids')
        if not os.path.exists(base_dir):
                os.makedirs(base_dir)
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