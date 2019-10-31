import io

from typing import Any

from .hexbytes import hexbytes


class bin_methods:
    """
    Create "from_bytes" and "as_bin" methods in terms of "parse" and "stream" methods.
    """
    @classmethod
    def from_bytes(cls, blob: bytes) -> Any:
        f = io.BytesIO(blob)
        return cls.parse(f)

    def as_bin(self) -> hexbytes:
        f = io.BytesIO()
        self.stream(f)
        return hexbytes(f.getvalue())
