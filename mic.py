import asyncio
import websockets
import json
import io
import speech_recognition as sr

async def microphone_client():
    async with websockets.connect(
            'ws://localhost:2222') as websocket:
        r = sr.Recognizer()
        mic = sr.Microphone(sample_rate= 16000)
        while True:
            try:
                with mic as source:
                    r.adjust_for_ambient_noise(source)
                    audio = r.record(source,  duration=6)
                    data = b'MICROPHONE:' + audio.get_wav_data()
                    await websocket.send(data)
                    server_response = await websocket.recv()
                    print(server_response)
            except KeyboardInterrupt:
                break

asyncio.run(microphone_client())