import dataclasses

from typing import Tuple

from .Coin import Coin
from .Streamable import Streamable


@dataclasses.dataclass(frozen=True)
class Additions(Streamable):
    coins: Tuple[Coin]
