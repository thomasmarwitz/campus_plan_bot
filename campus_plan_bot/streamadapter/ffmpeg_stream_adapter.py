import subprocess
import time
from typing import Any, Optional, cast

from campus_plan_bot.streamadapter.input_stream_adapter import BaseAdapter


class FfmpegStream(BaseAdapter):
    def __init__(self, **kwargs) -> None:
        """Requires named parameter pre_input and post_output, volume,
        repeat_input."""
        if "pre_input" not in kwargs or kwargs["pre_input"] is None:
            kwargs["pre_input"] = ""
        if "post_input" not in kwargs or kwargs["post_input"] is None:
            kwargs["post_input"] = ""
        self._process: Optional[subprocess.Popen] = None
        self.url: Optional[str] = None
        self.pre_opt: list[str] = kwargs["pre_input"].split()
        self.post_opt: list[str] = kwargs["post_input"].split()
        self.volume: float = kwargs["volume"]
        self.repeat_input: bool = kwargs["repeat_input"]
        super().__init__(format=None)

        self.speed = kwargs["ffmpeg_speed"] if "ffmpeg_speed" in kwargs else -1.0

    def available(self) -> bool:
        import shutil

        if shutil.which("ffmpeg") is None:
            return False
        else:
            return True

    def get_stream(self, **kwargs) -> Any:
        if self.url is None:
            print("URL is None")
            raise ValueError("self.url must be a valid string.")
        if self._process is None:
            self.start_time = time.time()
            self.seconds_returned = 0
            self.chunk_size = 2 * 960 if self.speed != -1.0 else 167 * 2 * 960

            args: list[str] = [
                "ffmpeg",
                # be less verbose (but still show stats)
                "-hide_banner",
                "-loglevel",
                "error",  # "-stats",
            ]
            if len(self.pre_opt) > 0:
                args += self.pre_opt
            args += [
                # ignore video tracks
                # "-re",
                # "-rtsp_transport", "tcp",
                "-vn",
                "-i",
                self.url,
                *self.post_opt,
            ]
            if len(self.post_opt) > 0:
                args += self.post_opt
            args += [
                # use the first audio channel
                "-map",
                "0:a",
                "-ac",
                "1",
                "-channel_layout",
                "mono",
                # adjust volume
                "-filter:a",
                f"volume={self.volume}",
                # convert to 16kHz signed little endian, one audio channel only
                "-f",
                "s16le",
                "-ar",
                str(self.rate),
                "-c:a",
                "pcm_s16le",
                "-",
            ]
            self._process = subprocess.Popen(
                args, stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
        return self._process.stdout

    def read(self) -> bytes:
        stream = self.get_stream()
        if self.speed != -1.0:
            sleep = self.seconds_returned - (time.time() - self.start_time)
            if sleep > 0:
                time.sleep(sleep)
                if self.chunk_size > 2 * 960:
                    self.chunk_size -= 2 * 960
            else:
                if sleep < -5:
                    print(
                        "WARNING: Network is to slow. Having at least 5 seconds of delay!"
                    )
                self.chunk_size += 2 * 960
        chunk = cast(bytes, stream.read(self.chunk_size))
        if self._process is not None and self._process.poll() is not None:
            if self.repeat_input and len(chunk) == 0:
                self._process = None
                return self.read()
                # return self.read(self.chunk_size)
            elif not self.repeat_input and self._process.returncode == 0:
                pass  # first finish returning the rest of chunks and then an empty chunk is send. After the empty chunk the file is over
        self.seconds_returned += len(chunk) / 2 / self.rate / self.speed
        return chunk

    def chunk_modify(self, chunk: bytes) -> bytes:
        return chunk

    def cleanup(self) -> None:
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    def set_input(self, input: str) -> None:
        self.url = input
