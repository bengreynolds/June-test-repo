# -*- coding: utf-8 -*-
"""
Created on Tue Jan 16 16:15:29 2024

@author: reynoben
"""
import numpy as np
import pandas as pd
import os
from scipy.signal import savgol_coeffs, butter, filtfilt
import multiCam_DLC_utils_v2 as clara
import glob

#extract tracking data from H5 file 
def extract_tracking_data(session, vid_tag, dlc_seg):
    parts = ['Hand', 'Pellet']
    coordinates = ['y', 'z', 'yz likelihood', 'x', 'o', 'x likelihood']
    columns = pd.MultiIndex.from_product([parts, coordinates], names=['parts', 'coordinates'])
    newdf = pd.DataFrame(columns=columns)
    
    mp4_list = os.path.join(session, '*' + vid_tag)
    videoList = glob.glob(mp4_list)
    user_cfg = clara.read_config()
    key_list = list()
    video_paths = list()
    for cat in user_cfg.keys():
        key_list.append(cat)
    videoOrder = list()
    for key in key_list:
        if 'cam' in key:
            videoOrder.append(user_cfg[key]['nickname'])
    for key in videoOrder:
        for video in videoList:
            if key in video:
                video_paths.append(video)
                break
    if not len(video_paths):
        return newdf
    df_list = list()
    df_len = list() 
    for i, video_path in enumerate(video_paths):
        vid_dir, vid_name_raw = os.path.split(video_path)
        vid_name_raw, vid_ext = os.path.splitext(vid_name_raw)
        h5_file_path = os.path.join(vid_dir, vid_name_raw + dlc_seg + '.h5')
        if not os.path.isfile(h5_file_path):
            return newdf
        df = pd.read_hdf(h5_file_path)
        df_list.append(df)
        df_len.append(len(df))
        
    target_len = max(df_len)
    newdf = pd.DataFrame(columns=columns, index=range(target_len))
    
    for i, video_path in enumerate(video_paths):
        df = df_list[i]
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
        y2keep = y_array[row_index, col_index]
        
        if i == 0:
            # For the first video (columns: y, z, yz likelihood)
            newdf.loc[np.arange(len(df)), ('Hand', 'y')] = x2keep
            newdf.loc[np.arange(len(df)), ('Hand', 'z')] = y2keep
            newdf.loc[np.arange(len(df)), ('Hand', 'yz likelihood')] = p2keep
            newdf.loc[np.arange(len(df)), ('Pellet', 'y')] = df[(dlc_seg, 'Pellet', 'x')].values
            newdf.loc[np.arange(len(df)), ('Pellet', 'z')] = df[(dlc_seg, 'Pellet', 'y')].values
            newdf.loc[np.arange(len(df)), ('Pellet', 'yz likelihood')] = df[(dlc_seg, 'Pellet', 'likelihood')]
    
        elif i == 1:
            # For the second video (columns: x, x likelihood)
            newdf.loc[np.arange(len(df)), ('Hand', 'x')] = x2keep
            newdf.loc[np.arange(len(df)), ('Hand', 'o')] = y2keep
            newdf.loc[np.arange(len(df)), ('Hand', 'x likelihood')] = p2keep
            newdf.loc[np.arange(len(df)), ('Pellet', 'x')] = df[(dlc_seg, 'Pellet', 'x')].values
            newdf.loc[np.arange(len(df)), ('Pellet', 'o')] = df[(dlc_seg, 'Pellet', 'y')].values
            newdf.loc[np.arange(len(df)), ('Pellet', 'x likelihood')] = df[(dlc_seg, 'Pellet', 'likelihood')].values
  
    return newdf

def get_coeffs():
    # Savitzky-Golay Smoothing filter parameters
    window_length = 9
    poly_order = 3
    # Obtain Savitzky-Golay filter coefficients
    coeffs = savgol_coeffs(window_length, poly_order)
    
    return coeffs

def get_frame_rate(video_path):
    frame_rate = None
    # Extract relevant information from video_path
    vid_name_base, vid_dir = get_vid_name_base(video_path)
    frame_rate_file = os.path.join(vid_dir, vid_name_base + '_userdata_copy.yaml')
    if os.path.isfile(frame_rate_file):
        # Read frame rate from userdata_copy.yaml
        with open(frame_rate_file, 'r') as file:
            yaml_content = file.read()
        if 'framerate' in yaml_content:
            frame_rate_string = yaml_content.split('framerate:')[1].split()[0]
            frame_rate = int(''.join(filter(str.isdigit, frame_rate_string)))
    return frame_rate

#Filter raw tracking data 
def filter_data(session, vid_tag, dlc_seg):
    mp4_list = os.path.join(session, '*' + vid_tag)
    videoList = glob.glob(mp4_list)
    user_cfg = clara.read_config()
    key_list = list()
    video_paths = list()
    for cat in user_cfg.keys():
        key_list.append(cat)
    videoOrder = list()
    for key in key_list:
        if 'cam' in key:
            videoOrder.append(user_cfg[key]['nickname'])
    for key in videoOrder:
        for video in videoList:
            if key in video:
                video_paths.append(video)
                break
    if not len(video_paths):
        print('No videos found for %s' % session)
        return
    
    vid_name_base, vid_dir = get_vid_name_base(video_paths[0])
    # Initialize filt_data DataFrame
    parts = ['Hand', 'Pellet']
    data = ['y', 'y_filt', 'z', 'z_filt', 'yz_likelihood', 'x', 'x_filt', 'x_likelihood', 'distance', 'speed',
            'speed_filt']
    columns = pd.MultiIndex.from_product([parts, data], names=['parts', 'data'])
    filt_data = pd.DataFrame(columns=columns)

 
    # Extract reach data using DLC and apply conversions
    df = extract_tracking_data(session, vid_tag, dlc_seg)
    if np.shape(df)[0] == 0:
        print('No tracking available for %s' % vid_name_base)
        return
    
    # df_pixel = df.copy()
    side_conv = 0.1129277459460412
    front_conv = 0.19450780444855226
    df[[('Hand', 'y'), ('Hand', 'z'), ('Pellet', 'y'), ('Pellet', 'z')]] *= side_conv
    df[[('Pellet', 'x'), ('Hand', 'x')]] *= front_conv

    # Butterworth filter settings
    frame_rate = get_frame_rate(video_paths[0])
    if frame_rate == None:
        print('no frame rate available for %s' % vid_name_base)
        return
    
    cutoff_freq = 50  # Hz
    nyquist_freq = 0.5 * frame_rate
    normalized_cutoff_freq = cutoff_freq / nyquist_freq
    filter_order = 5
    # Create Butterworth filter coefficients
    b, a = butter(filter_order, normalized_cutoff_freq, btype='low', analog=False, output='ba')

    coeffs = get_coeffs()    

    # Grab bodyparts for indexing
    bodyparts = df.columns.get_level_values(0).tolist()[0::5]
    # Allocate empty arrays
    frm_count = np.shape(df)[0]
    df_yzlikelihood = np.empty((len(bodyparts), frm_count))
    df_xlikelihood = np.empty((len(bodyparts), frm_count))
    df_x = np.empty((len(bodyparts), frm_count))
    df_y = np.empty((len(bodyparts), frm_count))
    df_z = np.zeros((len(bodyparts), frm_count))
    x_filt = np.zeros((len(bodyparts), frm_count))
    y_filt = np.zeros((len(bodyparts), frm_count))
    z_filt = np.zeros((len(bodyparts), frm_count))
    speed = np.zeros((len(bodyparts), frm_count))
    speed_filt = np.zeros((len(bodyparts), frm_count))
    distance = np.zeros((len(bodyparts), frm_count))
    interp_counts_x = np.zeros((len(bodyparts),))
    interp_counts_yz = np.zeros((len(bodyparts),))
    full_frm_ref = np.arange(frm_count)

    for bpindex, bp in enumerate(bodyparts):
        df_yzlikelihood[bpindex, :] = df[bp]['yz likelihood'].values
        df_xlikelihood[bpindex, :] = df[bp]['x likelihood'].values
        df_x[bpindex, :] = df[bp]['x'].values
        df_y[bpindex, :] = df[bp]['y'].values
        df_z[bpindex, :] = df[bp]['z'].values

        # Find indices of low-confidence values
        df_yzlikelihood[bpindex, 1] = 1
        df_xlikelihood[bpindex, 1] = 1
        df_yzlikelihood[bpindex, -1] = 1
        df_xlikelihood[bpindex, -1] = 1

        low_confidence_indices_x = df_xlikelihood[bpindex, :] < 0.9  # confidence threshold
        low_confidence_indices_yz = df_yzlikelihood[bpindex, :] < 0.9  # confidence threshold
        interp_counts_x[bpindex] = sum(low_confidence_indices_x)
        interp_counts_yz[bpindex] = sum(low_confidence_indices_yz)

        # Linearly interpolate low-confidence values if enough high-confidence values are identified
        if (interp_counts_x[bpindex] >= frm_count - 2) or (interp_counts_yz[bpindex] >= frm_count - 2):
            df_x[bpindex, :] = np.zeros((frm_count,))
            df_y[bpindex, :] = np.zeros((frm_count,))
            df_z[bpindex, :] = np.zeros((frm_count,))
        else:
            # Interpolation
            df_x[bpindex, :] = np.interp(full_frm_ref, full_frm_ref[~low_confidence_indices_x],
                                         df_x[bpindex, ~low_confidence_indices_x])
            df_y[bpindex, :] = np.interp(full_frm_ref, full_frm_ref[~low_confidence_indices_yz],
                                         df_y[bpindex, ~low_confidence_indices_yz])
            df_z[bpindex, :] = np.interp(full_frm_ref, full_frm_ref[~low_confidence_indices_yz],
                                         df_z[bpindex, ~low_confidence_indices_yz])

        df_x[bpindex, :][np.where(np.isnan(df_x[bpindex, :]))] = 0
        df_y[bpindex, :][np.where(np.isnan(df_y[bpindex, :]))] = 0
        df_z[bpindex, :][np.where(np.isnan(df_z[bpindex, :]))] = 0

        x_filt[bpindex, :] = filtfilt(b, a, df_x[bpindex, :])
        y_filt[bpindex, :] = filtfilt(b, a, df_y[bpindex, :])
        z_filt[bpindex, :] = filtfilt(b, a, df_z[bpindex, :])

        # Calculate distance and speed
        distA = np.sqrt(np.diff(x_filt[bpindex, :]) ** 2 + np.diff(y_filt[bpindex, :]) ** 2 +
                        np.diff(z_filt[bpindex, :]) ** 2)  # calculate distance
        distA = np.concatenate(([0], distA))  # adjust length by adding a zero to the beginning
        speedA = distA * (frame_rate / 1000)  # calculate speed in pixels per ms and convert to mm/ms

        # add speed and dist vectors to the pre-allocated arrays
        distance[bpindex, :] = distA
        speed[bpindex, :] = speedA

        # Apply filter using filtfilt for smoothing
        speed_filt[bpindex, :] = filtfilt(coeffs, [1], speed[bpindex, :])

        filt_data.loc[:, (bp, 'x')] = df_x[bpindex, :]
        filt_data.loc[:, (bp, 'y')] = df_y[bpindex, :]
        filt_data.loc[:, (bp, 'z')] = df_z[bpindex, :]
        filt_data.loc[:, (bp, 'x_filt')] = x_filt[bpindex, :]
        filt_data.loc[:, (bp, 'y_filt')] = y_filt[bpindex, :]
        filt_data.loc[:, (bp, 'z_filt')] = z_filt[bpindex, :]
        filt_data.loc[:, (bp, 'yz_likelihood')] = df_yzlikelihood[bpindex, :]
        filt_data.loc[:, (bp, 'x_likelihood')] = df_xlikelihood[bpindex, :]
        filt_data.loc[:, (bp, 'distance')] = distance[bpindex, :]
        filt_data.loc[:, (bp, 'speed')] = speed[bpindex, :]
        filt_data.loc[:, (bp, 'speed_filt')] = speed_filt[bpindex, :]
    
    
    filt_data_path = os.path.join(vid_dir, vid_name_base + 'filt_data.h5')
    if os.path.isfile(filt_data_path):
        os.remove(filt_data_path)
        
    filt_data_path = os.path.join(vid_dir, vid_name_base + '_filt_data.h5')
    filt_data.to_hdf(filt_data_path,'df_with_missing',format='table', mode='w')
    return filt_data
    
def get_vid_name_base(video_path):
    vid_dir, vid_name = os.path.split(video_path)
    vid_name, vid_ext = os.path.splitext(vid_name)
    txtparts = vid_name.split('_')
    vid_name_base = txtparts[0] + '_' + txtparts[1] + '_' + txtparts[2]
    return vid_name_base, vid_dir

#Find Reach Events w logical tests (FSM)
def find_reach_events(session, vid_tag):
    mp4_list = os.path.join(session, '*' + vid_tag)
    # print(mp4_list)
    videoList = glob.glob(mp4_list)
    user_cfg = clara.read_config()
    key_list = list()
    video_paths = list()
    for cat in user_cfg.keys():
        key_list.append(cat)
    videoOrder = list()
    for key in key_list:
        if 'cam' in key:
            videoOrder.append(user_cfg[key]['nickname'])
    for key in videoOrder:
        for video in videoList:
            if key in video:
                video_paths.append(video)
                break
    if not len(video_paths):
        print('No videos found for %s' % session)
        return
    
    debug = False
    vid_name_base, vid_dir = get_vid_name_base(video_paths[0])
    frame_list_file = os.path.join(vid_dir, vid_name_base + '_frontCam_events.txt')
    if not os.path.isfile(frame_list_file):
        frame_list_file = os.path.join(vid_dir, vid_name_base + '_events.txt')
        if not os.path.isfile(frame_list_file):
            print('No events file available for %s' % vid_name_base)
        
    # Read pellet_delivery Frames from .txt file
    frame_list = []
    with open(frame_list_file, 'r') as file:
        for line in file:
            if "pellet_delivery" in line:
                try:
                    frame_number = int(line.split("pellet_delivery")[1].strip())
                    frame_list.append(frame_number)
                except ValueError:
                    print(f"Warning: Skipped Line '{line.strip()}' Because No Frame Present.")

    filt_data_path = os.path.join(vid_dir, vid_name_base + '_filt_data.h5')
    if not os.path.isfile(filt_data_path):
        print('No filtered data available for %s' % vid_name_base)
    filt_data = pd.read_hdf(filt_data_path,'df_with_missing')
    coeffs = get_coeffs()    
    frame_rate = get_frame_rate(video_paths[0])
    if frame_rate == None:
        print('No frame rate available for %s' % vid_name_base)
        return
    
    frm_count = np.shape(filt_data)[0]
    batch_frm = 10
    batch_dist = 5
    batch_drop = 25
    batch_speed = 5
    batch_stall = 25
    reach_init_speed = -0.025
    pellet_drop_speed = 0.275 #0.225
    pellet_drop_dist = -5
    dist_thresh_end = 5
    confidence = 0.9
    reach_events = []
    
    for frmindex, start_frame in enumerate(frame_list):
        #define dist and velo for each reach sequence (changes according to start_frame)
        if frmindex < len(frame_list)-1:
            search_end = frame_list[frmindex+1]-batch_frm-1
        else:
            search_end = frm_count
        pellet_was_detected = False
        search_list = np.arange(start_frame+20,search_end)
        for sfp in search_list.tolist():
            # testA = filt_data['Pellet']['x_likelihood'][sfp] > confidence
            # testB = filt_data['Pellet']['yz_likelihood'][sfp] > confidence
            testA = np.sum(filt_data['Pellet']['x_likelihood'][sfp:sfp+batch_frm] > confidence)/batch_frm > 0.75 # test if pellet is there 
            testB = np.sum(filt_data['Pellet']['yz_likelihood'][sfp:sfp+batch_frm] > confidence)/batch_frm > 0.75
            
            if testA and testB:
                distance_p = np.sqrt((filt_data['Pellet']['x_filt'].values-filt_data['Pellet']['x_filt'].values[sfp])**2 + (filt_data['Pellet']['y_filt'].values-filt_data['Pellet']['y_filt'].values[sfp])**2 + (filt_data['Pellet']['z_filt'].values-filt_data['Pellet']['z_filt'].values[sfp])**2)
                distance_hvpp = np.sqrt((filt_data['Hand']['x_filt'].values-filt_data['Pellet']['x_filt'].values[sfp])**2 + (filt_data['Hand']['y_filt'].values-filt_data['Pellet']['y_filt'].values[sfp])**2 + (filt_data['Hand']['z_filt'].values-filt_data['Pellet']['z_filt'].values[sfp])**2)
                Z_dist_h = filt_data['Hand']['z_filt'].values-filt_data['Pellet']['z_filt'].values[sfp]
                Z_dist_p = filt_data['Pellet']['z_filt'].values[sfp]-filt_data['Pellet']['z_filt'].values
                Y_dist_p = filt_data['Pellet']['y_filt'].values[sfp]-filt_data['Pellet']['y_filt'].values
                
                pellet_was_detected = True
                break
        if not pellet_was_detected:
            print('Pellet origin not found for %s at %d' % (vid_name_base, start_frame))
            continue
        velocity_h = np.diff(distance_hvpp)*(frame_rate/1000)
        velocity_h_filt = filtfilt(coeffs, [1], velocity_h)
        
        search_status = 1
        food_was_dropped = False
        frame = sfp-20
        pellet_detected = False
        while frame < frm_count - batch_frm:
            # test if we reached the next pellet placement 
            if frmindex < len(frame_list)-1 and frame >= frame_list[frmindex+1]: 
                if search_status == 1:
                    if debug:
                        if pellet_detected == False:
                            print('No pellet detected')
                        else:
                            print('No (additional) reach detected')
                break
            testA = np.sum(filt_data['Pellet']['x_likelihood'][frame:frame+batch_frm] > confidence)/batch_frm > 0.75 # test if pellet is there 
            testB = np.sum(filt_data['Pellet']['yz_likelihood'][frame:frame+batch_frm] > confidence)/batch_frm > 0.75
            if testA and testB: 
                pellet_detected = True
            else:
                pellet_detected = False
            
            if search_status == 1:                  # search for a reach initiation
                if pellet_detected == True:
                    testD = np.sum(filt_data['Hand']['x_likelihood'][frame:frame+batch_frm] > confidence)/batch_frm > 0.75 # test if hand is there
                    testE = np.sum(filt_data['Hand']['yz_likelihood'][frame:frame+batch_frm] > confidence)/batch_frm > 0.75
                    if testD and testE:                        
                        testA = Z_dist_h[frame] > -4 
                        testB = np.mean(velocity_h_filt[frame:frame+batch_speed]) < reach_init_speed
                        
                        if testA and testB: 
                            if debug:
                                print('reach began at frame %d!' % frame)
                            reach_events.append(('reachInit', frame))
                            search_status = 2
                            food_was_dropped = False
            
            elif search_status == 2:                #search for reach max
                if np.any(filt_data['Pellet']['speed_filt'][frame:frame + batch_drop] > pellet_drop_speed):
                    food_was_dropped = True  
                if np.any(Y_dist_p[frame:frame+batch_drop] < -3):
                    food_was_dropped = True 
                if np.any(Z_dist_p[frame:frame+batch_drop] < pellet_drop_dist): #food dropped if pellet is too low - 
                    z_dist_indices = np.where(Z_dist_p[frame:frame+batch_drop] < pellet_drop_dist)
                    testD = np.any(filt_data['Pellet']['yz_likelihood'][frame:frame+batch_drop].iloc[z_dist_indices] > confidence) 
                    if testD:
                        food_was_dropped = True
                testB = np.mean(velocity_h_filt[frame:frame + batch_speed]) > 0.0
                if testB:
                    if debug:
                        print('reach max at frame %d!' % int(frame+3))
                    reach_events.append(('reachMax', int(frame+3)))
                    search_status = 3
                    frame += 3
            
            elif search_status == 3:                # search for reach end 
                keep_looking = True
                testA = np.mean(distance_hvpp[frame:frame + batch_dist]) > dist_thresh_end  # test if hand is far enough away and moving away from pellet             
                testB = np.mean(velocity_h_filt[frame:frame+batch_speed]) > 0
                testC = np.mean(velocity_h_filt[frame:frame+batch_speed]) < reach_init_speed
                testD = np.allclose(np.mean(distance_hvpp[frame:frame+batch_stall]), distance_hvpp[frame], atol = 2)
                testE = np.isclose(np.mean(filt_data['Hand']['speed_filt'][frame:frame + batch_stall]), 0, atol = 0.025) 
                testF = np.all(distance_hvpp[frame:frame + batch_stall] < 6) #4

                if np.any(filt_data['Pellet']['speed_filt'][frame:frame + batch_drop] > pellet_drop_speed):
                    food_was_dropped = True 
                if np.any(Y_dist_p[frame:frame+batch_drop] < -3):
                    food_was_dropped = True 
                if np.any(Z_dist_p[frame:frame+batch_drop] < pellet_drop_dist): #food dropped if pellet is too low
                    z_dist_indices = np.where(Z_dist_p[frame:frame+batch_drop] < pellet_drop_dist)
                    testD = np.any(filt_data['Pellet']['yz_likelihood'][frame:frame+batch_drop].iloc[z_dist_indices] > confidence)
                    if testD:
                        food_was_dropped = True
                      
                if testA and testC and not food_was_dropped: #and pellet_detected: 
                    if debug:
                        print('reach ended at frame %d!: NEW REACH' % int(frame-1))
                    reach_events.append(('reachEnd_missed', int(frame-1)))
                    search_status = 1
                
                elif testD and testE and testF: # and not food_was_dropped: 
                    if debug: 
                      print('reach stalled')
                    reach_events.append(('reachEnd_stalled', int(frame+3)))
                    keep_looking = False
             
                elif testA and testB:
                    pTest = np.mean(distance_p[frame:frame+batch_frm]) < 2 # pellet wasnt dropped and still in original position 
                    if food_was_dropped == True:
                        if debug:
                            print ('reach ended at frame %d!: DROPPED' % int(frame+2))
                        reach_events.append(('reachEnd_dropped', int(frame+2)))
                        keep_looking = False
                    elif pellet_detected == True and pTest:
                        if debug:
                            print('reach ended at frame %d!: MISSED' % int(frame+2))
                        reach_events.append(('reachEnd_missed', int(frame+2)))
                        frame += 2
                        search_status = 1  
                    else:
                        if debug:
                            print('reach ended at frame %d!: GRABBED' % int(frame+2)) #alt: pellet position close to hand(within some threshold)
                        reach_events.append(('reachEnd_grabbed', int(frame+2)))
                        keep_looking = False 
                # start_query = reach_events[-2][1]
                # testX = was it too long
                # testY = was it too long
                # testZ = did the hand get close enough to food origin
                # if testX or testY or testZ:
                    # reach_events.pop()
                    # reach_events.pop()
                if keep_looking == False:
                    break
            frame += 1
            
    
    # # Write all reach events to .txt file 
    vid_dir, vid_name = os.path.split(video_paths[0])            
    fileID = '_'.join(vid_dir.split('\\')[-3:])
    file_path = os.path.join(vid_dir, f'{fileID}_Ordered_Reach_Events.txt') 
    with open(file_path, 'w') as file:
        for event in reach_events:
            file.write(f"{event[0]}\t{event[1]}\n")
        

#%% TEST

# video_paths = [r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230821\christie2P\session005\20230821_christie2P_session005_sideCam-0000_264.mp4',
#                 r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230821\christie2P\session005\20230821_christie2P_session005_frontCam-0000_264.mp4']
# video_paths = [r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230815\christie2P\session001\20230815_christie2P_session001_sideCam-0000_264.mp4',
#               r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230815\christie2P\session001\20230815_christie2P_session001_frontCam-0000_264.mp4']

dlc_seg = 'DLC_resnet50_Reach2PDec5shuffle1_1030000'
# sess= r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230815\christie2P\session003'
# sess= r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230822\christie2P\session010'
# sess= r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230821\christie2P\session005'
sess= r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230818\christie2P\session008'
vid_tag = '_264.mp4'
# sess_dir = r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230815\christie2P\session003'

filter_data(sess, vid_tag, dlc_seg)
find_reach_events(sess, vid_tag)
# find_reach_events(video_paths)

#%% unused
# if np.all(Z_dist_p[frame:frame+2]<-5): #food dropped if pellet is too low
#     if debug:
#         print ('reach ended at frame %d!: DROPPED' % int(frame))
#     reach_events.append(('reachEnd_dropped', int(frame)))
#     break 

 # testC =  np.all(distance_p[frame:frame + 2] < 2)
 # testA = np.mean(distance_hvpp[frame:frame + 5]) < dist_thresh_max (=8)
 # testA = np.all(distance_hvpp[frame:frame + 2] > dist_thresh_max) # test if hand far enough away, below the pellet, and moving towards pellet

# Y_dist_h = filt_data['Pellet']['y'].values[start_frame]-filt_data['Hand']['y'].values
# velocity_y_h = np.diff(Y_dist_h)*(frame_rate/1000)
# velocity_p_filt = filtfilt(coeffs, [1], velocity_p)
# velocity_y_h_filt = filtfilt(coeffs, [1], velocity_y_h)
# velocity_p = np.diff(distance_p)*(frame_rate/1000)

