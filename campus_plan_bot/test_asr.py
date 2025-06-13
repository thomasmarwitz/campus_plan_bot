#!/usr/bin/env python3

import os
import subprocess
import tempfile

import click
from loguru import logger

from campus_plan_bot.local_asr import LocalASR
from campus_plan_bot.remote_asr import RemoteASR
from campus_plan_bot.settings import Settings


def convert_to_wav(input_file: str) -> str:
    """Convert audio file to WAV format using ffmpeg."""
    # Create a temporary WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
        temp_wav_path = temp_wav.name
    
    try:
        # Convert to WAV using ffmpeg
        subprocess.run([
            'ffmpeg', '-i', input_file,
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '16000',  # 16kHz sampling rate
            '-ac', '1',  # mono
            '-y',  # overwrite output file
            temp_wav_path
        ], check=True, capture_output=True)
        
        return temp_wav_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting file: {e}")
        if os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)
        raise


def test_asrs(audio_file: str):
    """Test both ASR implementations with the same audio file."""

    logger.info(f"Testing ASR with {audio_file}")
    logger.debug(f"Token: {Settings().load_settings('token')[:10]}")
    
    # Convert to WAV for Local ASR if needed
    wav_file = None
    if not audio_file.lower().endswith('.wav'):
        logger.info(f"Converting {audio_file} to WAV format for Local ASR...")
        wav_file = convert_to_wav(audio_file)
    else:
        wav_file = audio_file
    
    try:
        # Initialize ASR implementations
        local_asr = LocalASR(wav_file)
        remote_asr = RemoteASR(wav_file)  # Remote ASR can handle M4A directly
        
        # Test local ASR
        logger.info("Testing Local ASR...")
        local_transcript = local_asr.transcribe(wav_file)
        logger.info(f"Local ASR transcript: {local_transcript}")
        
        # Test remote ASR
        logger.info("\nTesting Remote ASR...")
        remote_transcript = remote_asr.transcribe(audio_file)
        logger.info(f"Remote ASR transcript: {remote_transcript}")
        
        # Print comparison
        logger.info("\nComparison:")
        logger.info("-" * 50)
        logger.info(f"Local ASR:  {local_transcript}")
        logger.info(f"Remote ASR: {remote_transcript}")
    
    finally:
        # Clean up temporary WAV file if we created one
        if wav_file != audio_file and wav_file and os.path.exists(wav_file):
            os.unlink(wav_file)


@click.command()
@click.argument('audio_file', type=click.Path(exists=True))
def main(audio_file: str):
    """Compare local and remote ASR implementations on the same audio file."""
    test_asrs(audio_file)


if __name__ == "__main__":
    main() 