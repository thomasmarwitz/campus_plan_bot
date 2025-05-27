import threading
import wave

import click
import pyaudio
from pynput import keyboard


class AudioRecorder:
    """Create audio recording as file from device microphones."""

    def __init__(
        self, filename="campus_plan_bot/out.wav", channels=1, rate=44100, chunk=1024
    ):
        self.filename = filename
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.frames = [bytes]
        self.p = pyaudio.PyAudio()
        self.recording = False
        self.recording_thread = None
        self.listener = None

    def record(self):
        """Start recording audio in a background thread."""
        self.frames = []

        self.recording = True
        stream = self.p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
        )
        click.echo("Recording...", nl=False)

        while self.recording:
            data = stream.read(self.chunk)
            self.frames.append(data)

        stream.stop_stream()
        stream.close()
        self.p.terminate()

    def end_recording(self):
        """Stop recording audio and save to file."""
        click.echo("Recording stopped.")
        self.recording = False

        # Save the recorded data as a .wav file
        with wave.open(self.filename, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.rate)
            wf.writeframes(b"".join(self.frames))
        self.frames.clear()

    def start(self):
        """Start background thread for recording."""
        self.recording_thread = threading.Thread(target=self.record)
        self.recording_thread.start()

    def stop(self):
        """Stop background thread for recording."""
        self.end_recording()
        self.recording_thread.join()

    def on_press(self, key):
        """Register keypress."""
        if key == keyboard.Key.space and not self.recording:
            self.start()

    def on_release(self, key):
        """Register key release."""
        if key == keyboard.Key.space:
            self.stop()
            return False

    def record_audio(self):
        """Create an audio recording."""
        self.listener = keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release, suppress=True
        )
        self.listener.start()
        click.echo("Press and hold the spacebar to record your input.")

        # Wait for the listener to stop
        self.listener.join()


if __name__ == "__main__":
    recorder = AudioRecorder(filename="campus_plan_bot/out.wav")
    recorder.record_audio()
