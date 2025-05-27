import click
import torch
import torchaudio
from audio_recorder import AudioRecorder
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from campus_plan_bot.interfaces import AutomaticSpeechRecognition


class LocalASR(AutomaticSpeechRecognition):
    """Creating transcript from audio file with local whisper model."""

    def __init__(self):

        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        """Several options for local whisper models with associated storage
        sizes When choosing a new model it will be automatically downloaded and
        cached."""
        # whisper_model_name = "openai/whisper-tiny.en" # English-only, ~ 151 MB
        # whisper_model_name = "openai/whisper-base.en" # English-only, ~ 290 MB
        # whisper_model_name = "openai/whisper-small.en" # English-only, ~ 967 MB
        # whisper_model_name = "openai/whisper-medium.en" # English-only, ~ 3.06 GB
        # whisper_model_name = "openai/whisper-tiny" # multilingual, ~ 151 MB
        whisper_model_name = "openai/whisper-base"  # multilingual, ~ 290 MB
        # whisper_model_name = "openai/whisper-small" # multilingual, ~ 967 MB
        # whisper_model_name = "openai/whisper-medium" # multilingual, ~ 3.06 GB
        # whisper_model_name = "openai/whisper-large-v2" # multilingual, ~ 6.17 GB

        # load the model and the processor
        self.whisper_processor = WhisperProcessor.from_pretrained(whisper_model_name)
        self.whisper_model = WhisperForConditionalGeneration.from_pretrained(
            whisper_model_name
        ).to(self.device)

    def load_audio(self, audio_path):
        """Load the audio file & convert to 16,000 sampling rate."""

        # load our wav file
        speech, sr = torchaudio.load(audio_path)
        resampler = torchaudio.transforms.Resample(sr, 16000)
        speech = resampler(speech)
        return speech.squeeze()

    def whisper_transcription(
        self, audio, model, processor, language="english", skip_special_tokens=True
    ) -> str:
        """Transcribe the provided torch audio vector with specified whisper
        model."""

        # get the input features from the audio file
        input_features = processor(
            audio,
            return_tensors="pt",
            padding="longest",
            return_attention_mask=True,
            sampling_rate=16000,
        ).input_features.to(self.device)

        # get the forced decoder ids
        forced_decoder_ids = processor.get_decoder_prompt_ids(
            language=language, task="transcribe"
        )

        # NOTE: this attention mask is experimental to silence warning - check that giving all ones does not mess up model prediction
        attention_mask = torch.ones(input_features.shape, dtype=torch.long)

        # generate the transcription
        predicted_ids = model.generate(
            input_features,
            attention_mask=attention_mask,
            forced_decoder_ids=forced_decoder_ids,
        )
        # decode the predicted ids
        whisper_transcript = processor.batch_decode(
            predicted_ids, skip_special_tokens=skip_special_tokens
        )[0]
        return whisper_transcript

    def transcribe(self, audio_path: str) -> str:
        """Create transcript for specified audio file."""

        audio = self.load_audio(audio_path)

        transcript = self.whisper_transcription(
            audio,
            self.whisper_model,
            self.whisper_processor,
            language="german",
            skip_special_tokens=True,
        )
        return transcript

    def get_input(self) -> str:
        """Get audio input from the user and return the transcript."""

        filename = "campus_plan_bot/out.wav"
        recorder = AudioRecorder(filename)

        interrupt = recorder.record_audio()
        if interrupt:
            return "exit"
        else:
            transcript = self.transcribe(filename).lstrip()
            print("\033[A                                                  \033[A")
            click.secho("You: ", fg="blue", nl=False)
            click.echo(f"{transcript}")
            return transcript


if __name__ == "__main__":
    asr = LocalASR()
    text = asr.get_input()
