#!/usr/bin/env python3

from abc import ABCMeta, abstractmethod
from typing import Any, Optional


class BaseAdapter(metaclass=ABCMeta):
    def __init__(self, format: Any) -> None:
        self.rate = 16000
        self.format = format
        self.channel_count = 1
        self.chosen_channel: Optional[int] = None

    def available(self) -> bool:
        """Should return if the backend is available and print an error message
        if not.

        Called before setting input
        """
        return True

    @abstractmethod
    def get_stream(self, **kwargs) -> Any:
        """Should return the stream for reading."""
        pass

    @abstractmethod
    def read(self) -> bytes:
        """Should return a chunk of bytes from the audio device."""
        pass

    def chunk_modify(self, chunk: bytes) -> bytes:
        """Allows modifying of the chunk."""
        return chunk

    @abstractmethod
    def cleanup(self) -> None:
        """Should be called after the session was closed."""
        pass

    @abstractmethod
    def set_input(self, input: Any) -> None:
        """Should be called to set an input, which can be for example an id,
        string etc."""
        pass
