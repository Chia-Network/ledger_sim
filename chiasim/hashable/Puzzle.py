from ..atoms import streamable, hexbytes


@streamable
class Puzzle:
    code: hexbytes

    def stream(self, f):
        f.write(self.code)
