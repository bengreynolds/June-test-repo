# -*- coding: utf-8 -*-
"""
Created on Wed Feb  7 13:39:05 2024

@author: reynoben
"""

import os
import shutil


config_path = r'C:\Users\reynoben\Documents\Reach2P-christie-2023-12-05\config.yaml'
root_path = "Y:\ChristieLab\\Data\\MSP_Z\\Reach_Training"
cutoff_date = "20230815"

for foldername in os.listdir(root_path):
    if foldername.isdigit() and len(foldername) == 8 and foldername >= cutoff_date:
        folder_path = os.path.join(root_path, foldername)
        christie2P = os.path.join(folder_path, 'christie2P')
        if os.path.exists(christie2P):
            for dirpath, dirnames, filenames in os.walk(christie2P):
                for dirname in dirnames:
                    if dirname.startswith("session") and dirname[7:].isdigit():
                        session_path = os.path.join(dirpath, dirname)
                        session_files = os.listdir(session_path)
                        has_264 = any(filename.endswith('_264.mp4') for filename in session_files)
                        has_no_0000 = all('0000.mp4' not in filename for filename in session_files)
                        if has_264 and has_no_0000:                            
                            print(f'{christie2P}{dirname}')
                            for filename in session_files:
                                if filename.endswith('_264.mp4'):
                                    original_path = os.path.join(session_path, filename)
                                    new_name = filename.replace("_264", "")
                                    new_path = os.path.join(session_path, new_name)
                                    shutil.copy2(original_path, new_path)
                                    os.remove(original_path)



