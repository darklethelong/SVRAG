import asyncio
import websockets
import threading

# Function to handle the WebSocket connection and receive messages
async def receive_transcriptions(uri):
    async with websockets.connect(uri) as websocket:
        while True:
            transcription = await websocket.recv()
            print(f"Transcription: {transcription}")

# Function to run the WebSocket client in a separate thread
def run_websocket_client(uri):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(receive_transcriptions(uri))
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

# Main function to start the WebSocket client thread
def main():
    uri = "ws://localhost:8765"
    client_thread = threading.Thread(target=run_websocket_client, args=(uri,))
    client_thread.daemon = True
    client_thread.start()

    # Keep the main thread running to allow the client thread to continue
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Client stopped.")

if __name__ == "__main__":
    main()