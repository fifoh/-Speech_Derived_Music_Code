#!/usr/bin/env python
# coding: utf-8

# In[ ]:


thisdevice = 'Device_2' # or Device_3

audio_volume = 0.5

# specify audio and MIDI folders
audio_path = f"/home/fin/speech/SmalltalkFINAL/audio/{thisdevice}"
midi_path = f"/home/fin/speech/SmalltalkFINAL/midi/{thisdevice}"

# Get audio and MIDI files
audio_files = [os.path.join(audio_path, f) for f in os.listdir(audio_path) if f.endswith(('.mp3', '.wav'))]
midi_files = [os.path.join(midi_path, f) for f in os.listdir(midi_path) if f.endswith(('.mid', '.midi'))]

print("files loaded")

# ---------------

from pythonosc import udp_client
import pygame
pygame.mixer.init(frequency=44100, size=-16, channels=1)
import os

from pythonosc import dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
import time

import serial
import struct
import serial.tools.list_ports

import random
import time

# Configuration for receiving OSC messages
RECEIVE_IP = "192.168.0.27" 
RECEIVE_PORT = 5010 

running = True

# Setup Arduino connection
arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=.01) # wait a little after starting serial connection
time.sleep(5)
print('arduino connected')

# define motor material

silence = "<X, 0>"

def lightON():
    message = "<L>"
    arduino.write(message.encode('utf-8'))
    
def lightOFF():
    message = "<D>"
    arduino.write(message.encode('utf-8'))
    
# show lights working and setup complete
lightON()
time.sleep(0.2)
lightOFF()
time.sleep(1)

def play_audio_file(audio_file, volume=0.5):
    volume = max(0, min(volume, 1))
    pygame.mixer.music.load(audio_file)
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play()

# mapping MIDI velocity to motor speed:
def map_to_motor_speeds(midi_velocity):
    """Map MIDI velocity (0-127) to motor speed (30-250)."""
    min_midi = 0
    max_midi = 127
    min_speed = 30
    max_speed = 250
    
    motor_speed = int(min_speed + (midi_velocity - min_midi) * (max_speed - min_speed) / (max_midi - min_midi))

    return motor_speed
    
def message_handler(address, *args):
    global running
    
    try:    
        if args[0] == 'audio':
            current_audio_sample = args[1]        
            current_audio_file = audio_files[current_audio_sample]
            play_audio_file(current_audio_file, audio_volume)

        elif args[0] == 'motor_1_on':
            velocity = args[1]
            mapped_speed = map_to_motor_speeds(velocity)
            motor_output = f'<A, {mapped_speed}>'
            arduino.write(motor_output.encode('utf-8'))        

        elif args[0] == 'motor_1_off':    
            arduino.write(silence.encode('utf-8'))

        elif args[0] == 'motor_2_on':
            velocity = args[1]
            mapped_speed = map_to_motor_speeds(velocity)
            motor_output = f'<B, {mapped_speed}>'
            arduino.write(motor_output.encode('utf-8'))    

        elif args[0] == 'motor_2_off':
            arduino.write(silence.encode('utf-8'))

        elif args[0] == 'light_on':
            lightON()

        elif args[0] == 'light_off':
            lightOFF()

        elif args[0] == 'playback_complete':
            running = False
        
    except Exception as e:
        print(f"Error handling OSC message: {e}")

def start_server():
    global running
    server = None
    
    try:
        disp = dispatcher.Dispatcher()
        disp.map("/*", message_handler)

        server = BlockingOSCUDPServer((RECEIVE_IP, RECEIVE_PORT), disp)
        print(f"Listening for OSC messages on {RECEIVE_IP}:{RECEIVE_PORT}")
        
        while running:
            server.handle_request()  # Process one message at a time
            
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        if server:
            server.server_close()
        pygame.mixer.quit()
        arduino.write(silence.encode('utf-8'))
        lightOFF()
        time.sleep(0.2)
        arduino.close()
        print("Cleanup complete")

if __name__ == "__main__":
    start_server()

