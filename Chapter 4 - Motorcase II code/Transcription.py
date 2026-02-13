#!/usr/bin/env python
# coding: utf-8

# --------------------------------------------

# THIS file is for transcribing the speech of the corpus to MIDI, using a 32-band mel-spectrogram

# --------------------------------------------

# In[23]:


import numpy as np
import librosa
import pretty_midi
import glob, os
import pickle

midi_out_folder = '{folder_to_save_MIDI_transcriptions}'

with open('{uniform_noisy_data_clipped.pkl}', 'rb') as f: # path to MSP-podcast data (added small amount of noise to spread distribution)
    data_array = pickle.load(f)

with open('filenames.pkl', 'rb') as f: # path to corpus filenames
    filenames = pickle.load(f)
audiofilepaths = ['MSP_podcast_corpus/Audios/Audio/' + filename for filename in filenames] # path to corpus audio

# Minimum duration threshold in seconds
min_duration_threshold = 0.03

# Repeat time threshold in seconds to join repeated notes
repeat_time_threshold = 0.1


# In[24]:


data_array[0] # check


# In[25]:


filenames[0] # check


# In[26]:


# Function to convert dB value to MIDI velocity
def db_to_velocity(db_value, threshold):
    velocity = int(np.clip((db_value - threshold) / (0 - threshold) * 64, 0, 127))
    return velocity

# Define a mapping dictionary for MIDI notes
midi_note_mapping = {
    0: 31,
    1: 12,
    2: 2,
    3: 0,
    4: 4,
    5: 19,
    6: 14,
    7: 9,
    8: 3,
    9: 1,
    10: 5,
    11: 8,
    12: 7,
    13: 6,
    14: 25,
    15: 16,
    16: 20,
    17: 18,
    18: 26,
    19: 10,
    20: 17,
    21: 15,
    22: 13,
    23: 21,
    24: 22,
    25: 29,
    26: 23,
    27: 24,
    28: 11,
    29: 27,
    30: 30,
    31: 28
}

# Store skipped files info
skipped_files = []

# Update progress every n files
progress_interval = 1000

# Process each audio file
for index, audiofile in enumerate(audiofilepaths):
    try:
        # Only print progress for every progress_interval files
        if index % progress_interval == 0:
            print(f'Processing file {index + 1}/{len(audiofilepaths)}')
        
        # Load the audio file
        y, sr = librosa.load(audiofile)
        
        # Create the mel spectrogram with 32 bands
        S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=32, fmin=2000, fmax=6000)
        S_dB = librosa.power_to_db(S, ref=np.max)
        
        # Calculate the hop length in seconds
        hop_length = 512  # Default hop length used by librosa.feature.melspectrogram
        hop_duration = hop_length / sr
        
        # Apply threshold to create MIDI notes
        threshold = -25  # in decibels
        midi_notes = []
        current_notes = {}
        last_note_time = {}  # Dictionary to keep track of the last time each note was added
        
        for t in range(S_dB.shape[1]):
            # Get all active notes at this time step with their decibel values
            active_notes = [(mel_band, S_dB[mel_band, t]) for mel_band in range(S_dB.shape[0]) if S_dB[mel_band, t] > threshold]
            # Sort by decibel values and select top 5
            active_notes = sorted(active_notes, key=lambda x: x[1], reverse=True)[:5]
        
            # Update current notes
            active_mel_bands = {mel_band for mel_band, _ in active_notes}
            for mel_band in list(current_notes):
                if mel_band not in active_mel_bands:
                    start_time, max_mel_value = current_notes[mel_band]
                    end_time = t * hop_duration
                    if end_time - start_time >= min_duration_threshold:
                        velocity = db_to_velocity(max_mel_value, threshold)
                        if mel_band in last_note_time and start_time - last_note_time[mel_band] < repeat_time_threshold:
                            # Extend the last note's end time instead of creating a new note
                            midi_notes[-1] = (mel_band, last_note_time[mel_band], end_time, velocity)
                        else:
                            midi_notes.append((mel_band, start_time, end_time, velocity))
                            last_note_time[mel_band] = start_time
                    del current_notes[mel_band]
        
            for mel_band, mel_value in active_notes:
                if mel_band in current_notes:
                    _, current_max_value = current_notes[mel_band]
                    current_notes[mel_band] = (current_notes[mel_band][0], max(current_max_value, mel_value))
                else:
                    start_time = t * hop_duration
                    current_notes[mel_band] = (start_time, mel_value)
        
        # Ensure any notes that are still active are properly closed at the end
        for mel_band, (start_time, max_mel_value) in current_notes.items():
            end_time = S_dB.shape[1] * hop_duration
            if end_time - start_time >= min_duration_threshold:
                velocity = db_to_velocity(max_mel_value, threshold)
                if mel_band in last_note_time and start_time - last_note_time[mel_band] < repeat_time_threshold:
                    # Extend the last note's end time instead of creating a new note
                    midi_notes[-1] = (mel_band, last_note_time[mel_band], end_time, velocity)
                else:
                    midi_notes.append((mel_band, start_time, end_time, velocity))
                    last_note_time[mel_band] = start_time
        
        # Generate MIDI file
        midi = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)
        
        for mel_band, start_time, end_time, velocity in midi_notes:
            # Map mel band to MIDI note number using the mapping dictionary
            note_number = midi_note_mapping.get(mel_band, mel_band)  # Default to mel_band if not found
            note = pretty_midi.Note(velocity=velocity, pitch=note_number, start=start_time, end=end_time)
            instrument.notes.append(note)
        
        midi.instruments.append(instrument)
        
        # Define the MIDI file path with the same name as the audio file but with a .midi extension
        midi_file_path = audiofile.replace('MSP_podcast_corpus/Audios/Audio/', midi_out_folder) # save path 
        midi_file_path = midi_file_path.replace('.wav', '.midi')
        
        # Write the MIDI file
        midi.write(midi_file_path)
    
    except Exception as e:
        # Record skipped file information
        skipped_files.append((index, audiofile, str(e)))
        print(f'Error processing file {audiofile} at index {index}: {e}')
        continue

# Print the summary of skipped files
print("Skipped files:")
for index, filename, error in skipped_files:
    print(f"Index: {index}, File: {filename}, Error: {error}")


# In[27]:


skipped_files # to view errors (empty audio files etc.)

# ------------------
# TESTING playback from here
# ------------------


# playback
import mido
from mido import MidiFile
mido.get_output_names()

port = mido.open_output('loopMIDI Port 1') # to send to Max-MSP for testing


# In[35]:


loaded_midi_file = MidiFile(r"{path to midi file}")


for msg in loaded_midi_file.play():
    port.send(msg)


# In[ ]:




