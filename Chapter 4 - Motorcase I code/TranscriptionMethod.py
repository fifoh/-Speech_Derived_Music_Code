# THIS file was used to create motor transcriptions from speech audio, and was run in a jupyter notebook

# manual text transcription + audio >> motor transcription in three layers (letters, words, sound/silence)

# -------------------------------------------------------------------------------------

# used for forced alignment: https://pytorch.org/tutorials/intermediate/forced_alignment_with_torchaudio_tutorial.html#preparation

# pre: install libraries

# 1. define folder of motor sounds, and source audio file.
# motor sound folder 'C:/Users/Fin/Desktop/pythonspeech/Motor_combinations_Sound'
filename = "C:/Users/Fin/Desktop/pythonspeech/Transcriptions_TEXT/poetry_hour.wav" # # must be mono 16bit 16000 khz

# 2. transcribe speech manually:
input_transcript = 'are going to miss them I like to read about such things presented not with self pity or dispair or romanticism but with the realistic firmness and even humor that is in fact what I call the moral tone of miss pimms novels it is also the moral tone of larkins poems he once said that art should either help us to enjoy or to endure yet he himself found it difficult to do either why'

# 3. set silence threshold for sound/silence segmentation
MYsilence_thresh = -29

# 4. Run all, produces a list of onsets, offsets, and matching motor numbers for 'letters', 'words', 'sound/silence'

import speech_recognition as sr
import soundfile as sf
import IPython.display as ipd
import librosa, librosa.display
import torch
import torchaudio
import os
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE" # kernel dies if you don't do this
from dataclasses import dataclass
import IPython
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import glob
from tkinter import Tcl
import itertools
from itertools import combinations
import numpy as np
from itertools import chain
import time
import string
from pythonosc import osc_message_builder
from pythonosc import udp_client
from google.cloud import speech
import os
import io

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.random.manual_seed(0)

SPEECH_FILE = filename

bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
model = bundle.get_model().to(device)
labels = bundle.get_labels()
with torch.inference_mode():
    waveform, _ = torchaudio.load(SPEECH_FILE)
    emissions, _ = model(waveform.to(device))
    emissions = torch.log_softmax(emissions, dim=-1)

emission = emissions[0].cpu().detach()

manualtranscript = input_transcript.upper()
format_transcript3 = manualtranscript # hash if not using manual transcript
# get location of spaces
def find_whitespace(st):
   for index, character in enumerate(st):
      if character in string.whitespace:
           yield index

spaceIndexes = list(find_whitespace(format_transcript3))
#then more transcription formatting
format_transcript4 = format_transcript3.replace(" ", "|" ) # check if key error later - numbers it doesn't like

transcript = format_transcript4
dictionary = {c: i for i, c in enumerate(labels)}

tokens = [dictionary[c] for c in transcript]

def get_trellis(emission, tokens, blank_id=0):
    num_frame = emission.size(0)
    num_tokens = len(tokens)

    # Trellis has extra diemsions for both time axis and tokens.
    # The extra dim for tokens represents <SoS> (start-of-sentence)
    # The extra dim for time axis is for simplification of the code.
    trellis = torch.empty((num_frame + 1, num_tokens + 1))
    trellis[0, 0] = 0
    trellis[1:, 0] = torch.cumsum(emission[:, 0], 0)
    trellis[0, -num_tokens:] = -float("inf")
    trellis[-num_tokens:, 0] = float("inf")

    for t in range(num_frame):
        trellis[t + 1, 1:] = torch.maximum(
            # Score for staying at the same token
            trellis[t, 1:] + emission[t, blank_id],
            # Score for changing to the next token
            trellis[t, :-1] + emission[t, tokens],
        )
    return trellis

trellis = get_trellis(emission, tokens)

@dataclass
class Point:
    token_index: int
    time_index: int
    score: float

def backtrack(trellis, emission, tokens, blank_id=0):
    # Note:
    # j and t are indices for trellis, which has extra dimensions
    # for time and tokens at the beginning.
    # When referring to time frame index `T` in trellis,
    # the corresponding index in emission is `T-1`.
    # Similarly, when referring to token index `J` in trellis,
    # the corresponding index in transcript is `J-1`.
    j = trellis.size(1) - 1
    t_start = torch.argmax(trellis[:, j]).item()

    path = []
    for t in range(t_start, 0, -1):
        # 1. Figure out if the current position was stay or change
        # Note (again):
        # `emission[J-1]` is the emission at time frame `J` of trellis dimension.
        # Score for token staying the same from time frame J-1 to T.
        stayed = trellis[t - 1, j] + emission[t - 1, blank_id]
        # Score for token changing from C-1 at T-1 to J at T.
        changed = trellis[t - 1, j - 1] + emission[t - 1, tokens[j - 1]]

        # 2. Store the path with frame-wise probability.
        prob = emission[t - 1, tokens[j - 1] if changed > stayed else 0].exp().item()
        # Return token index and time index in non-trellis coordinate.
        path.append(Point(j - 1, t - 1, prob))

        # 3. Update the token
        if changed > stayed:
            j -= 1
            if j == 0:
                break
    else:
        raise ValueError("Failed to align")
    return path[::-1]


path = backtrack(trellis, emission, tokens)

@dataclass
class Segment:
    label: str
    start: int
    end: int
    score: float

    def __repr__(self):
        return f"{self.label}\t({self.score:4.2f}): [{self.start:5d}, {self.end:5d})"

    @property
    def length(self):
        return self.end - self.start


def merge_repeats(path):
    i1, i2 = 0, 0
    segments = []
    while i1 < len(path):
        while i2 < len(path) and path[i1].token_index == path[i2].token_index:
            i2 += 1
        score = sum(path[k].score for k in range(i1, i2)) / (i2 - i1)
        segments.append(
            Segment(
                transcript[path[i1].token_index],
                path[i1].time_index,
                path[i2 - 1].time_index + 1,
                score,
            )
        )
        i1 = i2
    return segments


segments = merge_repeats(path)

# LETTERS -----------------------------------------------------------------------
# create empty letter onset list
LETTERonsetlist = []

# return letter onsets
def return_LETTER_onset(i):
    ratio = waveform.size(1) / (trellis.size(0) - 1)
    letters = segments[i]
    x0 = int(ratio * letters.start)
    return (f"{x0 / bundle.sample_rate:.3f}")

# append to letter onset list
for x in range (0, len(segments)):
    LETTERonsetlist.append(return_LETTER_onset(x))

# create empty letter offset list
LETTERoffsetlist = []

# return letter offsets
def return_LETTER_offset(i):
    ratio = waveform.size(1) / (trellis.size(0) - 1)
    letters = segments[i]
    x0 = int(ratio * letters.end)
    return (f"{x0 / bundle.sample_rate:.3f}")

# append to letter offset list
for x in range (0, len(segments)):
    LETTERoffsetlist.append(return_LETTER_offset(x))

# WORDS -------------------------------------------------------------------------
# merge segments into words - from tutorial
def merge_words(segments, separator="|"):
    words = []
    i1, i2 = 0, 0
    while i1 < len(segments):
        if i2 >= len(segments) or segments[i2].label == separator:
            if i1 != i2:
                segs = segments[i1:i2]
                word = "".join([seg.label for seg in segs])
                score = sum(seg.score * seg.length for seg in segs) / sum(seg.length for seg in segs)
                words.append(Segment(word, segments[i1].start, segments[i2 - 1].end, score))
            i1 = i2 + 1
            i2 = i1
        else:
            i2 += 1
    return words


word_segments = merge_words(segments)

# create empty word onset list
WORDonsetlist = []

# return word onsets
def return_WORD_onset(i):
    ratio = waveform.size(1) / (trellis.size(0) - 1)
    words = word_segments[i]
    x0 = int(ratio * words.start)
    return (f"{x0 / bundle.sample_rate:.3f}")

# append to word onset list
for x in range (0, len(word_segments)):
    WORDonsetlist.append(return_WORD_onset(x))

# create empty word offset list
WORDoffsetlist = []

# return word offsets
def return_WORD_offset(i):
    ratio = waveform.size(1) / (trellis.size(0) - 1)
    words = word_segments[i]
    x0 = int(ratio * words.end)
    return (f"{x0 / bundle.sample_rate:.3f}")

# append to word offset list
for x in range (0, len(word_segments)):
    WORDoffsetlist.append(return_WORD_offset(x))

# sound / silence ---------------------------------------------------------
#adjust target amplitude
def match_target_amplitude(sound, target_dBFS):
    change_in_dBFS = target_dBFS - sound.dBFS
    return sound.apply_gain(change_in_dBFS)

#Convert wav to audio_segment
audio_segment = AudioSegment.from_wav(filename)

#normalize audio_segment to -20dBFS
normalized_sound = match_target_amplitude(audio_segment, -20.0)

#Print detected non-silent chunks, which in our case would be spoken words.
nonsilent_data = detect_nonsilent(normalized_sound, min_silence_len=500, silence_thresh=MYsilence_thresh, seek_step=1)

# create empty sound onset list, append sound onsets
SOUNDonsetList = []
SoundOnsets_pre_list = [sublist[0] for sublist in nonsilent_data]
SOUNDonsetList.append(SoundOnsets_pre_list)

# create empty sound offset list, append sound offsets
SOUNDoffsetList = []
Soundoffsets_pre_list = [sublist[1] for sublist in nonsilent_data]
SOUNDoffsetList.append(Soundoffsets_pre_list)

# SPEECH SOUND ANALYSIS ---------------------------------------------------------------------------
y, sr = librosa.load(filename)
# compute spectral centroid for entire sample
cent = librosa.feature.spectral_centroid(y=y, sr=sr)
S, phase = librosa.magphase(librosa.stft(y=y))
times = librosa.times_like(cent)

# calculate RMS energy from spectrogram
S, phase = librosa.magphase(librosa.stft(y))
rms = librosa.feature.rms(S=S)

# LETTER CENTROIDS ---------------------------------------------------------------------
# this interpolates the centroid values, returns the centroid at a specific time (in seconds)
def returnLetterCentroid(chosenTime):
    return np.interp(chosenTime, times, cent[0])

# Using spaces from earlier to delete letter onset and offset times at the whitespace
for index in sorted(spaceIndexes, reverse=True):
    del LETTERonsetlist[index]

for index in sorted(spaceIndexes, reverse=True):
    del LETTERoffsetlist[index]

# convert letter onsets and offsets to floats
LETTERonsetlist_floats = [float(x) for x in LETTERonsetlist]
LETTERoffsetlist_floats = [float(x) for x in LETTERoffsetlist]

# create a list of midpoints for onsets and offsets: subtract offsets from onsets, then ROUND timings to 3 decimal places
LETTER_midPointEvent = [((element1 + element2) / 2) for (element1, element2) in zip(LETTERoffsetlist_floats, LETTERonsetlist_floats)]
LETTER_Rounded_midPointEvents = [round(element, 3) for element in LETTER_midPointEvent]

# return letter centroids for mid-point of onset/offset - because they are so short you only need one value
Letter_Centroids_List = [returnLetterCentroid(x) for x in LETTER_Rounded_midPointEvents]

# WORD CENTROIDS ---------------------------------------------------------------------
# return word centroid mean: take onset centroid, offset centroid and mid point centroid: return mean of those 3 values
def returnWordCentroid(chosenOnsetTime, chosenOffsetTime):
    Centroid_Samples = np.interp(chosenOnsetTime, times, cent[0]), np.interp(((chosenOffsetTime-chosenOnsetTime)/2), times, cent[0]), np.interp(chosenOffsetTime, times, cent[0])
    return np.mean(Centroid_Samples, dtype=np.float64)

# convert word onsets and offsets to floats
WORDonsetlist_floats = [float(x) for x in WORDonsetlist]
WORDoffsetlist_floats = [float(x) for x in WORDoffsetlist]

# create a list of word centroid mean values
WORD_meanCentroids_List = [(returnWordCentroid(element1, element2)) for (element1, element2) in zip(WORDonsetlist_floats, WORDoffsetlist_floats)]

# return sound/silence centroids: sample points between onset and offset and return mean centroid
def returnSound_Silence_Centroid(chosenOnsetTime, chosenOffsetTime):
    # create evenly spaced time samples to use: between onset and offset - currently set at 10 samples per sound/silence
    myTimeSamples = np.linspace(chosenOnsetTime,chosenOffsetTime,10).tolist()
    # return centroids for those sampled time values
    MySoundCentroids = [returnLetterCentroid(x) for x in myTimeSamples]
    return np.mean(MySoundCentroids, dtype=np.float64)

# convert sound/silence onsets and offsets to seconds: [0] for nested list
SOUNDonsetlist_seconds = [x / 1000 for x in SOUNDonsetList[0]]
SOUNDoffsetlist_seconds = [x / 1000 for x in SOUNDoffsetList[0]]

# return mean sound/silence centroid list
SOUND_meanCentroids_List = [(returnSound_Silence_Centroid(element1, element2)) for (element1, element2) in zip(SOUNDonsetlist_seconds, SOUNDoffsetlist_seconds)]


# Letters RMS ----------------------------------------------------------------------
def returnLetterRMS(chosenTime):
    return np.interp(chosenTime, times, rms[0])
Letter_RMS_List = [returnLetterRMS(x) for x in LETTER_Rounded_midPointEvents]
# scale values in letter RMS list to 0 - 4 and ROUND to nearest whole number
Letter_RMS_List_scaled_0_to_4 = np.interp(Letter_RMS_List,
                                     (min(Letter_RMS_List),
                                      max(Letter_RMS_List)), (0, +4))

Letter_Rounded_RMS_List_scaled = np.around(Letter_RMS_List_scaled_0_to_4)

# Words RMS ----------------------------------------------------------------------
def returnWordRMS(chosenOnsetTime, chosenOffsetTime):
    RMS_Samples = np.interp(chosenOnsetTime, times, rms[0]), np.interp(((chosenOffsetTime-chosenOnsetTime)/2), times, rms[0]), np.interp(chosenOffsetTime, times, rms[0])
    return np.mean(RMS_Samples, dtype=np.float64)
WORD_meanRMS_List = [(returnWordRMS(element1, element2)) for (element1, element2) in zip(WORDonsetlist_floats, WORDoffsetlist_floats)]

# scale values in word RMS list to 0 - 4 and ROUND to nearest whole number
Word_RMS_List_scaled_0_to_4 = np.interp(WORD_meanRMS_List,
                                     (min(WORD_meanRMS_List),
                                      max(WORD_meanRMS_List)), (0, +4))

Word_Rounded_RMS_List_scaled = np.around(Word_RMS_List_scaled_0_to_4)

# Sound/Silence RMS ----------------------------------------------------------------------
def returnSound_Silence_RMS(chosenOnsetTime, chosenOffsetTime):
    # create evenly spaced time samples to use: between onset and offset - currently set at 10 samples per sound/silence
    myTimeSamples = np.linspace(chosenOnsetTime,chosenOffsetTime,10).tolist()
    # return centroids for those sampled time values
    MySoundRMS = [returnLetterRMS(x) for x in myTimeSamples]
    return np.mean(MySoundRMS, dtype=np.float64)

SOUND_meanRMS_List = [(returnSound_Silence_RMS(element1, element2)) for (element1, element2) in zip(SOUNDonsetlist_seconds, SOUNDoffsetlist_seconds)]

# scale values in sound RMS list to 0 - 4 and ROUND to nearest whole number
Sound_RMS_List_scaled_0_to_4 = np.interp(SOUND_meanRMS_List,
                                     (min(SOUND_meanRMS_List),
                                      max(SOUND_meanRMS_List)), (0, +4))

Sound_Rounded_RMS_List_scaled = np.around(Sound_RMS_List_scaled_0_to_4)

# MOTOR SOUND ANALYSIS ---------------------------------------------------------------------------

# create list of motor sounds in the given folder
MOTORfiles = librosa.util.find_files('C:/Users/Fin/Desktop/pythonspeech/Motor_audio_individual')
motor_audios = Tcl().call('lsort', '-dict', MOTORfiles)
for i, v in enumerate(motor_audios):
    print(i, v)

# create list of individual motor centroids
motor_centroid_mean_list = []
def MOTOR_Return_motor_centroids(myFiles):
    for y in range(0, len(motor_audios)):
        y, sr = librosa.load(motor_audios[y])
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)
        mean_centroid = sum(cent[0])/len(cent[0])
        motor_centroid_mean_list.append(mean_centroid)

# return list of motor centroids, print along with the index number - used later
MOTOR_Return_motor_centroids(motor_audios)
for i, v in enumerate(motor_centroid_mean_list):
    print(i, v)

def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

All_MOTOR_Combinations_powerset = list(powerset(motor_centroid_mean_list))[1:]
Motor_index = list(powerset([1,2,3,4,5,6,7,8]))[1:]
# Means for each combination in the motor powerset list
Motor_combinations_centroid_means = [np.mean(x) for x in All_MOTOR_Combinations_powerset]

# SOUND MATCHING ---------------------------------------------------------------------------
# step 1. scaling: scale all values to numbers between 0 - 100
# MOTOR SCALING
MOTOR_Scaled_Centroids = np.interp(Motor_combinations_centroid_means,
                                     (min(Motor_combinations_centroid_means),
                                      max(Motor_combinations_centroid_means)), (0, +100))

# LETTER SCALING
LETTER_Scaled_Centroids = np.interp(Letter_Centroids_List,
                                     (min(Letter_Centroids_List),
                                      max(Letter_Centroids_List)), (0, +100))

# WORD SCALING
WORD_Scaled_Centroids = np.interp(WORD_meanCentroids_List,
                                     (min(WORD_meanCentroids_List),
                                      max(WORD_meanCentroids_List)), (0, +100))


# SOUND/SILENCE SCALING
SOUND_Scaled_Centroids = np.interp(SOUND_meanCentroids_List,
                                     (min(SOUND_meanCentroids_List),
                                      max(SOUND_meanCentroids_List)), (0, +100))


# match letter centroids to motor combination centroids
letter_match_list = []
def matching_letter_Centroids(mydataset):
    for x in range(0, len(LETTER_Scaled_Centroids)):
        idx = (np.abs(MOTOR_Scaled_Centroids - mydataset[x])).argmin()
        letter_match_list.append(idx) # it is appending the index of the motor group - to be matched to index later

matching_letter_Centroids(LETTER_Scaled_Centroids)

# match word centroids to motor combination centroids
word_match_list = []
def matching_word_Centroids(mydataset):
    for x in range(0, len(WORD_Scaled_Centroids)):
        idx = (np.abs(MOTOR_Scaled_Centroids - mydataset[x])).argmin()
        word_match_list.append(idx) # it is appending the index of the motor group - to be matched to index later

matching_word_Centroids(WORD_Scaled_Centroids)

# match sound/silence centroids to motor combination centroids
SOUND_match_list = []
def matching_SOUND_Centroids(mydataset):
    for x in range(0, len(SOUND_Scaled_Centroids)):
        idx = (np.abs(MOTOR_Scaled_Centroids - mydataset[x])).argmin()
        SOUND_match_list.append(idx) # it is appending the index of the motor group - to be matched to index later

matching_SOUND_Centroids(SOUND_Scaled_Centroids)

# match index of motor sound to the motor numbers, produce final lists of motor numbers LETTER/WORD/PHONEME
# LETTER MOTOR NUMBER MATCH LIST
LETTER_motorNum_match_list = [Motor_index[x] for x in letter_match_list]
# WORD MOTOR NUMBER MATCH LIST
WORD_motorNum_match_list = [Motor_index[x] for x in word_match_list]
# SOUND/SILENCE MOTOR NUMBER MATCH LIST
SOUND_motorNum_match_list = [Motor_index[x] for x in SOUND_match_list]

# convert sound/silence onsets + offsets to seconds
SOUNDonsetList_array = (np.array(SOUNDonsetList)/1000)
SOUNDoffsetList_array = (np.array(SOUNDoffsetList)/1000)

# round to 2 decimal places
rounded_SOUND_onsetsarray = SOUNDonsetList_array.round(2)
rounded_SOUND_offsetsarray = SOUNDoffsetList_array.round(2)

# to lists
rounded_SOUND_onset_list_2 = rounded_SOUND_onsetsarray.tolist()
rounded_SOUND_offset_list_2 = rounded_SOUND_offsetsarray.tolist()

# LETTER DATA -----------
LETTER_motorNum_match_list
LETTERonsetlist_floats
LETTERoffsetlist_floats

# WORD DATA -------------
WORD_motorNum_match_list
WORDonsetlist_floats
WORDoffsetlist_floats

# SOUND / SILENCE DATA -------------
SOUND_motorNum_match_list
rounded_SOUND_onset_list_2
rounded_SOUND_offset_list_2