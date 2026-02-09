#!/usr/bin/env python
# coding: utf-8

# In[9]:

# ----------------------------------------------
# THIS code is for improvisation with motorcase II

Input VAD >> find nearest file >> output MIDI transcription >> loop / remap

# ----------------------------------------------


import asyncio
import mido

import threading
from threading import Lock
from threading import Thread, Event

import sys
import time
import numpy as np
import os, glob, pickle
import pandas as pd

import pygame
import random
import pickle
from time import sleep
import signal

# load pickled data
with open('C:/Users/Fin/Desktop/MSP_podcast_corpus/Pickled_for_code/filenames.pkl', 'rb') as f:
    filenames = pickle.load(f)
    
# load the noisy data
with open('C:/Users/Fin/Desktop/MSP_podcast_corpus/Pickled_for_code/uniform_noisy_data_clipped.pkl', 'rb') as f:
    data_array = pickle.load(f)
    
# MIDI input setup -----------------------------------------------------    
def list_available_midi_devices_and_select_MIDI_Mix():
    midi_device_name = None  # Initialize the variable to store the selected device name
    for device_name in mido.get_input_names():
        if 'MIDI Mix' in device_name:  # Check if 'MIDI Mix' is in the device name
            midi_device_name = device_name  # Set the variable to the matching device name
            break  # Optional: break the loop if you only need the first match

    # Check if a device was selected
    if midi_device_name:
        print(f"'MIDI Mix' device selected: {midi_device_name}")
    else:
        print("No 'MIDI Mix' device found.")
    
    return midi_device_name  # Return the selected device name or None if not found

midi_device_name = list_available_midi_devices_and_select_MIDI_Mix()

# MIDI output setup -----------------------------------------------------    
def Midi_Output_Setup():
    midi_port_name = None
    for device_name in mido.get_output_names():
        if 'CircuitPython' in device_name: 
            midi_port_name = device_name  
            break

    # Check if device was selected
    if midi_port_name:
        print(f"Outport device selected: {midi_port_name}")
    else:
        print("No outport device found.")
    
    return midi_port_name

midi_port_name = Midi_Output_Setup()

# Audio related functions: --------------------------------------------------------

# Function to find the nth closest filename: if there isn't an nth filename, it returns the lowest value for n
def find_closest_filename_optimized(data_array, target_emo_act, target_emo_dom, target_emo_val, filenames, n=0):

    # Calculate Euclidean distance
    distances = np.linalg.norm(data_array - [target_emo_act, target_emo_dom, target_emo_val], axis=1)
    
    # Get indices of sorted distances
    sorted_indices = distances.argsort()
    
    # Ensure n is within the valid range. If n is too large, set it to the last valid index.
    n = max(0, min(n, len(filenames) - 1))
    
    # Find the nth closest index, adjusting for out-of-range n
    nth_closest_index = sorted_indices[n]
    
    return filenames[nth_closest_index]

# play audio
def play_sound(sound):
    if sound:
        sound.play(loops=0, fade_ms=80)

# stop audio playing
def stop_sound(sound):
    if sound:
        sound.fadeout(100)
        
# General mapping function for midi input to 0 - 7 (database parameters)
def create_adjusted_list(start, end, n_points):
    x = np.linspace(0, 1, n_points)
    # Creating a flatter distribution: low at the ends and high in the middle
    y = -4 * (x - 0.5)**2 + 1  # Parabola

    # Normalize the output
    scaled_y = start + (end - start) * y

    return scaled_y.tolist()

# Create the list with 127 points - can change this if input method changes
adjusted_list = create_adjusted_list(1.0, 7.0, 254)[:128]

# General mapping function for audio file choosing
def map_value(input_value):
    return adjusted_list[input_value]

# Mapping function specifically for loop length
def map_loop_length_values(value, from_min, from_max, to_min, to_max):
    # Ensure the value is within the source range
    clamped_value = max(min(value, from_max), from_min)
    
    # Map the clamped value to the target range
    mapped_value = (clamped_value - from_min) / (from_max - from_min) * (to_max - to_min) + to_min
    
    return mapped_value

# Async timer for loop
async def async_timer(duration):
    await asyncio.sleep(duration)
    return True


# MIDI out functions ---------------------------------------------------------------

class MidiPlayer:
    def __init__(self, port_name):
        self.port_name = port_name
        self.port = mido.open_output(port_name)
        self.playing = False
        self.muted = False
        self.thread = None
        self.mid = None
        self.playing_notes = set()
        self.lock = threading.Lock()
        self.note_mapping = {i: i for i in range(32)}  # Initial identity mapping
        self.remapping_enabled = False  # Controls whether new mappings can be generated

    def enable_remapping(self):
        # Generate a new mapping
        self.generate_new_mapping()
        # Allow new mappings to be generated
        self.remapping_enabled = True

    def disable_remapping(self):
        # Prevent new mappings from being generated
        self.remapping_enabled = False

    def generate_new_mapping(self):
        all_notes = list(range(32))
        random.shuffle(all_notes)
        self.note_mapping = {i: all_notes[i] for i in range(32)}

    def load_and_play(self, file_path, loop=False):
        with self.lock:
            if not os.path.exists(file_path):
                return
            if self.playing:
                self.stop_playback()

            with open(file_path, 'rb') as file:
                self.mid = pickle.load(file)
            self.playing = True
            self.playing_notes.clear()

            if not self.thread or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._play, args=(loop,))
                self.thread.start()

    def _play(self, loop):
        while self.playing:
            for msg in self.mid.play(meta_messages=True):
                if not self.playing:
                    break

                # Apply the current mapping to all note_on and note_off messages within the range 0 to 31
                if msg.type in ['note_on', 'note_off'] and 0 <= msg.note <= 31:
                    # Retrieve the remapped note, falling back to the original note if not mapped
                    remapped_note = self.note_mapping.get(msg.note, msg.note)
                    # Create a new message with the remapped note
                    msg = msg.copy(note=remapped_note)

                if msg.type == 'note_on' and msg.velocity == 0:
                    self.playing_notes.discard(msg.note)
                elif msg.type == 'note_on' and msg.velocity > 0:
                    self.playing_notes.add(msg.note)
                elif msg.type == 'note_off':
                    self.playing_notes.discard(msg.note)

                if not self.muted and self.port:
                    try:
                        if isinstance(msg, mido.Message):
                            self.port.send(msg)
                    except ValueError as e:
                        print(f"Error sending message: {e}")
                    time.sleep(0.03)  # delay is a bit of a hacky solution here

            if not loop:
                break

        self.playing = False

    def stop_playback(self):
        with self.lock:
            self.playing = False
            if self.thread and self.thread.is_alive():
                self.thread.join()
            self.thread = None

            for note in list(self.playing_notes):
                off_msg = mido.Message('note_on', note=note, velocity=0, channel=0)
                self.port.send(off_msg)
                self.playing_notes.remove(note)

    def mute(self):
        with self.lock:
            self.muted = True

    def unmute(self):
        with self.lock:
            self.muted = False

    def close(self):
        self.stop_playback()
        self.port.close()
        
# get midi port names with mido.get_output_names()
mido.get_output_names()

midi_filename_path = 'C:/Users/Fin/Desktop/MSP_podcast_corpus/Serialised_Midi_transcriptions_new/'


# In[7]:


# "mute" buttons 1 and 2 for toggling audio playback [note 1] and for toggling midi playback [note 4]
# mute 3 for remapping the output [note 7]
# fader 1: activation
# fader 2: dominance
# fader 3: valence
# fader 4: loop length
# fader 5 sweep through identical valued files, return same file if no alternatives

# Global variables
MIDI_mute = False
Audio_mute = False
ReMap_Output = False


async def print_fader_values(device_name, target_controls=(19, 23, 27, 31, 49)):
    pygame.mixer.init(buffer=512)
    initial_sound = 'C:/Users/Fin/Desktop/MSP_podcast_corpus/Audios/Audio/MSP-PODCAST_0001_0008.wav'
    sound = pygame.mixer.Sound(initial_sound)
    
    # setup midi outport 
    player = MidiPlayer(midi_port_name)

    prev_closest_filename = None
    prev_loop_length = None
    prev_myvolume = None
    prev_MIDI_mute = None
    
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        print("Signal received, shutting down...")
        shutdown_event.set()

    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler)    

    try:
        with mido.open_input(device_name) as port:
            values = [0] * len(target_controls)
            prev_values = [None] * len(target_controls)

            timer_task = asyncio.create_task(async_timer(1.2))            


            while not shutdown_event.is_set():
                global MIDI_mute, Audio_mute, ReMap_Output
                messages = port.iter_pending()
                if messages:
                    for message in messages:
                        # print("Received MIDI message:", message)  # Debug print
                        
                        if message.type == 'control_change' and message.control in target_controls:
                            index = target_controls.index(message.control)
                            values[index] = message.value
                        if message.type == 'note_on' and message.note == 1:
                            Audio_mute = not Audio_mute
                        if message.type == 'note_on' and message.note == 4:
                            MIDI_mute = not MIDI_mute
                        ## remapping the output
                        if message.type == 'note_on' and message.note == 7:
                            ReMap_Output = True
                            
                        # Midi muting
                        if MIDI_mute:
                            player.mute()
                            
                        if not MIDI_mute:
                            player.unmute()
                            
                        # Muting Audio: NOT DONE 
                        if Audio_mute:
                            sound.set_volume(0)
                        if not Audio_mute:
                            sound.set_volume(1)
                            
                        # Remap output
                        if ReMap_Output:
                            player.enable_remapping() 
                            ReMap_Output = False
                            player.disable_remapping()
                            
                    if values != prev_values:
                        value_1, value_2, value_3, value_4, value_5 = values
                        prev_values = values.copy()

                        
                        # Midi input mapped to variables
                        target_emo_act = map_value(value_1)
                        target_emo_dom = map_value(value_2)
                        target_emo_val = map_value(value_3)
                        loop_length = map_loop_length_values(value_4, 0, 127, 0.3, 4) # mapping loop length
                        
                        # scrubbing through identically labeled files
                        identical_scrub_value = value_5
                        
                        # Audio file path
                        closest_filename = find_closest_filename_optimized(data_array, target_emo_act, target_emo_dom, target_emo_val, filenames, n=identical_scrub_value)
                        folder_path = 'C:/Users/Fin/Desktop/MSP_podcast_corpus/Audios/Audio/'
                        full_path = os.path.join(folder_path, closest_filename)   
                        
                        # Midi file path
                        midi_file_path = os.path.join(midi_filename_path, closest_filename.replace('.wav', '.pkl'))                     
                        
                        # Check if either closest_filename or loop_length has changed
                        if closest_filename != prev_closest_filename or loop_length != prev_loop_length:
                            # Stop the current sound
                            stop_sound(sound)
                            
                            # Stop the current midi
                            player.stop_playback()

                            # Load and play new sound
                            full_path = os.path.join(folder_path, closest_filename)
                            sound = pygame.mixer.Sound(file=full_path)
                            
                            if Audio_mute:
                                sound.set_volume(0)  # Apply mute state immediately
                            else:
                                sound.set_volume(1)  # Ensure sound is played at full volume if not muted
                            play_sound(sound)                            
                            
                            play_sound(sound)
                            
                            # Load and play new midi
                            # Midi muting
                            if MIDI_mute:
                                player.mute()

                            if not MIDI_mute:
                                player.unmute()                            
                            player.load_and_play(midi_file_path, loop=False)

                            # Update previous values
                            prev_closest_filename = closest_filename
                            prev_loop_length = loop_length
                            prev_MIDI_mute = MIDI_mute

                        # Reset the timer with new loop length
                        timer_task.cancel()
                        timer_task = asyncio.create_task(async_timer(loop_length))

                # Check if timer is finished
                if timer_task.done():
                    # Stop the current sound
                    stop_sound(sound)
                    
                    # stop the current MIDI
                    player.stop_playback()

                    # Load and play sound based on the latest filename
                    full_path = os.path.join(folder_path, closest_filename)
                    sound = pygame.mixer.Sound(file=full_path)

                    # Midi muting
                    if MIDI_mute:
                        player.mute()

                    if not MIDI_mute:
                        player.unmute()                       
                    
                    # MIDI out
                    player.load_and_play(midi_file_path, loop=False)
                    
                    # Audio out
                    if Audio_mute:
                        sound.set_volume(0)  # Apply mute state immediately
                    else:
                        sound.set_volume(1)  # Ensure sound is played at full volume if not muted                    
                    play_sound(sound)

                    # Restart the timer
                    timer_task = asyncio.create_task(async_timer(loop_length))

                await asyncio.sleep(0.02) # 0.02 stops most audio overlays

    except asyncio.CancelledError:
        pass
    finally:
        print("Cleaning up...")
        stop_sound(sound)
        player.stop_playback() # stop the MIDI playback
        
        # Close the MIDI port when done
        player.close()
        
        # Stop the pygame mixer
        pygame.mixer.quit()
        
        if timer_task:
            timer_task.cancel()
            
        print("Finished")
        
# Def main
async def main():
    device_name = midi_device_name
    await print_fader_values(device_name)


# In[8]:


# Run the main function
asyncio.run(main())


# In[ ]:




