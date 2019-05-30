import io

from typing import Any

from .hexbytes import hexbytes


class bin_methods:
    @classmethod
    def from_bin(cls, blob: bytes) -> Any:
        f = io.BytesIO(blob)
        return cls.parse(f)

    def as_bin(self) -> hexbytes:
        f = io.BytesIO()
        self.stream(f)
        return hexbytes(f.getvalue())
