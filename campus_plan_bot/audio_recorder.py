import threading
import wave

import pyaudio
from pynput import keyboard


class AudioRecorder:
    def __init__(self, output_filename: str):
        self.format = pyaudio.paInt16  # Audio format
        self.channels = 1  # Number of audio channels (mono needed for whisper)
        self.rate = 44100  # Sample rate (oversampling compared to whisper input)
        self.chunk = 1024  # Buffer size
        self.output_filename = output_filename
        self.audio = pyaudio.PyAudio()
        self.frames = [bytes]
        self.is_recording = False
        self.listener = None

    def record_audio(self):
        self.is_recording = False
        self.frames.clear()  # Clear any previous frames

        # Start the keyboard listener
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        print("Press the spacebar to start recording.")

        # Wait for the listener to stop
        self.listener.join()

        self.audio.terminate()
        return

    def on_press(self, key):
        if key == keyboard.Key.space and not self.is_recording:
            self.is_recording = True
            print("Recording ... press the spacebar again to stop.")
            self.start_recording_thread()
        elif key == keyboard.Key.space and self.is_recording:
            self.is_recording = False
            print("Stopped recording.")
            self.stop_recording()
            self.listener.stop()  # Stop the listener

    def start_recording_thread(self):
        recording_thread = threading.Thread(target=self.start_recording)
        recording_thread.start()

    def start_recording(self):
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
        )

        while self.is_recording:
            data = stream.read(self.chunk)
            self.frames.append(data)

        stream.stop_stream()
        stream.close()

    def stop_recording(self):
        # Save the recorded data as a .wav file
        with wave.open(self.output_filename, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b"".join(self.frames))
        self.frames.clear()  # Clear frames for the next recording
