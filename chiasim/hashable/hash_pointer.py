from .Hash import std_hash

from typing import get_type_hints


def hash_pointer(the_type, hash_f=std_hash):

    hash_type = get_type_hints(std_hash)["return"]

    def __new__(self, v):
        if isinstance(v, the_type):
            self._obj = v
            v = hash_f(v.as_bin())
        return hash_type.__new__(self, v)

    async def obj(self, data_source=None):
        if self._obj is None and data_source:
            blob = await data_source.fetch(self)
            if hash_f(blob) == self:
                self._obj = the_type.from_bin(blob)
        return self._obj

    namespace = dict(__new__=__new__, obj=obj)
    hash_pointer_type = type(
        "%sPointer" % the_type.__name__, (hash_type,), namespace)
    return hash_pointer_type
