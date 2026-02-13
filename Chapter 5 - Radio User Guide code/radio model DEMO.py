#!/usr/bin/env python
# coding: utf-8

# This code is for testing the radio text models. 
# Models and files under Models / Chapter 5 - Radio User Guide models / Text models

# In[1]:
# define file paths
onnx_model_path = "{path-to}/1.onnx"
idx_to_char_path = "{path-to}/idx_to_char.pkl"
char_to_idx_path = "{path-to}/char_to_idx.pkl"


import onnxruntime as ort
import numpy as np
import pickle


# Load dictionaries
def load_dictionaries(idx_to_char_path, char_to_idx_path):
    with open(idx_to_char_path, 'rb') as file:
        idx_to_char = pickle.load(file)

    with open(char_to_idx_path, 'rb') as file:
        char_to_idx = pickle.load(file)

    return idx_to_char, char_to_idx

# Function to load the ONNX model
def load_model(onnx_model_path):
    session = ort.InferenceSession(onnx_model_path)
    return session

def generateWord():
    currentWord = ''
    for x in range(100):
        next_char = text_generator.generate_next_char()
        currentWord = currentWord + next_char
        if next_char == ' ' and not currentWord.isspace():
            currentWord= currentWord.strip()
            return currentWord
            break

class TextGenerator:
    def __init__(self, session, char_to_idx, idx_to_char, start_text=' ', hidden_size=128, n_layers=2, temp=0.3):
        self.session = session
        self.char_to_idx = char_to_idx
        self.idx_to_char = idx_to_char
        self.hidden_size = hidden_size
        self.n_layers = n_layers
        self.temp = temp

        # Initialize hidden and cell states
        self.hidden = np.zeros((n_layers, 1, hidden_size), dtype=np.float32)
        self.cell = np.zeros((n_layers, 1, hidden_size), dtype=np.float32)

        # Initialize input sequence
        self.idx_input = [char_to_idx[char] for char in start_text]
        self.input_seq = np.array(self.idx_input, dtype=np.int64).reshape(-1, 1, 1)
        
        # Prime the model with the start text
        for i in range(len(start_text)):
            inputs = {
                'input': self.input_seq[i:i+1], 
                'hidden': self.hidden, 
                'onnx::Slice_2': self.cell
            }
            outputs = self.session.run(None, inputs)
            self.hidden = outputs[1]
            self.cell = outputs[2]

        self.inp = self.input_seq[-1].reshape(-1, 1, 1)

    def generate_next_char(self):
        inputs = {
            'input': self.inp, 
            'hidden': self.hidden, 
            'onnx::Slice_2': self.cell
        }
        outputs = self.session.run(None, inputs)
        output_logits = outputs[0].squeeze()
        self.hidden = outputs[1]
        self.cell = outputs[2]
        
        # Apply the log-sum-exp trick to stabilize softmax
        max_logit = np.max(output_logits)
        stabilized_logits = output_logits - max_logit
        exp_logits = np.exp(stabilized_logits / self.temp)
        p_next = exp_logits / np.sum(exp_logits)
        
        top_index = np.random.choice(len(self.char_to_idx), p=p_next)
        
        self.inp = np.array([[top_index]], dtype=np.int64).reshape(-1, 1, 1)
        predicted_char = self.idx_to_char[top_index]
        
        return predicted_char

def change_model(filepath):
    # Load new model
    session = load_model(filepath)
    return session

idx_to_char, char_to_idx = load_dictionaries(idx_to_char_path, char_to_idx_path)


# In[3]:


##############################################


# In[2]:
# LOAD MODELS -----------------------------------------------------------

# redefine if using a different model, numered 1 to 14: onnx_model_path = "{path-to}/14.onnx"
session = load_model(onnx_model_path)
text_generator = TextGenerator(session, char_to_idx, idx_to_char, start_text=' ')


# In[3]:


# generate the next word   
word = generateWord()


# In[4]:

# Generating more text 

words = []

for x in range(700):
    word = generateWord()
    if word:
        words.append(word)

wordstrings = ' '.join(words)

print(wordstrings)

