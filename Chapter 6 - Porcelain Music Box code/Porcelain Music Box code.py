#!/usr/bin/env python
# coding: utf-8

# -----------------------------------------
# THIS is the entire code for porcelain music box, in an installation setting

# user input >> playback

# -----------------------------------------


# In[3]:


import tensorflow as tf
import random
import time
import numpy as np
import pickle

import numpy as np
import random
import time
from itertools import permutations
# -------------------------------------------------------------------------------------------------- 
# https://github.com/NathanDuran/MRDA-Corpus/blob/master/README.md source for the dialogue acts dataset
def intersperse(lst, item):
    result = [item] * (len(lst) * 2 - 1)
    result[0::2] = lst
    return result
# -------------------------------------------------------------------------------------------------- 
# palette of patterns for generating material
perm_4 = list(permutations([1, 1, 2, 2], 4))
perm_3 = list(permutations([1, 1, 2, 2], 3))
combi_perm = perm_4 + perm_3
patternpallete = [list(i) for i in set(map(tuple, combi_perm))]
# -------------------------------------------------------------------------------------------------- 
# import needed data
with open('tokenizer_BASIC_6voices.pkl', 'rb') as fp:
    tokenizer = pickle.load(fp)
    
with open('vocabulary_BASIC_6voices.pkl', 'rb') as fp:
    vocabulary = pickle.load(fp)
# --------------------------------------------------------------------------------------------------     
# Load the TFLite model in TFLite Interpreter
interpreter = tf.lite.Interpreter('STM_words_BASIC_6voices.tflite')
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# setup initial input for model (random values)
temperature = 1.0 # was 1.0
random_samples_for_start = []
for x in range(0,64):
    sample = random.choice(vocabulary)
    random_samples_for_start.append(sample)
sample_vector = np.reshape(np.float32(np.array([tokenizer[i] for i in random_samples_for_start])), (64,1))
# -------------------------------------------------------------------------------------------------- 
# setup initial input for statement output:
ending_rhythm_value = 300
ending_amplitude_value = 60
# -------------------------------------------------------------------------------------------------- 
# define all the sounding functions
def create_statement(initial_duration, initial_amplitude):
    gracenotes_on_or_off = random.choice([0,1])
    if gracenotes_on_or_off == 0: # if grace notes on
        
        # rhythm ------------------------------------------------------------
        full_list_rhythm = []
        decide_on_gracenotes_or_not = random.choice(list(range(0,4)))
        samples_to_generate = random.choice(list(range(4,6)))
        starting_value = initial_duration
        ending_rhythm_value = random.choice(list(range(150,600)))
        x1 = np.geomspace(starting_value, ending_rhythm_value, samples_to_generate, endpoint = False)
        full_list_rhythm.append(x1)
        rhythm = [round(item) for sublist in full_list_rhythm for item in sublist]          
        
        # amplitude ------------------------------------------------------------
        full_list_amplitude = []
        starting_amplitude_value = initial_amplitude
        ending_amplitude_value = random.choice(list(range(40,100))) # full range 0 - 127, reduced for statement
        x_amp = np.geomspace(starting_amplitude_value, ending_amplitude_value, len(rhythm), endpoint = False)
        full_list_amplitude.append(x_amp)
        amplitude = [round(item) for sublist in full_list_amplitude for item in sublist]          
        
        # note pattern ------------------------------------------------------------
        notepattern = []
        note_pattern_choices = random.sample(patternpallete, k=5)
        note_pattern_choice =  [item for sublist in note_pattern_choices for item in sublist] 
        for x in range(0, 50):
            notepattern.append(note_pattern_choice)
        notepattern =  [item for sublist in notepattern for item in sublist]    
        root_patterns_used = []
        for x in range(0, len(note_pattern_choices)):
            root_patterns_used.append(patternpallete.index(note_pattern_choices[x]))
        final_note_pattern = notepattern[0:len(rhythm)]             

        # and now the grace notes ------------------------------------------------------------
        repeated_ones = [1,1]
        repeated_twos = [2,2]
        pickonesortwos = random.choice([0,1])

        possible_gracenote_indexes = []
        if pickonesortwos == 0:
            possible_gracenote_indexes_ones = [((i+len(repeated_ones))-1) for i in range(len(final_note_pattern)) if final_note_pattern[i:i+len(repeated_ones)] == repeated_ones]
            if possible_gracenote_indexes_ones ==[]:
                # intersperse with rest
                withinbetween_rests_rhythm = intersperse(rhythm, 20)
                withinbetween_rests_amplitude = intersperse(amplitude, 0)
                withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
                withinbetween_rests_rhythm.append(20)
                withinbetween_rests_amplitude.append(0)
                withinbetween_rests_note_pattern.append(0)                      
                total_duration = sum(withinbetween_rests_rhythm)
                return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    
         
            if possible_gracenote_indexes_ones !=[]:
                gracenoteIndex = random.choice(possible_gracenote_indexes_ones)
                final_note_pattern.insert(gracenoteIndex, 2)
                rhythm.insert(gracenoteIndex, round(starting_value/5))
                amplitude.insert(gracenoteIndex, round(starting_amplitude_value/5))
                # intersperse with rest 
                withinbetween_rests_rhythm = intersperse(rhythm, 20)
                withinbetween_rests_amplitude = intersperse(amplitude, 0)
                withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
                withinbetween_rests_rhythm.append(20)
                withinbetween_rests_amplitude.append(0)
                withinbetween_rests_note_pattern.append(0)                                     
                total_duration = sum(withinbetween_rests_rhythm)
                return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    

        if pickonesortwos == 1:
            possible_gracenote_indexes_twos = [((i+len(repeated_twos))-1) for i in range(len(final_note_pattern)) if final_note_pattern[i:i+len(repeated_twos)] == repeated_twos]
            if possible_gracenote_indexes_twos ==[]:
                # intersperse with rest
                withinbetween_rests_rhythm = intersperse(rhythm, 20)
                withinbetween_rests_amplitude = intersperse(amplitude, 0)
                withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
                withinbetween_rests_rhythm.append(20)
                withinbetween_rests_amplitude.append(0)
                withinbetween_rests_note_pattern.append(0)                      
                total_duration = sum(withinbetween_rests_rhythm)
                return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    
   
            if possible_gracenote_indexes_twos !=[]:
                gracenoteIndex = random.choice(possible_gracenote_indexes_twos)
                final_note_pattern.insert(gracenoteIndex, 1)        
                rhythm.insert(gracenoteIndex, round(50))
                amplitude.insert(gracenoteIndex, round(starting_amplitude_value/5))       
                # intersperse with rest
                withinbetween_rests_rhythm = intersperse(rhythm, 20)
                withinbetween_rests_amplitude = intersperse(amplitude, 0)
                withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
                withinbetween_rests_rhythm.append(20)
                withinbetween_rests_amplitude.append(0)
                withinbetween_rests_note_pattern.append(0)                
                total_duration = sum(withinbetween_rests_rhythm)
                return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    
   
    if gracenotes_on_or_off == 1: # if no grace note
        full_list_rhythm = []
        decide_on_gracenotes_or_not = random.choice(list(range(0,4)))
        samples_to_generate = random.choice(list(range(4,6)))
        starting_value = initial_duration
        ending_rhythm_value = random.choice(list(range(150,600)))
        x1 = np.geomspace(starting_value, ending_rhythm_value, samples_to_generate, endpoint = False)
        full_list_rhythm.append(x1)
        rhythm = [round(item) for sublist in full_list_rhythm for item in sublist]  

        # amplitude ------------------------------------------------------------
        full_list_amplitude = []
        starting_amplitude_value = initial_amplitude
        ending_amplitude_value = random.choice(list(range(40,100))) # full range 0 - 127, reduced for statement
        x_amp = np.geomspace(starting_amplitude_value, ending_amplitude_value, len(rhythm), endpoint = False)
        full_list_amplitude.append(x_amp)
        amplitude = [round(item) for sublist in full_list_amplitude for item in sublist]  

        # note pattern ------------------------------------------------------------
        notepattern = []
        note_pattern_choices = random.sample(patternpallete, k=5)
        note_pattern_choice =  [item for sublist in note_pattern_choices for item in sublist] 
        for x in range(0, 50):
            notepattern.append(note_pattern_choice)
        notepattern =  [item for sublist in notepattern for item in sublist]    
        root_patterns_used = []
        for x in range(0, len(note_pattern_choices)):
            root_patterns_used.append(patternpallete.index(note_pattern_choices[x]))
        final_note_pattern = notepattern[0:len(rhythm)]     

        # intersperse with rest ------------------------------------------------------------
        withinbetween_rests_rhythm = intersperse(rhythm, 20)
        withinbetween_rests_rhythm.append(20)
        withinbetween_rests_amplitude = intersperse(amplitude, 0)
        withinbetween_rests_amplitude.append(0)
        withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
        withinbetween_rests_note_pattern.append(0)

        total_duration = sum(withinbetween_rests_rhythm)

        return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern
    

# -------------------------------------------------------------------------------------------------- 
# backchannels don't disrupt the flow, simply a much shorter statement (1 or 2 sounds) WITHOUT grace notes
def create_backchannel(initial_duration, initial_amplitude):
    full_list_rhythm = []
    samples_to_generate = random.choice(list(range(1,3)))
    starting_value = initial_duration
    
    # for a backchannel, the ending rhythm value and amplitude value should be very close to the original, if a 
    # pair then then the second note is always softer and longer
    ending_rhythm_value = (starting_value + random.choice(list(range(50))))
    x1 = np.geomspace(starting_value, ending_rhythm_value, samples_to_generate, endpoint = False)
    full_list_rhythm.append(x1)
    rhythm = [round(item) for sublist in full_list_rhythm for item in sublist]  

    # amplitude ------------------------------------------------------------
    full_list_amplitude = []
    starting_amplitude_value = initial_amplitude
    ending_amplitude_value = (starting_amplitude_value - random.choice(list(range(0,25))))
    if ending_amplitude_value > 10:
        ending_amplitude_value = 10
    x_amp = np.geomspace(starting_amplitude_value, ending_amplitude_value, len(rhythm), endpoint = False)
    full_list_amplitude.append(x_amp)
    amplitude = [round(item) for sublist in full_list_amplitude for item in sublist]  

    # note pattern ------------------------------------------------------------
    notepattern = []
    note_pattern_choices = random.sample(patternpallete, k=5)
    note_pattern_choice =  [item for sublist in note_pattern_choices for item in sublist] 
    for x in range(0, 50):
        notepattern.append(note_pattern_choice)
    notepattern =  [item for sublist in notepattern for item in sublist]    
    root_patterns_used = []
    for x in range(0, len(note_pattern_choices)):
        root_patterns_used.append(patternpallete.index(note_pattern_choices[x]))
    final_note_pattern = notepattern[0:len(rhythm)]     

    # intersperse with rest ------------------------------------------------------------
    withinbetween_rests_rhythm = intersperse(rhythm, 20)
    withinbetween_rests_rhythm.append(20)
    withinbetween_rests_amplitude = intersperse(amplitude, 0)
    withinbetween_rests_amplitude.append(0)
    withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
    withinbetween_rests_note_pattern.append(0)
    
    total_duration = sum(withinbetween_rests_rhythm)

    return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    

# -------------------------------------------------------------------------------------------------- 
# Disruptions are just an unconnected statement, breaking the flow (do not connect start, but do connect end)
def create_disruption(): # no arguments for a disruption
    gracenotes_on_or_off = random.choice([0,1])
    if gracenotes_on_or_off == 0: # if grace notes on
        
        # rhythm ------------------------------------------------------------
        full_list_rhythm = []
        samples_to_generate = random.choice(list(range(4,6)))
        
        # starting rhythm value either long or short
        lowstarting_values = list(range(150,600))[0:40]
        highstarting_values = list(range(160,600))[400:450]
        combined_starting_values = lowstarting_values + highstarting_values
        starting_value = random.choice(combined_starting_values)

        ending_rhythm_value = random.choice(list(range(150,600)))
        x1 = np.geomspace(starting_value, ending_rhythm_value, samples_to_generate, endpoint = False)
        full_list_rhythm.append(x1)
        rhythm = [round(item) for sublist in full_list_rhythm for item in sublist]          
        
        # amplitude ------------------------------------------------------------
        full_list_amplitude = []
        # starting amplitude either high or low to emphasise disruption - but not extreme values
        low_amplitude_list = list(range(30,110))[0:20]
        high_amplitude_list = list(range(30,110))[-20:]
        combined_amplitude_list = low_amplitude_list + high_amplitude_list
        
        starting_amplitude_value = random.choice(combined_amplitude_list)
        ending_amplitude_value = random.choice(list(range(40,100))) # full range 0 - 127
        x_amp = np.geomspace(starting_amplitude_value, ending_amplitude_value, len(rhythm), endpoint = False)
        full_list_amplitude.append(x_amp)
        amplitude = [round(item) for sublist in full_list_amplitude for item in sublist]          
        
        # note pattern ------------------------------------------------------------
        notepattern = []
        note_pattern_choices = random.sample(patternpallete, k=5)
        note_pattern_choice =  [item for sublist in note_pattern_choices for item in sublist] 
        for x in range(0, 50):
            notepattern.append(note_pattern_choice)
        notepattern =  [item for sublist in notepattern for item in sublist]    
        root_patterns_used = []
        for x in range(0, len(note_pattern_choices)):
            root_patterns_used.append(patternpallete.index(note_pattern_choices[x]))
        final_note_pattern = notepattern[0:len(rhythm)]             

        # and now the grace notes ------------------------------------------------------------
        repeated_ones = [1,1]
        repeated_twos = [2,2]
        pickonesortwos = random.choice([0,1])

        possible_gracenote_indexes = []
        if pickonesortwos == 0:
            possible_gracenote_indexes_ones = [((i+len(repeated_ones))-1) for i in range(len(final_note_pattern)) if final_note_pattern[i:i+len(repeated_ones)] == repeated_ones]
            if possible_gracenote_indexes_ones ==[]:
                # intersperse with rest
                withinbetween_rests_rhythm = intersperse(rhythm, 20)
                withinbetween_rests_amplitude = intersperse(amplitude, 0)
                withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
                withinbetween_rests_rhythm.append(20)
                withinbetween_rests_amplitude.append(0)
                withinbetween_rests_note_pattern.append(0)                      
                total_duration = sum(withinbetween_rests_rhythm)
                return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    
         
            if possible_gracenote_indexes_ones !=[]:
                gracenoteIndex = random.choice(possible_gracenote_indexes_ones)
                final_note_pattern.insert(gracenoteIndex, 2)
                rhythm.insert(gracenoteIndex, round(starting_value/5))
                amplitude.insert(gracenoteIndex, round(starting_amplitude_value/5))
                # intersperse with rest 
                withinbetween_rests_rhythm = intersperse(rhythm, 20)
                withinbetween_rests_amplitude = intersperse(amplitude, 0)
                withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
                withinbetween_rests_rhythm.append(20)
                withinbetween_rests_amplitude.append(0)
                withinbetween_rests_note_pattern.append(0)                                     
                total_duration = sum(withinbetween_rests_rhythm)
                return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    

        if pickonesortwos == 1:
            possible_gracenote_indexes_twos = [((i+len(repeated_twos))-1) for i in range(len(final_note_pattern)) if final_note_pattern[i:i+len(repeated_twos)] == repeated_twos]
            if possible_gracenote_indexes_twos ==[]:
                # intersperse with rest
                withinbetween_rests_rhythm = intersperse(rhythm, 20)
                withinbetween_rests_amplitude = intersperse(amplitude, 0)
                withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
                withinbetween_rests_rhythm.append(20)
                withinbetween_rests_amplitude.append(0)
                withinbetween_rests_note_pattern.append(0)                      
                total_duration = sum(withinbetween_rests_rhythm)
                return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    
   
            if possible_gracenote_indexes_twos !=[]:
                gracenoteIndex = random.choice(possible_gracenote_indexes_twos)
                final_note_pattern.insert(gracenoteIndex, 1)        
                rhythm.insert(gracenoteIndex, round(50))
                amplitude.insert(gracenoteIndex, round(starting_amplitude_value/5))       
                # intersperse with rest
                withinbetween_rests_rhythm = intersperse(rhythm, 20)
                withinbetween_rests_amplitude = intersperse(amplitude, 0)
                withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
                withinbetween_rests_rhythm.append(20)
                withinbetween_rests_amplitude.append(0)
                withinbetween_rests_note_pattern.append(0)                
                total_duration = sum(withinbetween_rests_rhythm)
                return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    
   
    if gracenotes_on_or_off == 1: # if no grace note ------------------------------------------------------------
        full_list_rhythm = []
        samples_to_generate = random.choice(list(range(4,6)))
        
        # starting rhythm value either long or short
        lowstarting_values = list(range(150,600))[0:40]
        highstarting_values = list(range(160,600))[400:450]
        combined_starting_values = lowstarting_values + highstarting_values
        starting_value = random.choice(combined_starting_values)
        
        ending_rhythm_value = random.choice(list(range(150,600)))
        x1 = np.geomspace(starting_value, ending_rhythm_value, samples_to_generate, endpoint = False)
        full_list_rhythm.append(x1)
        rhythm = [round(item) for sublist in full_list_rhythm for item in sublist]  

        # amplitude ------------------------------------------------------------
        # either high or low
        full_list_amplitude = []
        low_amplitude_list = list(range(30,110))[0:20]
        high_amplitude_list = list(range(30,110))[-20:]
        combined_amplitude_list = low_amplitude_list + high_amplitude_list
        
        starting_amplitude_value = random.choice(combined_amplitude_list)        
        ending_amplitude_value = random.choice(list(range(40,100))) # full range 0 - 127, reduced for statement
        x_amp = np.geomspace(starting_amplitude_value, ending_amplitude_value, len(rhythm), endpoint = False)
        full_list_amplitude.append(x_amp)
        amplitude = [round(item) for sublist in full_list_amplitude for item in sublist]  

        # note pattern ------------------------------------------------------------
        notepattern = []
        note_pattern_choices = random.sample(patternpallete, k=5)
        note_pattern_choice =  [item for sublist in note_pattern_choices for item in sublist] 
        for x in range(0, 50):
            notepattern.append(note_pattern_choice)
        notepattern =  [item for sublist in notepattern for item in sublist]    
        root_patterns_used = []
        for x in range(0, len(note_pattern_choices)):
            root_patterns_used.append(patternpallete.index(note_pattern_choices[x]))
        final_note_pattern = notepattern[0:len(rhythm)]     

        # intersperse with rest ------------------------------------------------------------
        withinbetween_rests_rhythm = intersperse(rhythm, 20)
        withinbetween_rests_rhythm.append(20)
        withinbetween_rests_amplitude = intersperse(amplitude, 0)
        withinbetween_rests_amplitude.append(0)
        withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
        withinbetween_rests_note_pattern.append(0)

        total_duration = sum(withinbetween_rests_rhythm)

        # disruption still return the same values so the next item can flow
        return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern


# -------------------------------------------------------------------------------------------------- 
# floorgrabbers should grab attention: always start short and loud, a single statement getting shorter and softer
# these don't have grace notes
def create_floorgrabber(): # no inputs, always disrupts
    full_list_rhythm = []
    samples_to_generate = random.choice(list(range(4,7)))
    starting_value = random.choice(list(range(80,120))) # constricted ranges, start fast, end slower
    ending_rhythm_value = random.choice(list(range(450,600)))
    x1 = np.geomspace(starting_value, ending_rhythm_value, samples_to_generate, endpoint = False)
    full_list_rhythm.append(x1)
    rhythm = [round(item) for sublist in full_list_rhythm for item in sublist]  

    # amplitude ------------------------------------------------------------
    full_list_amplitude = []
    starting_amplitude_value = random.choice(list(range(110,127))) # always start loud
    ending_amplitude_value = random.choice(list(range(20,50))) # always end soft
    x_amp = np.geomspace(starting_amplitude_value, ending_amplitude_value, len(rhythm), endpoint = False)
    full_list_amplitude.append(x_amp)
    amplitude = [round(item) for sublist in full_list_amplitude for item in sublist]  

    # note pattern ------------------------------------------------------------
    notepattern = []
    note_pattern_choices = random.sample(patternpallete, k=5)
    note_pattern_choice =  [item for sublist in note_pattern_choices for item in sublist] 
    for x in range(0, 50):
        notepattern.append(note_pattern_choice)
    notepattern =  [item for sublist in notepattern for item in sublist]    
    root_patterns_used = []
    for x in range(0, len(note_pattern_choices)):
        root_patterns_used.append(patternpallete.index(note_pattern_choices[x]))
    final_note_pattern = notepattern[0:len(rhythm)]     

    # intersperse with rest ------------------------------------------------------------
    withinbetween_rests_rhythm = intersperse(rhythm, 20)
    withinbetween_rests_rhythm.append(20)
    withinbetween_rests_amplitude = intersperse(amplitude, 0)
    withinbetween_rests_amplitude.append(0)
    withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
    withinbetween_rests_note_pattern.append(0)

    total_duration = sum(withinbetween_rests_rhythm)

    return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    

# -------------------------------------------------------------------------------------------------- 
# gets faster, then slows down into a pause at the end...
def create_question(initial_duration, initial_amplitude):
    # rhythm ------------------------------------------------------------
    full_list_rhythm = []
    samples_to_generate = random.choice(list(range(4,6)))
    starting_value = initial_duration
    ending_rhythm_value = random.choice(list(range(150,200)))
    start_second_phrase_val = ending_rhythm_value
    x1 = np.geomspace(starting_value, ending_rhythm_value, samples_to_generate, endpoint = False)
    full_list_rhythm.append(x1)
    rhythm = [round(item) for sublist in full_list_rhythm for item in sublist]          

    # and the second phrase rhythm
    full_list_rhythm2 = []
    samples_to_generate2 = random.choice(list(range(4,6)))
    starting_value2 = start_second_phrase_val
    ending_rhythm_value2 = random.choice(list(range(1000,1300)))
    x12 = np.geomspace(starting_value2, ending_rhythm_value2, samples_to_generate2, endpoint = False)
    full_list_rhythm2.append(x12)
    rhythm2 = [round(item) for sublist in full_list_rhythm2 for item in sublist]      
    
    rhythm = rhythm + rhythm2
    
    # amplitude ------------------------------------------------------------
    # no need for two phrases here, just use rhythm as before
    full_list_amplitude = []
    starting_amplitude_value = initial_amplitude
    ending_amplitude_value = random.choice(list(range(40,100))) # full range 0 - 127, reduced for statement
    x_amp = np.geomspace(starting_amplitude_value, ending_amplitude_value, len(rhythm), endpoint = False)
    full_list_amplitude.append(x_amp)
    amplitude = [round(item) for sublist in full_list_amplitude for item in sublist]          

    # note pattern ------------------------------------------------------------
    notepattern = []
    note_pattern_choices = random.sample(patternpallete, k=5)
    note_pattern_choice =  [item for sublist in note_pattern_choices for item in sublist] 
    for x in range(0, 50):
        notepattern.append(note_pattern_choice)
    notepattern =  [item for sublist in notepattern for item in sublist]    
    root_patterns_used = []
    for x in range(0, len(note_pattern_choices)):
        root_patterns_used.append(patternpallete.index(note_pattern_choices[x]))
    final_note_pattern = notepattern[0:len(rhythm)]    
    
    # intersperse with rest ------------------------------------------------------------
    withinbetween_rests_rhythm = intersperse(rhythm, 20)
    withinbetween_rests_rhythm.append(20)
    withinbetween_rests_amplitude = intersperse(amplitude, 0)
    withinbetween_rests_amplitude.append(0)
    withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
    withinbetween_rests_note_pattern.append(0)

    total_duration = sum(withinbetween_rests_rhythm)

    return withinbetween_rests_rhythm, ending_rhythm_value2, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern    
# -------------------------------------------------------------------------------------------------- 
# the response to a question is always a note loop taken from the question
def create_statement_response_to_question(initial_duration, initial_amplitude, root_note_pattern):
    # essentially like a statement, but looping a note pattern from the question.. and always getting faster
    # (as the question always ends slow)
    
    # rhythm ------------------------------------------------------------
    full_list_rhythm = []
    samples_to_generate = random.choice(list(range(11,14)))
    starting_value = initial_duration
    ending_rhythm_value = random.choice(list(range(150,250)))
    start_second_phrase_val = ending_rhythm_value
    x1 = np.geomspace(starting_value, ending_rhythm_value, samples_to_generate, endpoint = False)
    full_list_rhythm.append(x1)
    rhythm = [round(item) for sublist in full_list_rhythm for item in sublist]          
    
    # amplitude ------------------------------------------------------------
    full_list_amplitude = []
    starting_amplitude_value = initial_amplitude
    ending_amplitude_value = random.choice(list(range(20,40))) # getting quieter to end
    x_amp = np.geomspace(starting_amplitude_value, ending_amplitude_value, len(rhythm), endpoint = False)
    full_list_amplitude.append(x_amp)
    amplitude = [round(item) for sublist in full_list_amplitude for item in sublist]          

    # note pattern ------------------------------------------------------------
    notepattern_without_zeros = [i for i in root_note_pattern if i != 0]
    notepattern_starting_range = (random.choice(list(range(len(notepattern_without_zeros)-4))))
    notepattern_len_for_loop = random.choice(list(range(2,4))) # 2 or 3
    notepattern_ending_range = notepattern_starting_range + notepattern_len_for_loop
    notepattern_for_loop = notepattern_without_zeros[notepattern_starting_range:notepattern_ending_range]    
    
    notepattern = []
    for x in range(0, 50):
        notepattern.append(notepattern_for_loop)
    notepattern_for_loop =  [item for sublist in notepattern for item in sublist]    
    final_note_pattern = notepattern_for_loop[0:len(rhythm)]    
    
    # intersperse with rest ------------------------------------------------------------
    withinbetween_rests_rhythm = intersperse(rhythm, 20)
    withinbetween_rests_rhythm.append(20)
    withinbetween_rests_amplitude = intersperse(amplitude, 0)
    withinbetween_rests_amplitude.append(0)
    withinbetween_rests_note_pattern = intersperse(final_note_pattern, 0)
    withinbetween_rests_note_pattern.append(0)

    total_duration = sum(withinbetween_rests_rhythm)

    return withinbetween_rests_rhythm, ending_rhythm_value, total_duration, withinbetween_rests_amplitude, ending_amplitude_value, withinbetween_rests_note_pattern     

# once setup is done:
# time.sleep(2) # wait for 2 seconds?
print('setup done')

#============================================================================================================
# Code running in a loop from here

# %%time to time cell execution
# this block gives voice, rhythm, amplitude and notepattern in single items
try:
    while True:
        interpreter.set_tensor(input_details[0]['index'], sample_vector)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])
        pred = output_data[0]/temperature
        pred = tf.random.categorical(pred, num_samples=1)[-1,0].numpy()
        sample = vocabulary[pred]   
        last_sample_token = [tokenizer[sample]]
        appended = np.append(sample_vector, last_sample_token)
        deleted = np.delete(appended, 0)
        reshaped = np.reshape(deleted, (64,1))
        sample_vector = np.float32(reshaped)    
        voice_number = sample[:1]
        act_type = ""
        for char in sample:
            if ord(char) >= 65 and ord(char) <= 90:
                act_type += char
            elif ord(char) >= 97 and ord(char) <= 122:
                act_type += char    

        prev_act_full = vocabulary[int(appended[-2])]
        prev_act_type = ""
        for char in prev_act_full:
            if ord(char) >= 65 and ord(char) <= 90:
                prev_act_type += char
            elif ord(char) >= 97 and ord(char) <= 122:
                prev_act_type += char    

        prev_prev_act_full = vocabulary[int(appended[-3])]
        prev_prev_act_type = ""
        for char in prev_prev_act_full:
            if ord(char) >= 65 and ord(char) <= 90:
                prev_prev_act_type += char
            elif ord(char) >= 97 and ord(char) <= 122:
                prev_prev_act_type += char   

        print(voice_number, act_type, [prev_act_type, prev_prev_act_type])
        # prints the previous and penultimate act type as this will affect the material produced

        # generating material: -------------------------------------------------------------------
        if act_type=='S': # if the current act is a statement
            if prev_act_type =='S': # if statement follows statement, create statement
                rhythm, ending_rhythm_value, total_duration, amplitude, ending_amplitude_value, notepattern = create_statement(ending_rhythm_value, ending_amplitude_value)
            if prev_act_type == 'B': # create statement
                rhythm, ending_rhythm_value, total_duration, amplitude, ending_amplitude_value, notepattern = create_statement(ending_rhythm_value, ending_amplitude_value)
            if prev_act_type == 'D': # create statement
                rhythm, ending_rhythm_value, total_duration, amplitude, ending_amplitude_value, notepattern = create_statement(ending_rhythm_value, ending_amplitude_value)
            if prev_act_type == 'F': # create statement
                rhythm, ending_rhythm_value, total_duration, amplitude, ending_amplitude_value, notepattern = create_statement(ending_rhythm_value, ending_amplitude_value)
            if prev_act_type == 'Q': # create question response
                rhythm, ending_rhythm_value, total_duration, amplitude, ending_amplitude_value, notepattern = create_statement_response_to_question(ending_rhythm_value, ending_amplitude_value, notepattern)
            # -----------------------------------------------------------------------------------    
        if act_type=='B': # doesn't matter what the previous act was
            rhythm, ending_rhythm_value, total_duration, amplitude, ending_amplitude_value, notepattern = create_backchannel(ending_rhythm_value, ending_amplitude_value)
            # -----------------------------------------------------------------------------------    
        if act_type == 'D': # also doesn't matter what prev act was
            rhythm, ending_rhythm_value, total_duration, amplitude, ending_amplitude_value, notepattern = create_disruption()
            # -----------------------------------------------------------------------------------    
        if act_type == 'F':
            rhythm, ending_rhythm_value, total_duration, amplitude, ending_amplitude_value, notepattern = create_floorgrabber()
            # -----------------------------------------------------------------------------------    
        if act_type == 'Q':
            rhythm, ending_rhythm_value, total_duration, amplitude, ending_amplitude_value, notepattern = create_question(ending_rhythm_value, ending_amplitude_value)



        # following code for testing, send OSC message to max msp... but important lists for motors are (rhythm), (amplitude) and (notepattern)
        # print(voice_number, rhythm)

        # send OSC message
        for x in range(0, len(notepattern)):
            mymsg = notepattern[x]

            client = udp_client.UDPClient('127.0.0.1', 6500) # send to max msp
            msg = osc_message_builder.OscMessageBuilder(address = '/inputs')
            msg.add_arg(mymsg)
            msg = msg.build()
            client.send(msg)

        for x in range(0, len(rhythm)):
            mymsg = rhythm[x]

            client = udp_client.UDPClient('127.0.0.1', 6400) # send to max msp
            msg = osc_message_builder.OscMessageBuilder(address = '/inputs')
            msg.add_arg(mymsg)
            msg = msg.build()
            client.send(msg)


        for x in range(0, len(amplitude)):
            mymsg = amplitude[x]

            client = udp_client.UDPClient('127.0.0.1', 6300) # send to max msp
            msg = osc_message_builder.OscMessageBuilder(address = '/inputs')
            msg.add_arg(mymsg)
            msg = msg.build()
            client.send(msg)

        time.sleep(0.2)
        # in a loop, then sleep for duration of the segment (IN SECONDS NOT MS)
        time.sleep(((total_duration/1000)+(ending_rhythm_value/1000)) - 0.17) # last val to compensate for computation time


    
except KeyboardInterrupt:
    print('Stop')
    pass


# In[ ]:




