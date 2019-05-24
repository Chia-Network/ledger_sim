import dataclasses

from typing import Tuple

from .Hash import Hash
from .Streamable import Streamable


@dataclasses.dataclass(frozen=True)
class Removals(Streamable):
    coin_ids: Tuple[Hash]
