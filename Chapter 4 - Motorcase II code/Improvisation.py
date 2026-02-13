#!/usr/bin/env python
# coding: utf-8

# ----------------------------------------------
# THIS code is for improvisation with motorcase II
# Input VAD >> find nearest file >> output MIDI transcription >> loop / remap
# ----------------------------------------------

import asyncio
import mido
import threading
from threading import Lock, Thread, Event
import sys
import time
import numpy as np
import os, glob, pickle
import pandas as pd
import random
from time import sleep
import signal

# load pickled data
with open('{filenames.pkl}', 'rb') as f: # path to filenames
    filenames = pickle.load(f)
    
with open('{uniform_noisy_data_clipped.pkl}', 'rb') as f: # path to corpus data (VAD)
    data_array = pickle.load(f)
    
# MIDI input setup -----------------------------------------------------    
def list_available_midi_devices_and_select_MIDI_Mix():
    midi_device_name = None  
    for device_name in mido.get_input_names():
        if 'MIDI Mix' in device_name:  
            midi_device_name = device_name  
            break  

    if midi_device_name:
        print(f"'MIDI Mix' device selected: {midi_device_name}")
    else:
        print("No 'MIDI Mix' device found.")
    
    return midi_device_name  

midi_device_name = list_available_midi_devices_and_select_MIDI_Mix()

# MIDI output setup -----------------------------------------------------    
def Midi_Output_Setup():
    midi_port_name = None
    for device_name in mido.get_output_names():
        if 'CircuitPython' in device_name:  
            midi_port_name = device_name  
            break

    if midi_port_name:
        print(f"Outport device selected: {midi_port_name}")
    else:
        print("No outport device found.")
    
    return midi_port_name

midi_port_name = Midi_Output_Setup()

# Data Selection Logic --------------------------------------------------------

def find_closest_filename_optimized(data_array, target_emo_act, target_emo_dom, target_emo_val, filenames, n=0):
    distances = np.linalg.norm(data_array - [target_emo_act, target_emo_dom, target_emo_val], axis=1)
    sorted_indices = distances.argsort()
    n = max(0, min(n, len(filenames) - 1))
    nth_closest_index = sorted_indices[n]
    return filenames[nth_closest_index]

def create_adjusted_list(start, end, n_points):
    x = np.linspace(0, 1, n_points)
    y = -4 * (x - 0.5)**2 + 1  
    scaled_y = start + (end - start) * y
    return scaled_y.tolist()

adjusted_list = create_adjusted_list(1.0, 7.0, 254)[:128]

def map_value(input_value):
    return adjusted_list[input_value]

def map_loop_length_values(value, from_min, from_max, to_min, to_max):
    clamped_value = max(min(value, from_max), from_min)
    mapped_value = (clamped_value - from_min) / (from_max - from_min) * (to_max - to_min) + to_min
    return mapped_value

async def async_timer(duration):
    await asyncio.sleep(duration)
    return True

# MIDI Player Class ---------------------------------------------------------------

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
        self.note_mapping = {i: i for i in range(32)}  
        self.remapping_enabled = False  

    def enable_remapping(self):
        self.generate_new_mapping()
        self.remapping_enabled = True

    def disable_remapping(self):
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

                if msg.type in ['note_on', 'note_off'] and 0 <= msg.note <= 31:
                    remapped_note = self.note_mapping.get(msg.note, msg.note)
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
                    time.sleep(0.03) 

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
                if self.port:
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
        if self.port:
            self.port.close()

midi_filename_path = '{path_to_transcribed_MIDI}' # define folder of midi transcriptions

# Main Control Logic ---------------------------------------------------------------

# mute 2 for toggling midi playback [note 4]
# mute 3 for remapping the output [note 7]
# faders 1-3: VAD, fader 4: loop length, fader 5: identical file scrub

MIDI_mute = False
ReMap_Output = False

async def main_loop(device_name, target_controls=(19, 23, 27, 31, 49)):
    player = MidiPlayer(midi_port_name)

    prev_closest_filename = None
    prev_loop_length = None
    
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        print("Signal received, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)    

    try:
        with mido.open_input(device_name) as port:
            values = [0] * len(target_controls)
            prev_values = [None] * len(target_controls)
            timer_task = asyncio.create_task(async_timer(1.2))            

            while not shutdown_event.is_set():
                global MIDI_mute, ReMap_Output
                messages = port.iter_pending()
                if messages:
                    for message in messages:
                        if message.type == 'control_change' and message.control in target_controls:
                            index = target_controls.index(message.control)
                            values[index] = message.value
                        
                        # MIDI Mute Toggle
                        if message.type == 'note_on' and message.note == 4:
                            MIDI_mute = not MIDI_mute
                            if MIDI_mute: player.mute()
                            else: player.unmute()
                            
                        # Remapping Trigger
                        if message.type == 'note_on' and message.note == 7:
                            player.enable_remapping() 
                            player.disable_remapping()
                            
                    if values != prev_values:
                        v1, v2, v3, v4, v5 = values
                        prev_values = values.copy()

                        target_emo_act = map_value(v1)
                        target_emo_dom = map_value(v2)
                        target_emo_val = map_value(v3)
                        loop_length = map_loop_length_values(v4, 0, 127, 0.3, 4)
                        identical_scrub_value = v5
                        
                        closest_filename = find_closest_filename_optimized(data_array, target_emo_act, target_emo_dom, target_emo_val, filenames, n=identical_scrub_value)
                        midi_file_path = os.path.join(midi_filename_path, closest_filename.replace('.wav', '.pkl'))                     
                        
                        if closest_filename != prev_closest_filename or loop_length != prev_loop_length:
                            player.stop_playback()
                            player.load_and_play(midi_file_path, loop=False)

                            prev_closest_filename = closest_filename
                            prev_loop_length = loop_length

                        timer_task.cancel()
                        timer_task = asyncio.create_task(async_timer(loop_length))

                if timer_task.done():
                    player.stop_playback()
                    # Re-trigger based on latest selection
                    closest_filename = find_closest_filename_optimized(data_array, map_value(values[0]), map_value(values[1]), map_value(values[2]), filenames, n=values[4])
                    midi_file_path = os.path.join(midi_filename_path, closest_filename.replace('.wav', '.pkl'))
                    player.load_and_play(midi_file_path, loop=False)
                    
                    timer_task = asyncio.create_task(async_timer(loop_length))

                await asyncio.sleep(0.01)

    except asyncio.CancelledError:
        pass
    finally:
        print("Cleaning up...")
        player.close()
        if timer_task:
            timer_task.cancel()
        print("Finished")

async def main():
    if midi_device_name:
        await main_loop(midi_device_name)
    else:
        print("Exit: No Input Device")

if __name__ == "__main__":
    asyncio.run(main())