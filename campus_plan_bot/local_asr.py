import torch
import torchaudio
from audio_recorder import AudioRecorder
from transformers import WhisperForConditionalGeneration, WhisperProcessor

device = "cuda:0" if torch.cuda.is_available() else "cpu"
"""Several options for local whisper models with associated storage sizes When
choosing a new model it will be automatically downloaded and cached."""
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
whisper_processor = WhisperProcessor.from_pretrained(whisper_model_name)
whisper_model = WhisperForConditionalGeneration.from_pretrained(whisper_model_name).to(
    device
)


def load_audio(audio_path):
    """Load the audio file & convert to 16,000 sampling rate."""
    # load our wav file
    speech, sr = torchaudio.load(audio_path)
    resampler = torchaudio.transforms.Resample(sr, 16000)
    speech = resampler(speech)
    return speech.squeeze()


def get_transcription_whisper(
    audio_path, model, processor, language="english", skip_special_tokens=True
):
    # resample from whatever the audio sampling rate to 16000
    speech = load_audio(audio_path)
    # get the input features from the audio file
    input_features = processor(
        speech,
        return_tensors="pt",
        padding="longest",
        return_attention_mask=True,
        sampling_rate=16000,
    ).input_features.to(device)
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
    transcription = processor.batch_decode(
        predicted_ids, skip_special_tokens=skip_special_tokens
    )[0]
    return transcription


def main():
    recorder = AudioRecorder(filename="out.wav")
    recorder.record_audio()
    print("Transcribing audio...")
    transcription = get_transcription_whisper(
        "out.wav",
        whisper_model,
        whisper_processor,
        language="german",
        skip_special_tokens=True,
    )
    print("German transcription:", transcription)


if __name__ == "__main__":
    main()
