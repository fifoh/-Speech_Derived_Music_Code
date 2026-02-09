from serial.tools import list_ports
import serial, time

def find_uno(baudrate=115200, timeout=1):
    for port in list_ports.comports():
        try:
            s = serial.Serial(port.device, baudrate, timeout=timeout)
            time.sleep(2)  # allow reset
            for _ in range(3):  # try 3 times
                s.write(b"IDENTIFY\n")
                resp = s.readline().strip()
                print(f"Probing {port.device}, got: {resp!r}")
                if resp == b"UNO_READY":
                    print("Found Uno on", port.device)
                    return s
                time.sleep(0.5)
            s.close()
        except Exception:
            continue
    raise IOError("Arduino Uno not found")
    
from serial.tools import list_ports
import serial, time

def find_motoron_r4(baudrate=115200, timeout=1):
    for port in list_ports.comports():
        # filter by VID/PID of R4 Minima
        if (port.vid, port.pid) != (0x2341, 0x0069):
            continue
        try:
            s = serial.Serial(port.device, baudrate, timeout=timeout)
            time.sleep(3)  # allow R4 Minima to reset
            for _ in range(5):  # try handshake 5 times
                s.write(b"IDENTIFY\n")
                resp = s.readline()
                print(f"Probing {port.device}, got raw: {resp!r}")
                if b"MOTORS_READY" in resp:
                    print("Found Motoron R4 Minima on", port.device)
                    return s
                time.sleep(0.5)
            s.close()
        except Exception as e:
            print(f"Failed on {port.device}: {e}")
            continue
    raise IOError("Motoron R4 Minima not found")

# Example usage
ser_motoron = find_motoron_r4()
    
# find the Uno for LED's using handshake
ser = find_uno()

active_motors = set()  # global 

# note: LED's are set for channels 1 - 9 (not 0 - 8 as on board, to align with motor control, this works)
def control_LED(channel, brightness):
    
    # map value to input for LEDs
    LED_value = int(round(brightness * 2048)) # 4095 max for LED's clamped on arduino, changed to be less
    
    LED_value = max(0, min(4095, int(LED_value)))
    
    cmd_str = f"{channel-1} {LED_value}\n"
    
    ser.write(cmd_str.encode()) # this maps the brightness
    ser.flush()
    time.sleep(0.002)   
    
# motor control
def control_motors(motor, speed, serial_conn=ser_motoron):
    """Send motor speed command to motor Arduino."""
    global active_motors
    
    # Clamp motor index
    motor = max(1, min(9, motor))
    
    # Define min and max motor command (non-zero min)
    MOTOR_MIN = 150  # minimum command for movement
    MOTOR_MAX = 400  # maximum command
    
    if speed <= 0:
        MOTOR_value = 0
    else:
        # Map speed (0.0-1.0) to MOTOR_MIN-MOTOR_MAX
        MOTOR_value = int(round(MOTOR_MIN + speed * (MOTOR_MAX - MOTOR_MIN)))
        MOTOR_value = min(MOTOR_value, MOTOR_MAX)  # clamp to max
    
    # Send command to Arduino
    cmd = f"{motor} {MOTOR_value}\n"
    serial_conn.write(cmd.encode('utf-8'))
    serial_conn.flush()
    time.sleep(0.002)  # short delay to avoid congestion

    # Track currently active motors
    if abs(MOTOR_value) > 0:
        active_motors.add(motor)
    else:
        active_motors.discard(motor)

def allOFF():
    """Turn off only the motors/LEDs that are currently active."""
    global active_motors

    if not active_motors:
        return

    for motor_id in list(active_motors):
        control_motors(motor_id, 0)
        control_LED(motor_id, 0)

    active_motors.clear()
    
# word stuff:

import numpy as np

# specify total phrase duration // input 0. - 1. // output 0.1 - 1.4 (seconds)
def generate_phrase_duration(input_val: float) -> float:
    clamped_input = max(0.0, min(1.0, input_val))
    min_output = 0.3 # was 0.1
    max_output = 1.7 # was 1.4
    output_span = max_output - min_output
    return round(min_output + (clamped_input * output_span), 3)

# specify number of notes in phrase
def generate_num_notes(input_val: float) -> float:
    clamped_input = max(0.0, min(1.0, input_val))
    min_output = 2
    max_output = 6 # was 6
    output_span = max_output - min_output
    return round(min_output + (clamped_input * output_span))

# utility for mapping
def map_minus1_to_1_to_0_to_1(x):
    import numpy as np
    x = np.array(x)
    return (x + 1) / 2

# CURVES: these are used for density, amplitude, onsets
# interpolates between a list of pre-defined curves
FAMILIES = [
    "parabola", "up_diagonal", "down_diagonal", "flat_line", "low_flat_line",
    "inverted_pulse", "s_shape", "reverse_s_shape",
    "sinusoid", "sinusoid_2", "damped_wave",
    "gaussian_pulse", "gaussian_pulse2", "gaussian_pulse3", "gaussian_shifted",
    "v_shape", "reverse_v_shape",
    "step", "reverse_step",
    "exp_rise", "exp_fall",
    "half_sine", "reverse_half_sine",
    "quick_drop"
]

def get_archetype_curve(family_name, n_points=200):
    """
    Generates a single "archetype" curve for a given family.
    Returns an array y of length n_points, normalized to [-1, 1].
    """
    t = np.linspace(-1, 1, n_points)
    y = np.zeros_like(t)
    if family_name == "parabola": y = t**2
    elif family_name == "up_diagonal": y = t
    elif family_name == "down_diagonal": y = -t
    elif family_name == "flat_line": y = np.ones_like(t)
    elif family_name == "low_flat_line": y = np.zeros_like(t)
    elif family_name == "inverted_pulse": y = -np.exp(-20 * t**2)
    elif family_name == "s_shape": y = t**3
    elif family_name == "reverse_s_shape": y = -t**3
    elif family_name == "sinusoid": y = np.cos(np.pi * t)
    elif family_name == "sinusoid_2": y = np.cos(np.pi * t + np.pi/2)
    elif family_name == "damped_wave": y = np.exp(-2.0 * (t + 1)) * np.sin(4 * (t + 1))
    elif family_name == "gaussian_pulse":
        y = np.exp(-30 * t**2)
        y = 2 * (y - np.min(y)) / (np.max(y) - np.min(y)) - 1  # rescale to [-1, 1]

    elif family_name == "gaussian_pulse2":
        y = np.exp(-30 * (t - 0.5)**2)
        y = 2 * (y - np.min(y)) / (np.max(y) - np.min(y)) - 1

    elif family_name == "gaussian_pulse3":
        y = np.exp(-30 * (t + 0.5)**2)
        y = 2 * (y - np.min(y)) / (np.max(y) - np.min(y)) - 1

    elif family_name == "gaussian_shifted":
        mu = 0.3
        y = np.exp(-30 * (t - mu)**2)
        y = 2 * (y - np.min(y)) / (np.max(y) - np.min(y)) - 1
    elif family_name == "v_shape": y = np.abs(t)
    elif family_name == "reverse_v_shape": y = -np.abs(t)
    elif family_name == "step": y = np.tanh(5 * t)
    elif family_name == "reverse_step": y = -np.tanh(5 * t)
    elif family_name == "exp_rise": y = 1 - np.exp(-5 * t)
    elif family_name == "exp_fall": y = np.exp(-5 * t)
    elif family_name == "half_sine": y = np.sin(np.pi * t / 2)
    elif family_name == "reverse_half_sine": y = np.cos(np.pi * t / 2)
    elif family_name == "quick_drop": y = 1 - np.tanh(5 * t)
        
    if np.max(np.abs(y)) > 1e-6: y = y / np.max(np.abs(y))        

        
    return y

def get_all_archetypes(families_list, n_points=200):
    return [get_archetype_curve(name, n_points) for name in families_list]

def interpolate_between_curves(interp_val, all_curves):
    num_curves = len(all_curves)
    continuous_index = np.clip(interp_val * (num_curves - 1), 0, num_curves - 1)
    idx1 = int(np.floor(continuous_index))
    idx2 = int(np.ceil(continuous_index))
    if idx1 == idx2:
        return all_curves[idx1]
    else:
        weight = continuous_index - idx1
        return (1 - weight) * all_curves[idx1] + weight * all_curves[idx2]

ALL_ARCHETYPES = get_all_archetypes(FAMILIES)

def get_interpolated_curve_as_list(interp_val: float) -> list:
  # Takes a float between 0 and 1 and returns the interpolated curve as a list.
    if not 0 <= interp_val <= 1:
        raise ValueError("Input value must be between 0 and 1.")
    interpolated_curve_np = interpolate_between_curves(interp_val, ALL_ARCHETYPES)
    return interpolated_curve_np.tolist()

# Get a list of onsets from the density curve, total phrase length, and num_notes parameters
def generate_onsets_deterministic(density_curve, phrase_duration, num_notes):
    if num_notes == 0:
        return []

    # Convert density curve to a probability distribution
    density_as_array = np.array(density_curve, dtype=float)
    if density_as_array.sum() == 0:
        # If curve is all zeros, distribute notes evenly
        density_as_array = np.ones_like(density_as_array)
    pdf = density_as_array / density_as_array.sum()
    # Create the Cumulative Distribution Function (CDF)
    cdf = np.cumsum(pdf)
    num_bins = len(density_curve)
    bin_width = phrase_duration / num_bins

    # Create evenly spaced points in the probability domain (0 to 1)
    target_probabilities = [(i + 0.5) / num_notes for i in range(num_notes)]
    onsets = []
    for prob in target_probabilities:
        # Find the first bin index where the CDF value exceeds target probability
        # This is the inverse of the CDF
        bin_index = np.searchsorted(cdf, prob)
        # Ensure index is within bounds
        bin_index = min(bin_index, num_bins - 1)
        # The onset time is the start of that bin
        onset_time = bin_index * bin_width
        onsets.append(onset_time)

    return onsets

def get_amplitudes(onsets, amplitude_curve, phrase_duration):
    amplitudes = []
    num_points_in_curve = len(amplitude_curve)

    for onset in onsets:
        position = min(onset / phrase_duration, 1.0)
        curve_index = int(round(position * (num_points_in_curve - 1)))
        raw_amplitude = amplitude_curve[curve_index]
        # Scale to desired linear range first
        linear_amp = 0.2 + raw_amplitude * 0.8
        # Apply perceptual curve (exaggerates differences)
        perceptual_amp = linear_amp ** 2  # or **2.2 for stronger contrast
        amplitudes.append(perceptual_amp)

    return amplitudes

# Other parameters are done by interpolating between sequences of 'paths'

from itertools import cycle, islice

# auto extend repeating sequences (utility)
def repeat_to_length(seq, length):
    return list(islice(cycle(seq), length))

# Motor sequences 
Msequence1 = [0,1]
Msequence2 = [8,2,5]
Msequence3 = [4,7,8,5]
Msequence4 = [6,7]
Msequence5 = [5,8,2]
Msequence6 = [0,4,6,7]
Msequence7 = [3,6,2,5]
Msequence8 = [7,8,0,1]
Msequence9 = [1,4,7]
Msequence10 = [3,4,5]
Msequence11 = [8,3,6,7,0]
Msequence12 = [1,2,7]
Msequence13 = [6,3]
Msequence14 = [8,4,1,5]
Msequence15 = [2,1,0,4]
Msequence16 = [7,4]
Msequence17 = [8,1]

# to interpolate between sequences
def interpolate_simple_repeats(A, B, t):
    max_len = max(len(A), len(B))
    result = []
    for i in range(max_len):
        # choose from A or B based on t
        if i / max_len < (1-t):
            if i < len(A):
                result.append(A[i])
        else:
            if i < len(B):
                result.append(B[i])
    return result

# predefined paths for motor sequences (these were regions before, didn't change the name)
regions = [Msequence1, Msequence2, Msequence3, Msequence4,
           Msequence5, Msequence6, Msequence7, Msequence8,
           Msequence9, Msequence10, Msequence11, Msequence12,
           Msequence13, Msequence14, Msequence15, Msequence16, Msequence17
]

# returns the interpolated path
def path_at(u, regions=regions):
    u = max(0.0, min(1.0, u))
    num_regions = len(regions)
    pos = u * (num_regions - 1)
    i = int(np.floor(pos))
    t = pos - i
    if i >= num_regions - 1:
        return regions[-1]
    
    return interpolate_simple_repeats(regions[i], regions[i+1], t)

# ARTICULATION follow same idea as the paths for notes:
# S // staccato (short fixed length)
# L // legato (full length until next onset - if final note is legato, make it same duration as previous ioi)
# Ss // Stacatissimo (fixed very short duration)
# D // detatched (50 percent note length)

Asequence1 = ['S', 'S', 'S', 'S']
Asequence2 = ['L','S', 'Ss', 'L']
Asequence3 = ['L', 'L', 'Ss']
Asequence4 = ['L', 'S', 'S', 'S', 'S']
Asequence5 = ['D','L','L', 'D', 'L']
Asequence6 = ['S','S','L','Ss', 'L', 'S']
Asequence7 = ['L', 'D', 'S']
Asequence8 = ['D', 'L', 'D', 'L']
Asequence9 = ['S', 'D', 'D', 'L']
Asequence10 = ['L', 'D', 'S', 'Ss', 'Ss', 'Ss']
Asequence11 = ['L', 'Ss', 'S']
Asequence12 = ['Ss', 'Ss', 'Ss']
Asequence13 = ['D', 'D', 'D']
Asequence14 = ['Ss', 'L', 'Ss', 'L', 'D']
Asequence15 = ['S', 'Ss', 'Ss', 'Ss', 'S']
Asequence16 = ['Ss','L','L', 'L', 'L']
Asequence17 = ['D', 'D', 'D', 'D']
Asequence18 = ['L', 'Ss', 'S', 'D']
Asequence19 = ['Ss','L','Ss', 'L', 'L']
Asequence20 = ['D', 'L', 'L', 'S']
Asequence21 = ['L', 'L', 'L', 'S']
Asequence22 = ['Ss', 'L', 'S', 'S', 'D']
Asequence23 = ['Ss', 'L', 'Ss', 'L', 'Ss', 'L'] 
Asequence24 = ['S', 'S', 'S', 'D']
Asequence25 = ['L', 'S', 'Ss']
Asequence26 = ['D', 'L', 'D', 'S']
Asequence27 = ['S', 'Ss' 'Ss']
Asequence28 = ['D', 'D', 'D', 'S']

articulation_regions = [Asequence1, Asequence2, Asequence3, Asequence4,
           Asequence5, Asequence6, Asequence7, Asequence8,
           Asequence9, Asequence10, Asequence11, Asequence12,
           Asequence13, Asequence14, Asequence15, Asequence16,
            Asequence17, Asequence18, Asequence19, Asequence20,
            Asequence21, Asequence22, Asequence23, Asequence24,
                        Asequence25, Asequence26, Asequence27, Asequence28
]

# individual amplitude sequences: fade in strong, fade in mild, flat, fade out strong, fade out mild
# strong should be from 0 percent amplitude, wheras mild should be from 60 percent amplitude
# Fi = fade in strong
# Fo = fade out strong
# Fl = flat
# Fiw = fade in weak
# Fow = fade out weak
Isequence1 = ['Fi', 'Fl', 'Fl', 'Fl']
Isequence2 = ['Fl','Fl', 'Fl', 'Fl']
Isequence3 = ['Fi', 'Fl', 'Fo']
Isequence4 = ['Fi', 'Fi', 'Fi', 'Fi', 'Fi']
Isequence5 = ['Fi','Fo','Fi', 'Fo']
Isequence6 = ['Fiw','Fo','Fow','Fiw', 'Fo']
Isequence7 = ['Fow', 'Fow', 'Fow']
Isequence8 = ['Fl', 'Fiw', 'Fl', 'Fiw']
Isequence9 = ['Fiw', 'Fiw', 'Fiw', 'Fiw']
Isequence10 = ['Fl', 'Fow', 'Fl', 'Fl', 'Fiw', 'Fl']
Isequence11 = ['Fl', 'Fl', 'Fow']
Isequence12 = ['Fow', 'Fow', 'Fow']
Isequence13 = ['Fi', 'Fow', 'Fo']
Isequence14 = ['Fl', 'Fi', 'Fl', 'Fi', 'Fl']
Isequence15 = ['Fi', 'Fi', 'Fi', 'Fl']
Isequence16 = ['Fiw', 'Fow', 'Fiw', 'Fow']
Isequence17 = ['Fow', 'Fiw', 'Fo', 'Fo']
Isequence18 = ['Fo', 'Fo', 'Fo', 'Fo', 'Fo']
Isequence19 = ['Fl', 'Fo', 'Fo', 'Fl']
Isequence18 = ['Fl', 'Fi', 'Fl', 'Fi']
Isequence19 = ['Fo', 'Fi', 'Fo']
Isequence20 = ['Fl', 'Fiw', 'Fo', 'Fi', 'Fiw', 'Fo']
Isequence21 = ['Fi', 'Fl', 'Fi', 'Fl', 'Fo']
Isequence22 = ['Fi', 'Fo', 'Fo']
Isequence23 = ['Fi', 'Fo', 'Fl', 'Fi']
Isequence24 = ['Fo', 'Fi', 'Fi']

individual_amplitude_regions = [Isequence1, Isequence2, Isequence3, Isequence4,
           Isequence5, Isequence6, Isequence7, Isequence8,
           Isequence9, Isequence10, Isequence11, Isequence12,
           Isequence13, Isequence14, Isequence15, Isequence16, Isequence17, Isequence18,
                                Isequence19, Isequence20, Isequence21, Isequence22, Isequence23, Isequence24
]

import pickle
import joblib

# Load the word vectors (reduced 7 dims)
with open('/home/fin/Documents/pickled_7dim_vectors.pkl', 'rb') as file:
    STRETCHED_VECTORS = pickle.load(file)
    
# Load the dictionary that maps words to their index (row number)
WORD_TO_INDEX = joblib.load('/home/fin/Documents/word_to_index.joblib')
INDEX_TO_WORD = [word for word, index in sorted(WORD_TO_INDEX.items(), key=lambda item: item[1])]

def get_stretched_params(word):
    try:
        idx = WORD_TO_INDEX[word.lower()]
        vector = STRETCHED_VECTORS[idx]
        return vector
    except KeyError:
        print(f"'{word}' not in vocab.")
        return None


# In[3]:


# motor code to test (play word on motors)

# motor code to test (play word on motors)
import numpy as np
import time

STACCATISSIMO_DUR = 0.05
STACCATO_DUR = 0.1

def precompute_events(word, max_val=0.5, max_motor_updates_per_sec=50):
    events = []

    params = get_stretched_params(word)
    note_sequence = path_at(params[0])  # integers 0–8
    phrase_duration = generate_phrase_duration(params[1])
    num_notes = generate_num_notes(params[2])
    density_curve = get_interpolated_curve_as_list(params[3])
    amplitude_curve = get_interpolated_curve_as_list(params[4])
    articulation_path = path_at(params[5], articulation_regions)
    individual_amplitude_path = path_at(params[6], individual_amplitude_regions)

    note_sequence = repeat_to_length(note_sequence, num_notes)
    articulation_sequence = repeat_to_length(articulation_path, num_notes)

    density_curve = map_minus1_to_1_to_0_to_1(density_curve)
    amplitude_curve = map_minus1_to_1_to_0_to_1(amplitude_curve)

    onsets = generate_onsets_deterministic(density_curve, phrase_duration, num_notes)
    amplitudes = get_amplitudes(onsets, amplitude_curve, phrase_duration)
    gamma = 2.5

    for i in range(num_notes):
        motor_id = note_sequence[i] + 1
        main_amp = amplitudes[i] ** gamma

        # Note duration
        if i < num_notes - 1:
            ioi = onsets[i+1] - onsets[i]
        else:
            ioi = onsets[i] - onsets[i-1] if num_notes > 1 else 0.5
        ioi = max(0.01, ioi)

        art = articulation_sequence[i]
        if art == 'L':
            note_duration = ioi
        elif art == 'D':
            note_duration = ioi * 0.5
        elif art == 'S':
            note_duration = 0.1
        else:
            note_duration = 0.05
        note_duration = min(note_duration, ioi)

        if note_duration <= 0:
            continue

        motor_val = main_amp * max_val
        if 0.0 < motor_val < 0.15:
            motor_val = 0.15

        # ON events
        events.append({"time": onsets[i], "motor": motor_id, "motor_val": motor_val, "led_val": None})
        events.append({"time": onsets[i], "motor": motor_id, "motor_val": None, "led_val": main_amp * max_val})

        # Staggered OFF times to prevent USB contention
        off_time_led = onsets[i] + note_duration
        off_time_motor = off_time_led + 0.02  # 20 ms after LED

        events.append({"time": off_time_led, "motor": motor_id, "motor_val": None, "led_val": 0.0})
        events.append({"time": off_time_motor, "motor": motor_id, "motor_val": 0.0, "led_val": None})

    events.sort(key=lambda e: e["time"])
    return events


def playback_events(events):
    start_time = time.time()
    for e in events:
        if stop_flag:
            print("Stop flag received during playback.")
            allOFF()
            return

        now = time.time()
        wait_time = e["time"] - (now - start_time)
        if wait_time > 0:
            time.sleep(wait_time)

        if e["motor_val"] is not None:
            control_motors(e["motor"], e["motor_val"])
        if e["led_val"] is not None:
            control_LED(e["motor"], e["led_val"])

    # final safety
    allOFF()

import string

def playback_word(words):
    """
    Play one or more words in sequence (e.g. 'LESSON ONE:').
    Writes progressively to /tmp/current_word.txt:
    Uses punctuation-free words for playback, but keeps punctuation
    in the text file writes (which trigger visuals).
    """
    # Clean version for playback (no punctuation)
    cleaned = words.translate(str.maketrans("", "", string.punctuation))
    cleaned_word_list = cleaned.split()
    original_word_list = words.split()

    for i in range(len(cleaned_word_list)):
        # Write the cumulative phrase using the *original* words (with punctuation)
        cumulative_phrase = " ".join(original_word_list[:i+1])
        with open("/tmp/current_word.txt", "w") as f:
            f.write(cumulative_phrase)

        # Print for feedback
        print(f"Current phrase: '{cumulative_phrase}'")

        # Play just this clean word (without punctuation)
        current_word = cleaned_word_list[i]
        events = precompute_events(current_word, max_val=0.7)
        playback_events(events)

        # Add a short gap between words (except after the last)
        if i < len(cleaned_word_list) - 1:
            time.sleep(0.05)

    # Clear file at the end
    with open("/tmp/current_word.txt", "w") as f:
        f.write("")


import keyboard
import time

# === CONTROL LOOP ===

sequences = [
    # ~10 mins total
    [("WORD GAMES", 3.5),  
     ("This machine turns", 0.05),
     ("words", 0.2),
     ("words", 0.2),
     ("words", 0.2),
     ("words", 0.2),
     ("words", 0.2),
     ("words into patterns", 0.05),
     ("of light", 0.1), ("and sound", 0.05),
     ("sound", 0.3),
     ("sound", 0.3),
     ("sound", 0.3),
     ("sound.", 3.6), # ? 
     
     ("Each word is", 0.05), ("stored as a", 0.05),
     ("sequence", 0.2),
     ("sequence", 0.2),
     ("sequence", 0.2),
     ("sequence", 0.2),
     ("sequence of numbers", 0.05),
     ("called a", 0.05),
     ("word embedding", 0.05),
     ("embedding", 0.3),
     ("embedding", 0.3),
     ("embedding", 0.3),     
     ("embedding", 0.3),
     ("embedding", 0.3),
     ("embedding.", 3.5),
     
     ("These numbers describe", 0.05), ("how words relate", 0.05),
     ("to each other", 0.05),
     ("other", 0.2),
     ("other", 0.2),
     ("other", 0.2),
     ("other", 0.2),
     ("other", 0.2),
     ("other.", 3.4),
     
     ("Words which appear", 0.05), ("in a similar context", 0.05),
     ("produce similar", 0.05),
     ("similar", 0.25),
     ("similar", 0.25),
     ("similar", 0.25),
     ("similar", 0.25),
     ("similar", 0.25),    
     ("similar patterns:", 2.2),
     
     ("RED,", 0.4), ("GREEN,", 0.4), ("BLUE,", 0.4), ("YELLOW.", 0.4),
     ("RED,", 0.4), ("GREEN,", 0.4), ("BLUE,", 0.4), ("YELLOW.", 0.4),
     ("RED,", 0.4), ("GREEN,", 0.4), ("BLUE,", 0.4), ("YELLOW.", 0.4),
     
     ("WITH", 0.7), ("WITHOUT", 0.7),
     ("WITH", 0.7), ("WITHOUT", 0.7),
     ("WITH", 0.7), ("WITHOUT", 0.7),
     
     ("ALWAYS", 1.0), ("NEVER", 1.0),
     ("ALWAYS", 1.0), ("NEVER", 1.0),
     ("ALWAYS", 1.0), ("NEVER", 1.0),
     ("ALWAYS", 1.0), ("NEVER", 2.0),     
 
     ("Each number", 0.1), ("controls one aspect", 0.1),
     ("aspect", 0.2),
     ("aspect", 0.2),
     ("aspect", 0.2),
     ("aspect", 0.2),
     ("aspect", 0.2),     
     ("of the pattern,", 0.1),         
     
     ("such as", 0.1), ("order, or direction", 0.1),
     ("or direction", 0.1),
     ("or direction", 0.1),
     ("or direction", 0.1),
     ("or direction", 0.1),
     ("direction", 0.1),
     ("direction", 0.1),
     ("direction", 3.5),     
     
     ("Words which are", 0.1), ("not closely related", 0.1),
     ("produce different patterns:", 0.1),
     ("patterns", 0.2),
     ("patterns", 0.2),
     ("patterns", 0.2),
     ("patterns", 0.2),
     ("patterns", 0.2),
     ("patterns:", 0.3),
     
     ("ELEPHANT,", 2.0), ("TACTILE,", 2.0), ("AUTUMN,", 2.0), ("56,", 2.0),
     ("REPEAT,", 2.0),
     ("REPEAT,", 2.0),
     ("REPEAT,", 2.0),
     ("REPEAT,", 2.0),
     ("REPEAT,", 2.0),
     ("REPEAT,", 2.0),
     ("REPEAT.", 2.0),
     
     
     # TIME: 4 minutes
     ],
    
     [
     
     ("The objects", 0.2),
     ("objects", 0.2),
     ("objects", 0.2),
     ("objects", 0.2),
     ("objects", 0.2),
     ("objects on", 0.1),
     ("the surface", 0.1),
     ("also determine", 0.3),
     ("determine", 0.3),
     ("determine", 0.3),
     ("determine", 0.3),
     ("determine", 0.3),     
     ("the sound", 0.1),
     ("sound", 0.1),
     ("sound", 0.1),
     ("sound", 0.1),     
     ("sound", 3.0),     
     
     ("Springs,", 0.1),
     ("sticky tape,", 0.3),
     ("plastics,", 0.3),
     ("elastic bands", 0.3),
     ("fabrics", 0.3),
     ("brushes", 0.3),
     ("wires", 0.3),
     ("strings,", 0.3),
     ("paper,", 0.3),
     ("cardboard", 0.3),
     ("and so on", 0.2),
     ("so on", 0.2),
     ("so on", 0.2),
     ("so on", 0.2),
     ("so on", 0.2),
     ("so on.", 0.2),
     ("so on", 0.2),
     ("so on", 0.2),
     ("so on", 0.2),
     ("so on.", 3.5) # 1:20 minutes additional, 5:20 total.      
     
     ],
    
     [
     ("A semantic field", 0.1), ("is a set ", 0.1),
     ("of words, ", 0.2),
     ("words, ", 0.2),
     ("words, ", 0.2), 
     ("words, ", 0.2),
     ("words, ", 0.2), 
     ("grouped by meaning ", 0.1),
     ("or theme.", 2.0),
     
     ("This final", 0.1), 
     ("section begins", 0.1),
     ("with letters", 0.2),
     ("letters", 0.2),
     ("letters", 0.2),
     ("letters", 0.2),
     ("letters", 0.2),
     ("letters.", 3.0),
      
     ("L", 0.01),
     ("B", 0.01), 
     ("W", 0.01),
     ("G", 0.01),
     ("N", 0.01),
     ("C", 0.01),
     ("J", 0.01),
     ("P", 0.01),
     ("H", 0.01),
     ("Q", 0.01),
     ("F", 0.01),      
     ("K", 0.01),
     ("Z", 0.01),
     ("X", 0.01),
     ("C", 0.01),
     ("V", 0.01),  
     
     ("11", 0.5),
     ("12", 0.5),
     ("13", 0.5),
     ("14", 0.5),
     ("15", 0.5),
     ("16", 0.5),
     ("17", 0.5),
     ("18", 0.5),
     ("19", 0.5),           
      
     ("TYPOS", 0.4),
     ("EDITS", 0.4),
     ("FIXES", 0.4),
     ("INSERTS", 0.4),
     ("TRIMS", 0.4),
     ("DELETES", 0.4),
     ("RECAPS", 0.4), 
     ("SUBS", 0.4),
     ("CLARIFIES", 0.4),
     ("RESTORES", 0.4),
     
     ("BRANCHES", 0.3),
     ("DIVIDED", 0.3), 
     ("FORMATION", 0.3),
     ("PORTIONS", 0.3),
     ("SPLIT", 0.3),
     ("SECTIONS", 0.3),
     ("WITHIN", 0.3),
     ("GROUPED", 0.3),
     
     ("THE", 0.05),
     ("OF", 0.05), 
     ("WHICH", 0.05),
     ("IN", 0.05),
     
     ("FOR", 0.05),
     ("AND", 0.05),
     ("WITH", 0.05),
     ("A", 0.05),
     
     ("BUT", 0.05),
     ("THEY", 0.05),
     ("THEM", 0.05),
     ("THEIR", 0.05),
     
     ("SCREEN", 0.1),
     ("VIEWING", 0.1),
     ("PICTURES", 0.1),
     ("PHOTOGRAPH", 0.1),
     ("DISPLAY", 0.1),
     ("IMAGES", 0.1),
     ("PRINTED", 0.1),
     ("COPIES", 0.1),
     
     ("100", 0.1),
     ("200", 0.1),
     ("300", 0.1),
     ("400", 0.1),
     ("500", 0.1),
     ("600", 0.1),
     ("700", 0.1),       
      
     ("RARELY", 1.0),
     ("OFTEN", 1.0),
     ("SOMETIMES", 1.0),     
     ("NOWADAYS", 1.0),
     ("GENERALLY", 1.0),
     ("OCCASIONALLY", 1.0),
     ("HISTORICALLY", 1.0),  
     ("FREQUENTLY", 1.0),   
     
     ("ESPECIALLY", 1.0),
     ("TRADITIONALLY", 1.0),
     ("REGULARLY", 1.0),
     ("PARTICULARLY", 1.0),
     
     ("NOUN", 0.1),
     ("PLURAL", 0.1),
     ("VERB", 0.1),
     ("SUFFIX", 0.1),
     ("POSSESSIVE", 0.1),
     ("NOMINATIVE", 0.1),
     ("ADJECTIVES", 0.1),
     
     ("RESISTOR", 0.1),
     ("CAPACITOR", 0.1),
     ("INDUCTOR", 0.1),
     ("RESONATORS", 0.1),
     ("OSCILLATORS", 0.1),
     ("RESONATORS", 0.1),
     ("INSULATORS", 0.1),
     ("PIEZOELECTRIC", 0.1),
     
     ("TRANSLATOR", 0.3),
     ("INTERPRETER", 0.3),
     ("LANGUAGES", 0.3),
     ("DIALECT", 0.3),
     ("FLUENTLY", 0.3),
     
     ("SOON", 0.35),
     ("RETURN", 0.35), 
     ("HOLD", 0.35),
     ("EVENTUALLY", 0.35),
     ("ABRUPTLY", 0.35),
     ("FINALLY", 0.35),
     
     ("STOP", 0.4),
     ("CEASE", 0.4),
     ("QUIT", 0.4),
     ("END", 0.4),
     ("FINISH", 0.4),
     ("END", 0.4),
     ("FINISH", 0.4),
     ("END", 0.4),
     ("FINISH", 0.4),
     ("FINAL", 0.4),
     ("END", 0.4),
     ("END", 0.4),
     ("END", 0.4),
     ("END", 0.4),
     ("END", 0.4),
     ("END", 0.4),
     ("END", 0.4),
     ("END", 0.4),
     ("END", 0.4),       
     ("END.", 0.4)
     
     
     # end     ... 4 minutes additional, 9:20 total (call it 10 minutes)
      
     ], 
]

seq_id = 0
stop_flag = False

def interruptible_sleep(duration, step=0.1):
    """Sleep for `duration` seconds, checking stop_flag regularly."""
    global stop_flag
    end_time = time.time() + duration
    while time.time() < end_time:
        if stop_flag:
            break
        time.sleep(min(step, end_time - time.time()))

def play_sequence(seq):
    global stop_flag
    stop_flag = False
    for word, gap in seq:  # unpack tuple (word, sleep_time)
        if stop_flag:
            break

        playback_word(word)   # blocks until motors/LEDs finish
        interruptible_sleep(gap)

    allOFF()


# === CONTROL LOOP (same as before) ===

print("Controls: h=reset, i=next seq, g=prev seq, f=play, a=stop")

try:
    while True:
        event = keyboard.read_event(suppress=True)
        if event.event_type != "down":
            continue
        key = event.name

        if key == "h":
            seq_id = 0
            print(f"Sequence reset to {seq_id}")
        elif key == "i":
            seq_id = (seq_id + 1) % len(sequences)
            print(f"Sequence changed to {seq_id}")
        elif key == "g":
            seq_id = (seq_id - 1) % len(sequences)
            print(f"Sequence changed to {seq_id}")
        elif key == "f":
            print(f"Playing sequence {seq_id}")
            play_sequence(sequences[seq_id])
        elif key == "a":
            print("Stop command received.")
            stop_flag = True
            allOFF()
except KeyboardInterrupt:
    print("Keyboard interrupt detected.")
finally:
    print("Ensuring all devices are off and serial flushed...")
    allOFF()