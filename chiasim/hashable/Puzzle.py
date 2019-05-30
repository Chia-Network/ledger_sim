from ..atoms import streamable, hexbytes


@streamable
class Puzzle:
    code: hexbytes
