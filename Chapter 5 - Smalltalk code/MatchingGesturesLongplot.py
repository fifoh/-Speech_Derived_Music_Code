#!/usr/bin/env python
# coding: utf-8

# In[12]:


# longplot version of MatchingGestures, for longer audio files where images can't be rendered in notebook
# run this cell, draw a line, press 'ESC'

# Paths
input_audio_path = r"{input_audio_path}" # set audio path

mode = 'pitch' # mode = 'pitch' OR amplitude'

# adjustable parameters for DTW
max_rangefactor = 5 # how much the query can be stretched: default 5
overlap = 0 # whether found subsections can overlap: default 0
minlength = 30 # minimum length for match (frames): default 30
maxlength = 80 # maximum length for match (frames): default 150

top_n = 20  # Number of top matches you want to see

import parselmouth
import numpy as np
from scipy.interpolate import interp1d
import os
import numpy as np
import librosa
import soundfile as sf
from IPython.display import Audio

from dtaidistance.subsequence.dtw import subsequence_alignment
from dtaidistance import dtw_visualisation as dtwvis
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime

def make2d(arr):
    indexed_arr = np.column_stack((np.arange(len(arr)), arr))
    return indexed_arr

def extract_f0_and_energy_aligned_new(audio_path, time_step=0.01):
    # Load the audio file
    sound = parselmouth.Sound(audio_path)

    # Extract F0 (pitch)
    pitch = sound.to_pitch(time_step=time_step)
    f0_times = pitch.xs()  # Time points for F0
    f0_values = pitch.selected_array['frequency']  # F0 values in Hz

    # Extract amplitude/energy (intensity)
    intensity = sound.to_intensity(time_step=time_step)
    energy_times = intensity.xs()  # Time points for energy
    energy_values = intensity.values[0]  # Energy values in dB

    # Create interpolation functions
    f0_interp = interp1d(f0_times, f0_values, kind='linear', bounds_error=False, fill_value=np.nan)
    energy_interp = interp1d(energy_times, energy_values, kind='linear', bounds_error=False, fill_value=np.nan)

    # Define a common time axis (e.g., use the union of both time arrays)
    common_times = np.union1d(f0_times, energy_times)

    # Interpolate F0 and energy to the common time axis
    f0_aligned = f0_interp(common_times)
    energy_aligned = energy_interp(common_times)

    # Replace NaN values with 0
    f0_aligned = np.nan_to_num(f0_aligned, nan=0.0)
    energy_aligned = np.nan_to_num(energy_aligned, nan=0.0)

    # Find the bottom 25% threshold for energy
    energy_threshold = np.percentile(energy_aligned[energy_aligned > 0], 25)

    # Set F0 and energy values to 0 where energy is below the threshold
    low_energy_mask = energy_aligned < energy_threshold
    f0_aligned[low_energy_mask] = 0
    energy_aligned[low_energy_mask] = 0

    return common_times, f0_aligned, energy_aligned

common_times, f0_aligned, energy_aligned = extract_f0_and_energy_aligned_new(input_audio_path)

# Normalize the arrays to [0, 1]
normalized_f0_aligned = (f0_aligned - np.min(f0_aligned)) / (np.max(f0_aligned) - np.min(f0_aligned))
normalized_energy_aligned = (energy_aligned - np.min(energy_aligned)) / (np.max(energy_aligned) - np.min(energy_aligned))

# DRAWING 
import cv2
import numpy as np
import time
from scipy.interpolate import interp1d

# Create a blank white image
width, height = 800, 600
image = np.ones((height, width, 3), dtype=np.uint8) * 255

# Variables for drawing
drawing = False
last_pos = None
last_time = None  # To track time for speed calculation

# Min and max thickness for the line
min_thickness = 5
max_thickness = 70

# Define a maximum speed threshold (prevents excessive thickness)
max_speed = 1500  # Adjust based on testing

# Smoothing factor (adjust between 0.1 and 1.0)
smoothing_factor = 0.05  # Lower values make thickness changes smoother

# Store previous thickness for gradual transitions
prev_thickness = min_thickness

# Data storage (to store 100 points)
y_positions = np.zeros(width)
thickness_values = np.zeros(width)

# Mouse callback function
def draw_line(event, x, y, flags, param):
    global drawing, last_pos, last_time, prev_thickness, y_positions, thickness_values, image

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        last_pos = (x, y)
        last_time = time.time()  # Record the time

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            current_pos = (x, y)
            current_time = time.time()

            # Calculate speed (distance / time)
            distance = np.linalg.norm(np.array(last_pos) - np.array(current_pos))
            time_diff = current_time - last_time if last_time else 0.01  # Prevent division by zero

            speed = distance / time_diff  # Speed in pixels per second

            # Normalize speed into a 0-1 range and map it to thickness
            normalized_speed = min(speed / max_speed, 1)  # Clamping speed to prevent overshooting
            target_thickness = int(min_thickness + (max_thickness - min_thickness) * normalized_speed)

            # Smooth thickness transition using linear interpolation
            smoothed_thickness = int(prev_thickness + (target_thickness - prev_thickness) * smoothing_factor)

            # Draw the line with the smoothed thickness
            cv2.line(image, last_pos, current_pos, (0, 0, 0), smoothed_thickness, cv2.LINE_AA)
            
            # Update y_positions and thickness_values arrays
            x_indices = np.arange(min(last_pos[0], current_pos[0]), max(last_pos[0], current_pos[0]) + 1)
            y_interpolated = np.interp(x_indices, [last_pos[0], current_pos[0]], [last_pos[1], current_pos[1]])
            
            # Flip the y-values during data collection
            y_interpolated = height - y_interpolated  # Invert y-axis
            
            y_positions[x_indices] = y_interpolated
            thickness_values[x_indices] = smoothed_thickness

            # Update last position, time, and thickness
            last_pos = current_pos
            last_time = current_time
            prev_thickness = smoothed_thickness  # Store smoothed thickness for next update

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False

# Set up OpenCV window and mouse callback
cv2.namedWindow("Drawing")
cv2.setMouseCallback("Drawing", draw_line)

while True:
    cv2.imshow("Drawing", image)
    if cv2.waitKey(1) & 0xFF == 27:  # Press 'Esc' to exit
        break
        
# Ensure we have exactly 100 points
if np.any(y_positions):
    # Remove leading and trailing zeros
    nonzero_indices = np.nonzero(y_positions)[0]
    if len(nonzero_indices) > 0:
        y_positions = y_positions[nonzero_indices[0]: nonzero_indices[-1] + 1]
        thickness_values = thickness_values[nonzero_indices[0]: nonzero_indices[-1] + 1]

        # Sort x-values and corresponding y-values to ensure monotonicity
        sorted_indices = np.argsort(np.arange(len(y_positions)))
        y_positions_sorted = y_positions[sorted_indices]
        thickness_values_sorted = thickness_values[sorted_indices]

        # Resample to 50 points
        new_indices = np.linspace(0, len(y_positions_sorted) - 1, 50)
        y_positions_resampled = interp1d(np.arange(len(y_positions_sorted)), y_positions_sorted, kind='linear')(new_indices)
        thickness_values_resampled = interp1d(np.arange(len(thickness_values_sorted)), thickness_values_sorted, kind='linear')(new_indices)
        
        # Normalize y_positions within the image height range (0 to height)
        y_positions_resampled = (y_positions_resampled - 0) / (height - 0)
        
        # Normalize thickness_values within the thickness range (0 to max_thickness)
        thickness_values_resampled = (thickness_values_resampled - 0) / (max_thickness - 0)
        
    else:
        y_positions_resampled = np.zeros(50)
        thickness_values_resampled = np.zeros(50)
else:
    y_positions_resampled = np.zeros(50)  # Fallback in case of no drawing
    thickness_values_resampled = np.zeros(50)

# close
cv2.destroyAllWindows()

# get and visualize matches

if mode == 'pitch':
    series = normalized_f0_aligned
    query = y_positions_resampled   
    
if mode == 'amplitude':
    series = normalized_energy_aligned
    query = y_positions_resampled       

sa = subsequence_alignment(query, series)
matches = sa.best_matches(max_rangefactor=max_rangefactor, overlap=overlap, minlength=minlength, maxlength=maxlength)

# Convert the generator to a list and select the top N matches
matches_list = list(matches)[:top_n]  # Take only the first N matches

# Define how far left the query should be
query_offset = -2 * len(query)  # Adjust factor as needed

# Define margin size for the query box
margin_x = 0.7 * len(query) 
margin_y = 0.7 * (max(query) - min(query))

import matplotlib.pyplot as plt
import matplotlib.patches as patches

import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Plot the series and query together
fig, ax = plt.subplots(figsize=(2000, 6))  # dpi irrelevant for vector formats
ax.plot(series, label='Series', color='black')

# Offset the query to the left
query_x_range = range(query_offset, query_offset + len(query))
ax.plot(query_x_range, query, label='Query', color='green')

# Add a larger box around the query
query_min, query_max = min(query), max(query)
query_box = patches.Rectangle(
    (query_offset - margin_x / 2, query_min - margin_y / 2),
    len(query) + margin_x,
    (query_max - query_min) + margin_y,
    linewidth=3,
    edgecolor='green',
    facecolor='none'
)
ax.add_patch(query_box)

# Highlight the top matches
for i, match in enumerate(matches_list):
    start, end = match.segment
    if i == 0:
        color, alpha = 'green', 0.7
    else:
        color, alpha = 'green', max(0.3, 0.7 - (i * 0.1))
    ax.axvspan(start, end, color=color, alpha=alpha)

ax.set_title(f"Top {top_n} Matches")
ax.legend()

# Save to vector (no raster size limit!)
fig.savefig("long_plot.svg", format="svg")   # or "long_plot.pdf"

# Close to prevent Jupyter from trying to rasterize inline
plt.close(fig)

# play audio
# Load audio file
y, sr = librosa.load(input_audio_path)

audio_objects = []
for match in matches_list:
    segment = match.segment  # Access the matched segment in the series
    start = segment[0]       # Start index of the match
    end = segment[1]         # End index of the match
    
    start_time = common_times[start]
    end_time = common_times[end] 

    # Convert start and end time to sample indices
    start_sample = int(start_time * sr)  # Convert start time to sample index
    end_sample = int(end_time * sr)      # Convert end time to sample index

    # Slice the audio signal
    audio_segment = y[start_sample:end_sample]
    
    # Create an audio object and append to the list
    audio_obj = Audio(audio_segment, rate=sr)
    audio_objects.append(audio_obj)
    
# listen to the matched sounds, and download if needed (click "...")
for audio_object in range(0, len(audio_objects)):
    display(audio_objects[audio_object])
    
if not audio_objects:
    print('no good matches found')


# In[6]:


# save all matches to folder
saving_audio_directory = r"{save_folder_path}" # set folder base path

# Generate a folder name using the current date and time
folder_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # creates new folder date/time
save_folder_path = os.path.join(saving_audio_directory, folder_name) 
os.makedirs(save_folder_path, exist_ok=True)
print(f"Created folder: {save_folder_path}")

for i, match in enumerate(matches_list):
    segment = match.segment  # Access the matched segment in the series
    start = segment[0]       # Start index of the match
    end = segment[1]         # End index of the match
    
    start_time = common_times[start]
    end_time = common_times[end] 

    # Convert start and end time to sample indices
    start_sample = int(start_time * sr)  # Convert start time to sample index
    end_sample = int(end_time * sr)      # Convert end time to sample index

    # Slice the audio signal
    audio_segment = y[start_sample:end_sample]
    
    # Save the audio segment
    output_audio_path = os.path.join(save_folder_path, f'audio_segment_{i + 1}.wav')
    sf.write(output_audio_path, audio_segment, sr)  # Save the audio segment as a .wav file
    print(f"Saved audio segment {i + 1} to: {output_audio_path}")    


# In[7]:


fig.savefig("long_plot.svg")  # or "long_plot.pdf"


# In[ ]:




