#!/usr/bin/env python
# coding: utf-8

# In[ ]:


thisdevice = 'Device_1' # don't change for send device

audio_volume = 0.5

from pythonosc import udp_client
import pygame
pygame.mixer.init(frequency=44100, size=-16, channels=1)
import os
import serial
import serial.tools.list_ports
import random
import time
import mido

# specify audio and MIDI folders
audio_path = f"/home/fin/speech/SmalltalkFINAL/audio/Device_1"
midi_path = f"/home/fin/speech/SmalltalkFINAL/midi/Device_1"

# Get audio and MIDI files
audio_files = [os.path.join(audio_path, f) for f in os.listdir(audio_path) if f.endswith(('.mp3', '.wav'))]
midi_files = [os.path.join(midi_path, f) for f in os.listdir(midi_path) if f.endswith(('.mid', '.midi'))]

print("files loaded")

# ---------------

# Configuration for sending OSC messages
SEND_IP = "192.168.0.27"  
SEND_PORT = 5010

SEND_IP_2 = "192.168.0.38"
SEND_PORT_2 = 5011

osc_client_1 = udp_client.SimpleUDPClient(SEND_IP, SEND_PORT)
osc_client_2 = udp_client.SimpleUDPClient(SEND_IP_2, SEND_PORT_2)

def send_message(address: str, *args):
    osc_client_1.send_message(address, args)
    print(f"Sent: {address} -> {args}")

def send_message_2(address: str, *args):
    osc_client_2.send_message(address, args)
    print(f"Sent: {address} -> {args}")

# ---------------

# Setup Arduino connection
arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=.01) # wait a little after starting serial connection
time.sleep(5)
print('arduino connected')

# define motor silence
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

# ---------------
    
try:
    audio_file_counter_Device_1 = 0
    audio_file_counter_Device_2 = 0
    audio_file_counter_Device_3 = 0
        
    current_MIDI_file = midi_files[0]
    current_audio_file = audio_files[audio_file_counter_Device_1]

    # playback midi file
    mid = mido.MidiFile(current_MIDI_file)
    for msg in mid.play():
        if msg.type == 'note_on' and msg.velocity > 0:

            # DEV 1
            if msg.note == 72: # C5: dev 1, audio
                play_audio_file(current_audio_file, audio_volume)
                audio_file_counter_Device_1 +=1

            elif msg.note == 76: # E5: dev 1, motor 1 on
                mapped_speed = map_to_motor_speeds(msg.velocity)
                motor_output = f'<A, {mapped_speed}>'
                arduino.write(motor_output.encode('utf-8'))

            elif msg.note == 77: # F5: dev 1, motor 2 on
                mapped_speed = map_to_motor_speeds(msg.velocity)
                motor_output = f'<B, {mapped_speed}>'
                arduino.write(motor_output.encode('utf-8'))                        

            elif msg.note == 79: # G5: dev 1, light on
                lightON()

            # SEND TO DEV 2 --------------------------------------
            elif msg.note == 60: # C4: dev 2, audio
                message_content = ('audio', audio_file_counter_Device_2)
                send_message("/5006", *message_content)     
                audio_file_counter_Device_2 += 1

            elif msg.note == 64: # E4: dev 2, motor 1 on
                message_content = ('motor_1_on', msg.velocity)
                send_message("/5006", *message_content) 

            elif msg.note == 65: # F4: dev 2, motor 2 on
                message_content = ('motor_2_on', msg.velocity)
                send_message("/5006", *message_content)                         

            elif msg.note == 67: # G4: dev 2, light on
                message_content = ('light_on')
                send_message("/5006", *message_content)                         

            # SEND TO DEV 3 --------------------------------------
            elif msg.note == 48: # C3: dev 3, audio
                message_content = ('audio', audio_file_counter_Device_3)
                send_message_2("/5006", *message_content)     
                audio_file_counter_Device_3 += 1

            elif msg.note == 52: # E3: dev 3, motor 1 on
                message_content = ('motor_1_on', msg.velocity)
                send_message_2("/5006", *message_content) 

            elif msg.note == 53: # F3: dev 3, motor 2 on
                message_content = ('motor_2_on', msg.velocity)
                send_message_2("/5006", *message_content)                         

            elif msg.note == 55: # F3: dev 3, light on
                message_content = ('light_on')
                send_message_2("/5006", *message_content)                            

        elif msg.type == 'note_off': # --------------------------------------------------
            # DEV 1
            if msg.note == 76: # E5: dev 1, motor 1 off
                arduino.write(silence.encode('utf-8'))

            elif msg.note == 77: # F5: dev 1, motor 2 off
                arduino.write(silence.encode('utf-8'))                      

            elif msg.note == 79: # G5: dev 1, light off
                lightOFF()        

           # SEND TO DEV 2 --------------------------------------
            elif msg.note == 64: # E4: dev 2, motor 1 off
                message_content = ('motor_1_off')
                send_message("/5006", *message_content) 

            elif msg.note == 65: # F4: dev 2, motor 2 off
                message_content = ('motor_2_off')
                send_message("/5006", *message_content)                         

            elif msg.note == 67: # G4: dev 2, light off
                message_content = ('light_off')
                send_message("/5006", *message_content)                         

            # SEND TO DEV 3 --------------------------------------     
            elif msg.note == 52: # E3: dev 3, motor 1 off
                message_content = ('motor_1_off')
                send_message_2("/5006", *message_content) 

            elif msg.note == 53: # F3: dev 3, motor 2 off
                message_content = ('motor_2_off')
                send_message_2("/5006", *message_content)                         

            elif msg.note == 55: # F3: dev 3, light off
                message_content = ('light_off')
                send_message_2("/5006", *message_content)
                
    print("midi file complete")
    
    # Send completion signals to all devices
    send_message("/5006", 'playback_complete')
    send_message_2("/5006", 'playback_complete')    
    
except KeyboardInterrupt:
    print("Playback interrupted by user")
except Exception as e:
    print(f"Error during playback: {str(e)}")
finally:
    print("Cleanup")
    lightOFF()
    pygame.mixer.quit()
    arduino.write(silence.encode('utf-8'))
    time.sleep(0.2)
    arduino.close()
    print("END")

