# This code is for performing with the Radio User Guide devices (audio playback, midi motor control)

import os
os.environ['SDL_AUDIODRIVER'] = 'alsa'

audio_folder_path = '/device_3'
this_device = 'device_3'

# unchanged from here


from adafruit_motorkit import MotorKit
kit = MotorKit(address=0x61)

kit.motor1.throttle = 0
kit.motor3.throttle = 0
kit.motor4.throttle = 0

import time
import numpy as np
import pygame
import mido

import subprocess

pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=256)
pygame.mixer.init()

def volume_up():
    subprocess.run(["amixer", "set", "Master", "5%+"])

def volume_down():
    subprocess.run(["amixer", "set", "Master", "5%-"])

def shutdown_pi():
    print('shutdown pi')
    time.sleep(2)
    os.system("sudo shutdown -h now")

for portname in mido.get_input_names():
    print(portname)

port_name = mido.get_input_names()[1]

audio_trigger = 48 # low C
motor_1_trigger = 53 # low F
motor_3_trigger = 55 # low G
motor_4_trigger = 57 # low A

total_reset_trigger = 72 # high C

# REHEARSAL LETTERS: FLATS FROM C# UP
letter_A = 49
letter_B = 51
letter_C = 54
letter_D = 56
letter_E = 58
letter_F = 61
letter_G = 63
letter_H = 66
letter_I = 68

shutdown_trigger = 70
volume_up_trigger = 62
volume_down_trigger = 60

# use other keys for rehearsal letters

current_audio_sample = 1
playing_sounds = []

def play_audio(current_audio_sample):
    file_path = os.path.join(audio_folder_path, f"{current_audio_sample}.wav")
    sound = pygame.mixer.Sound(file_path)
    playing_sounds.append(sound)
    sound.play()
    
def mute_mixer():
    for sound in playing_sounds:
        sound.stop()
        
def mapping_range(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def get_rehearsal_letter(letter_index, this_device):
    if this_device == 'device_1':
        rehearsal_numbers = [5,14,20,29,38,48,66,68,82]
    if this_device == 'device_2':
        rehearsal_numbers = [7,14,21,34,43,50,63,70,90]
    if this_device == 'device_3':
        rehearsal_numbers = [5,14,19,30,37,44,51,61,73]
        
    audio_number = rehearsal_numbers[letter_index]
    return audio_number
                
try:      
    with mido.open_input(port_name) as port:
        for message in port:
            # NOTE ON
            if message.type == 'note_on' and message.velocity > 0:
                print(message.note, message.velocity)
                
                # reset counter to 1
                if message.note == total_reset_trigger:
                    current_audio_sample = 1

                # play next audio sample
                elif message.note == audio_trigger:
                    print(f"playing sample{current_audio_sample}")
                    # incremeent audio sample
                    play_audio(current_audio_sample)
                    current_audio_sample +=1
                
                # play motor 1
                elif message.note == motor_1_trigger:
                    print('motor 1 on')
                    motor_speed = mapping_range(message.velocity, 0, 127, -0.05, -1.0)
                    kit.motor1.throttle = motor_speed
            
                # play motor 3
                elif message.note == motor_3_trigger:
                    print('motor 3 on')
                    motor_speed = mapping_range(message.velocity, 0, 127, -0.1, -0.2)
                    kit.motor3.throttle = motor_speed
            
                # play motor 4
                elif message.note == motor_4_trigger:
                    print('motor 4 on')
                    motor_speed = mapping_range(message.velocity, 0, 127, -0.1, -0.15)
                    kit.motor4.throttle = motor_speed
                
                # REHEARSAL LETTERS
                elif message.note == letter_A:
                    current_audio_sample = get_rehearsal_letter(0, this_device)
                elif message.note == letter_B:
                    current_audio_sample = get_rehearsal_letter(1, this_device)        
                elif message.note == letter_C:
                    current_audio_sample = get_rehearsal_letter(2, this_device)
                elif message.note == letter_D:
                    current_audio_sample = get_rehearsal_letter(3, this_device)        
                elif message.note == letter_E:
                    current_audio_sample = get_rehearsal_letter(4, this_device)
                elif message.note == letter_F:
                    current_audio_sample = get_rehearsal_letter(5, this_device)        
                elif message.note == letter_G:
                    current_audio_sample = get_rehearsal_letter(6, this_device)
                elif message.note == letter_H:
                    current_audio_sample = get_rehearsal_letter(7, this_device)        
                elif message.note == letter_I:
                    current_audio_sample = get_rehearsal_letter(8, this_device)        
                                             
            
                elif message.note == volume_up_trigger:
                    volume_up()
                elif message.note == volume_down_trigger:
                    volume_down()

                elif message.note == shutdown_trigger:
                    print('shut down')
                    break

            # NOTE OFF
            elif message.type == 'note_off' or (message.type == 'note_on' and message.velocity ==0):
                print(f"note off {message.note}")
                
                if message.note ==48:
                    print('stopping audio')
                    mute_mixer()
                    
                elif message.note == motor_1_trigger:
                    print('motor 1 off')
                    kit.motor1.throttle = 0
                    
                elif message.note == motor_3_trigger:
                    print('motor 3 off')
                    kit.motor3.throttle = 0
                    
                elif message.note == motor_4_trigger:
                    print('motor 4 off')
                    kit.motor4.throttle = 0              
                    

                
except KeyboardInterrupt:
    print('exit')
    
#finally:
    #shutdown_pi()
    
    
                    
                    
                    
                    
