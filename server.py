import websockets
import os
import multiprocessing as mp
import threading
import websockets.connection
import websockets.exceptions
import websockets.sync
import websockets.sync.server
import copy
import socket
import wave
import pyaudio
import pyaudiowpatch as pyaudiop
from faster_whisper import WhisperModel
from pydub import AudioSegment
import io
import requests
from pydub.silence import split_on_silence
from fastapi import FastAPI, WebSocket
from phi3_model import Phi3Model

app = FastAPI()

transcription_queue = mp.Queue()
searching_queue = mp.Queue()
sending_queue = mp.Queue()

class SavingAudios:
    
    def __init__(self, channel_speaker = 2, channel_micro = 1, samplerate_speaker = 44100, samplerate_micro = 16000):
        self.paudio = pyaudiop.PyAudio()
        self.channel_speaker = channel_speaker
        self.channel_micro = channel_micro
        self.samplerate_speaker = samplerate_speaker
        self.samplerate_micro = samplerate_micro

    def save_audio_micro(self, data, name_file_micro):        
        wf = wave.open(name_file_micro, 'wb')
        wf.setnchannels(self.channel_micro)
        wf.setsampwidth(self.paudio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self.samplerate_micro)
        wf.writeframes(data)
        wf.close()

    def save_audio_speaker(self, data, name_file_speaker):
        wf = wave.open(name_file_speaker, 'wb')
        wf.setnchannels(self.channel_speaker)
        wf.setsampwidth(self.paudio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self.samplerate_speaker)
        wf.writeframes(data)
        wf.close()

class TranscriberThread(threading.Thread):

    def __init__(self, ws: socket.socket, running_flag : mp.Event):
        threading.Thread.__init__(self, daemon=True)
        self.saving_job = SavingAudios()
        self.model = WhisperModel("base.en")
        self.ws = ws
        self.running_flag = running_flag

    def run(self):
        print("Start Transcriber service")
        count_check  = 0
        while self.running_flag.is_set():
            try:
                raw_data = self.ws.recv()
                if len(raw_data) > 0:
                    count_check +=1
                    if raw_data.startswith(b'SPEAKER:'):
                        self.saving_job.save_audio_speaker(raw_data[8:], f"./audios/speaker_audio_{count_check}.wav")
                        result, _ = self.model.transcribe(f"./audios/speaker_audio_{count_check}.wav", vad_filter=True, vad_parameters=dict(min_silence_duration_ms=1500))
                        segments = list(result)
                        text = " ".join([segment.text for segment in segments])
                        
                        transcription_queue.put(text)
                        
                        if len(text) > 0 :
                            print("SPEAKER CALLER: " + text.strip())
                    else:
                        self.saving_job.save_audio_micro(raw_data[11:], f"./audios/microphone_audio_{count_check}.wav")
                        result, _ = self.model.transcribe(f"./audios/microphone_audio_{count_check}.wav", vad_filter=True, vad_parameters=dict(min_silence_duration_ms=1500))
                        segments = list(result)
                        text = " ".join([segment.text for segment in segments])
                        
                        searching_queue.put(text)
                        print("MICROPHONE CALLER: " + text.strip())
            except Exception as e:
                print(e)
                break

class SearchingThread(threading.Thread):

    def __init__(self, ws: socket.socket, running_flag : mp.Event):
        threading.Thread.__init__(self, daemon=True)
        self.running_flag = running_flag
        self.model = Phi3Model()
        self.ws = ws
    
    def run(self):
        count_check = 0
        print("Start Analyzing service")
        while self.running_flag.is_set():
            try:
                text_transcription = searching_queue.get()
                if len(text_transcription) > 0:
                    count_check +=1
                    response_llm = self.model.search(text_transcription)
                    self.ws.send(response_llm)
            except Exception as e:
                print(e)
                break 
            
def main(ws: socket.socket):
    
    running_flag = mp.Event()
    running_flag.set()

    transcriber_thread = TranscriberThread(ws, running_flag)
    searching_thread = SearchingThread(ws, running_flag)

    transcriber_thread.start()
    searching_thread.start()

    transcriber_thread.join()
    searching_thread.join()

if __name__ == '__main__':
    try:
        with websockets.sync.server.serve(main, "localhost", 2222) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        import sys
        sys.exit()
    finally:
        import sys
        sys.exit()
        