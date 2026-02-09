#!/usr/bin/env python
# coding: utf-8

# In[ ]:

# ------------------
# This code generates sentences for the puredata patch to read, creates new sentence when read

# this script >> puredata patch >> OSC_receive >> motors and lights
# -----------------


from wonderwords import RandomWord
randomword_gen = RandomWord()
from ollama import generate
import spacy
# Load the pre-trained dependency model
nlp = spacy.load("en_core_web_sm")
import random
import os
import numpy as np
import time
import json
import tempfile

loaded_gesture_grids = np.load("/home/fin/Documents/filtered_grids_pyin_FULL.npy")
depsavefilelocation = "/home/fin/Documents/depfolder/dependencylist.txt"
depsavefolder = "/home/fin/Documents/depfolder"

# direction grid for reading back
directiongrid = [[0,1,2,3],
                 [0,1,2,3],
                 [0,1,2,3],
                 [0,1,2,3]]

# reference only: motor 0 is top left
motorgrid = [[0,1,2,3],
            [4,5,6,7],
            [8,9,10,11],
            [12,13,14,15]]

# using qwen2.5:0.5b
# ollama pull qwen2.5:0.5b

# using dependency relations

dependency_labels = [
    "ROOT", "acl", "acomp", "advcl", "advmod", "agent", "amod", "appos", "attr", "aux", 
    "auxpass", "case", "cc", "ccomp", "compound", "conj", "csubj", "csubjpass", "dative", 
    "dep", "det", "dobj", "expl", "intj", "mark", "meta", "neg", "nmod", "npadvmod", 
    "nsubj", "nsubjpass", "nummod", "oprd", "parataxis", "pcomp", "pobj", "poss", 
    "preconj", "predet", "prep", "prt", "punct", "quantmod", "relcl", "xcomp"
]

# Create a mapping dictionary
dependency_map = {label: index for index, label in enumerate(dependency_labels)}

# Function to get the integer value of a dependency label
def get_dependency_indexes(label_list):
    return [dependency_map.get(label, -1) for label in label_list]

def fix_stop_chars(response):
    # Strip any leading/trailing spaces
    response = response.strip()

    # Remove <EOT> from the end of the response if it's present
    if response.endswith('<EOT>'):
        response = response[:-5].strip()  # Remove '<EOT>' and any trailing spaces

    # Check if the response ends with punctuation, and if not, add a period
    if response and response[-1] not in ['.', '?', '!']:
        response += '.'  # Default to period if no punctuation is found

    return response

def gen_randomSentence():
    # Generate response
    response = generate(
        model='smollm2:135m',
        prompt = f"Generate a sentence about {randomword_gen.word()}",
        options={
            'num_predict': 64,
            'temperature': 0.1, # 0.6
            'top_p': 0.1, # 0.1
            'stop': ['. ', '? ', '! ', '\n'], # Use <EOT> to indicate end of full output: here I want to stop at end of first sentence
        },
    )

    # Extract response and apply post-processing
    sentence = response['response'].strip()  # Remove any leading/trailing spaces
    sentence = fix_stop_chars(sentence)  # Ensure correct punctuation

    # Parse the sentence with SpaCy
    doc = nlp(sentence)

    # Extract dependencies as a list
    dependencies = [token.dep_ for token in doc]

    dep_index_list = get_dependency_indexes(dependencies)    
    return dep_index_list

def save_list_atomic(data: list, filepath: str = "data_list.txt"):
    # Convert each integer to string and join with newlines
    text_data = '\n'.join(map(str, data))
    
    with tempfile.NamedTemporaryFile(
        mode="w", 
        dir=os.path.dirname(filepath),
        delete=False
    ) as tmp_file:
        tmp_file.write(text_data)
        tmp_path = tmp_file.name
        
    os.replace(tmp_path, filepath)
    
while True:
    deleteme_path = os.path.join(depsavefolder, 'deleteme.txt')
    
    if os.path.isfile(deleteme_path):
        os.remove(deleteme_path)
        dependencies_list = gen_randomSentence()
        save_list_atomic(dependencies_list, depsavefilelocation)
    else:
        time.sleep(0.2)


# In[ ]:




