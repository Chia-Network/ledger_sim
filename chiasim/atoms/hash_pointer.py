from .bin_methods import bin_methods

from typing import get_type_hints


def hash_pointer(the_type, hash_f):
    """
    Create a "cryptographic pointer" type that can accept either a hash or an instance
    of the type. It can also reconstruct the underlying the object given a data source.

    The resulting type subclasses "bin_methods", and can stream and parse itself.
    """
    hash_type = get_type_hints(hash_f)["return"]

    def __new__(self, v):
        if isinstance(v, the_type):
            self._obj = v
            v = hash_f(v.as_bin())
        return hash_type.__new__(self, v)

    async def obj(self, data_source=None):
        """
        Return the underlying object that has the given hash. If it's not already in memory,
        it builds it using the blob from the given data source.
        """
        if self._obj is None and data_source:
            blob = await data_source.blob_for_hash(self)
            if hash_f(blob) == self:
                self._obj = the_type.from_bin(blob)
        return self._obj

    def stream(self, f):
        f.write(self)

    namespace = dict(__new__=__new__, obj=obj)
    hash_pointer_type = type(
        "%sPointer" % the_type.__name__, (hash_type, bin_methods,), namespace)
    return hash_pointer_type
