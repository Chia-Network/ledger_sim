from ..atoms import streamable, hexbytes


@streamable
class Solution:
    code: hexbytes

    def stream(self, f):
        f.write(self.code)
