# -*- coding: utf-8 -*-
"""
Created on Wed Jan 17 10:57:09 2024

@author: reynoben
"""
import os
import findReachEvents_v2 as fre

# config_path = r'C:\Users\pitram\Documents\SoleTrain-christie-2024-03-28\config.yaml'
# root_path = "Z:\PHYS\ChristieLab\Data\MSP_Z\Reach_Training"
config_path = r'C:\Users\pitram\Documents\SoleTrain-christie-2024-03-28\config.yaml'
root_path = r'F:\gradschool\rotations\jason_christie\behavior_videos\compressed'

sess_list_full = []
cutoff_date = "20240216"

for foldername in os.listdir(root_path):
    if foldername.isdigit() and len(foldername) == 8 and foldername >= cutoff_date:
        folder_path = os.path.join(root_path, foldername)
        christie2P = os.path.join(folder_path, 'christie2P')
        if os.path.exists(christie2P):
            sess_list = [name for name in os.listdir(christie2P)]
            if len(sess_list):
                for filename in sess_list:
                    sess_dir = os.path.join(christie2P, filename)
                    sess_list_full.append(sess_dir)
                    # mp4_list = os.path.join(sess_dir, '*_264.mp4')
                    # vid_list = glob.glob(mp4_list)
                    # if len(vid_list) == 2:
                    #     mp4_paths = [os.path.join(sess_dir, name) for name in vid_list]
                    #     video_pairs.append(mp4_paths)
                    print(sess_list_full)



#%% find events
import os
import findReachEvents_v2 as fre
dlc_seg = 'DLC_resnet50_SoleTrainMar28shuffle1_1030000'
# dlc_seg = 'DLC_resnet101_reach2graspMar3shuffle1_1030000'
# # # video_paths = [r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230620\christielab\session001\20230620_christielab_session001_sideCam-0000.mp4',
# # #               r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230620\christielab\session001\20230620_christielab_session001_frontCam-0000.mp4']
# # video_paths = [r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230821\christie2P\session005\20230821_christie2P_session005_sideCam-0000_264.mp4',
# #             r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230821\christie2P\session005\20230821_christie2P_session005_frontCam-0000_264.mp4']
# # # video_paths = [r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230927\christie2P\session009\20230927_christie2P_session009_sideCam-0000_264.mp4',
# # #                 r'Y:\ChristieLab\Data\MSP_Z\Reach_Training\20230927\christie2P\session009\20230927_christie2P_session009_frontCam-0000_264.mp4']
# vid_tag = '_264.mp4'
vid_tag = '-0000.mp4'
sess_list_full = []
sess1 = r'F:\gradschool\rotations\jason_christie\behavior_videos\compressed\20240213\session009'
# sess2 = r'F:\gradschool\rotations\jason_christie\behavior_videos\compressed\20240217\session016'
sess_list_full.append(sess1)
print(sess_list_full)
for session in sess_list_full:
    print(session)
    fre.extract_tracking_data(session, vid_tag, dlc_seg)
    fre.filter_data(session, vid_tag, dlc_seg)
    fre.find_reach_events(session, vid_tag)
    


#%%find reach durations

# full_dist_list = list()
# for i, sess in enumerate(sess_list_full):
#     print(sess)
#     dist_list = fre.find_reach_events(sess, vid_tag)
#     full_dist_list.extend(dist_list)
# # fre.filter_data(pair, dlc_seg)
# # import numpy as np
# # np_file_path = r'Y:\ChristieLab\Data\BR\Reach_refinement_miss_distance.npy'
# # full_dist_list = np.array(full_dist_list)
# # np.save(np_file_path, full_dist_list)
# #%%
# import numpy as np
# min_miss_dist = np.min(full_dist_list)
# max_miss_dist = np.max(full_dist_list)
# print(min_miss_dist,max_miss_dist)
# avg = np.average(full_dist_list)

# import matplotlib.pyplot as plt  
# from scipy.stats import norm

                   

# #plotting
# mu, std_dev = np.mean(full_dist_list), np.std(full_dist_list)
# xmin, xmax = min_miss_dist, max_miss_dist
# x = np.linspace(xmin, xmax, 100)
# p = norm.pdf(x, mu, std_dev)

# fig, ax = plt.subplots()
# n, bins, patches = ax.hist(full_dist_list, bins=60, alpha=0.7, color='black',range=(xmin, xmax))
# ax.plot(x, p * len(full_dist_list) * np.diff(bins)[0], 'k', linewidth=1)
# for i in range(0, 4):  # You can adjust the range as needed
#     ax.axvline(mu + i * std_dev, color='r', linestyle='--', linewidth=0.75, label=f'{i} Std Dev')


# ax.set_xticks(np.arange(0, xmax, 2))
# ax.set_xticklabels(np.arange(0, round(xmax), 2), fontsize = 'small')

# ax.set_xlabel('Miss Distance')
# ax.set_ylabel('Number of Reaches')
# ax.set_title('Duration Distribution')
# plt.show()
