import asyncio
import websockets
import pyaudio
import pyaudiowpatch as pyaudiop
import numpy as np

# Audio settings
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 6000
SECONDS = 12

# Silence detection settings
SILENCE_THRESHOLD = 500  # Adjust this value based on your needs
SILENCE_CHUNKS = 5  # Number of consecutive chunks to consider as silence

def get_default_loopback_device(paudio):
    wasapi = paudio.get_host_api_info_by_type(pyaudiop.paWASAPI)
    default_device = paudio.get_device_info_by_index(wasapi['defaultOutputDevice'])
    loopback_device = default_device
    # get the loopback device (same name and isLoopbackDevice)
    devices = paudio.get_device_info_generator_by_host_api(host_api_index=wasapi['index'])
    lb_devices = [d for d in devices if d['maxInputChannels'] > 0 and d['isLoopbackDevice']]
    for d in lb_devices:
        if default_device['name'] in d['name']:
            loopback_device = d
    return loopback_device

paudio = pyaudiop.PyAudio()
loopback_device = get_default_loopback_device(paudio)
print("loopback_device", loopback_device)

def is_silent(data_chunk, threshold):
    """Check if a chunk of data is silent."""
    as_ints = np.frombuffer(data_chunk, dtype=np.int16)
    return np.max(np.abs(as_ints)) < threshold

async def send_audio():
    async with websockets.connect('ws://localhost:2222') as websocket:
        stream = paudio.open(format=FORMAT, channels=CHANNELS,
                             rate=RATE, input=True,
                             frames_per_buffer=CHUNK,
                             input_device_index=loopback_device['index'])

        print("Recording from speaker...")
        silent_chunks = 0
        frames = []

        while True:
            try:
                data = stream.read(CHUNK)
                if is_silent(data, SILENCE_THRESHOLD):
                    silent_chunks += 1
                    if silent_chunks > SILENCE_CHUNKS and frames:
                        # Send accumulated non-silent audio
                        await websocket.send(b'SPEAKER:' + b''.join(frames))
                        server_response = await websocket.recv()
                        print(server_response)
                        frames = []
                else:
                    silent_chunks = 0
                    frames.append(data)

                if len(frames) >= int(RATE / CHUNK * SECONDS):
                    # Send accumulated audio if buffer is full
                    await websocket.send(b'SPEAKER:' + b''.join(frames))
                    server_response = await websocket.recv()
                    print(server_response)
                    frames = []

            except KeyboardInterrupt:
                print("Stopping recording")
                break
            except Exception as e:
                print(f"Error: {e}")
                break

        # Close the stream
        stream.stop_stream()
        stream.close()
        paudio.terminate()

asyncio.run(send_audio())