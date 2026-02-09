#!/usr/bin/env python
# coding: utf-8


# -----------------------------
# This code gets serial data from the puredata patch, and outputs to the motors and LED's

# puredata >> this script >> motors and lights

# ----------------------------

# In[ ]:
print("STARTING")

import serial
import time

ser = None

def initialize_led_control(port='/dev/ttyACM0'): # set port manually here - diff. for rpi / windows etc.
    global ser
    ser = serial.Serial(
        port=port,
        baudrate=115200,
        timeout=0, # was 0.05
        write_timeout=0,
        inter_byte_timeout=0.01
    )
    ser.dtr = None
    ser.reset_input_buffer()

def turn_LED_on(led_num, brightness):
    ser.write(f"{led_num} {brightness}\n".encode())
    ser.flush()

def turn_LED_off(led_num):
    ser.write(f"{led_num} 0\n".encode())
    ser.flush()

def close_led_control():
    if ser and ser.is_open:
        ser.close()

initialize_led_control()

import socket
from adafruit_motorkit import MotorKit
from adafruit_motor import motor

# Initialize all kits
kit1 = MotorKit()
kit2 = MotorKit(address=0x61)
kit3 = MotorKit(address=0x62)
kit4 = MotorKit(address=0x63)

kit1.frequency = 1600
kit2.frequency = 1600
kit3.frequency = 1600
kit4.frequency = 1600

kit1.motor1.decay_mode = motor.SLOW_DECAY # affects motor noise a bit
kit1.motor2.decay_mode = motor.SLOW_DECAY
kit1.motor3.decay_mode = motor.SLOW_DECAY
kit1.motor4.decay_mode = motor.SLOW_DECAY

kit2.motor1.decay_mode = motor.SLOW_DECAY
kit2.motor2.decay_mode = motor.SLOW_DECAY
kit2.motor3.decay_mode = motor.SLOW_DECAY
kit2.motor4.decay_mode = motor.SLOW_DECAY

kit3.motor1.decay_mode = motor.SLOW_DECAY
kit3.motor2.decay_mode = motor.SLOW_DECAY
kit3.motor3.decay_mode = motor.SLOW_DECAY
kit3.motor4.decay_mode = motor.SLOW_DECAY

kit4.motor1.decay_mode = motor.SLOW_DECAY
kit4.motor2.decay_mode = motor.SLOW_DECAY
kit4.motor3.decay_mode = motor.SLOW_DECAY
kit4.motor4.decay_mode = motor.SLOW_DECAY

# Manually define motor mapping
motor_mapping = {
    0: kit4.motor3,
    1: kit4.motor4,
    2: kit4.motor2,
    3: kit4.motor1,
    4: kit3.motor1,
    5: kit3.motor4,
    6: kit3.motor2,
    7: kit3.motor3,
    8: kit2.motor1,
    9: kit2.motor2,
    10: kit2.motor4,
    11: kit2.motor3,
    12: kit1.motor3,
    13: kit1.motor1,
    14: kit1.motor2,
    15: kit1.motor4
}

led_mapping = {
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    9: 9,
    10: 11,
    11: 10,
    12: 12,
    13: 13,
    14: 14,
    15: 15
}

def setmotorthrottle(motor_number, throttle_value):
    # Ensure motor_number is within valid range
    motor_number = max(0, min(15, motor_number))
    
    # Get the motor object from the mapping
    motor = motor_mapping[motor_number]
    
    # Set the throttle
    motor.throttle = throttle_value

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
sock.bind(("localhost", 3001))  # Must match Pd's port!

for x in range(25):
    turn_LED_off(0)

print("Waiting for messages...")
try: 
    while True:
        data, addr = sock.recvfrom(1024)  # Buffer = 1024 bytes
        decoded_data = data.decode().strip()  # Remove whitespace
        print("Received:", decoded_data)

        # Parse
        if decoded_data.endswith(';'):
            decoded_data = decoded_data[:-1]  # Remove semicolon
        
        # Split into parts by whitespace and convert to int & float
        parts = decoded_data.split()  # Splits on any whitespace
        if len(parts) == 2:
            motornum = int(parts[0])      # First value as integer
            motorspeed = float(parts[1])   # Second value as float
            setmotorthrottle(motornum, motorspeed)
            # LEDs
            if motorspeed > 0:
                led_mapped = led_mapping[motornum]
                brightness = min(4095, int(motorspeed*4095))
                turn_LED_on(led_mapped, brightness)
            elif motorspeed == 0:
                led_mapped = led_mapping[motornum]
                turn_LED_off(led_mapped)
        else:
            print(f"Error: {decoded_data}")
    
except KeyboardInterrupt:
    print('Stopping server...')
finally:
    sock.close()  # close the socket
    print("Socket closed.")
    for x in range(0, 16):
        setmotorthrottle(x, 0) # turn off the motors
    
    for x in range(0, 25):
        turn_LED_off(x)
    close_led_control()
        
    print("STOP")        
    

# In[ ]:





