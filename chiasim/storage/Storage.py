from ..hashable import Hash, Unspent


class Storage:

    async def hash_preimage(self, hash: Hash) -> bytes:
        raise NotImplementedError

    async def add_preimage(self, blob: bytes) -> None:
        raise NotImplementedError

    async def merkle_preimage(self, hash: Hash) -> bytes:
        raise NotImplementedError

    async def add_merkle_preimage(self, tree) -> None:
        raise NotImplementedError


class UnspentDB:
    async def unspent_for_coin_name(self, coin_name: Hash) -> Unspent:
        raise NotImplementedError

    async def set_unspent_for_coin_name(self, coin_name: Hash, unspent: Unspent) -> None:
        raise NotImplementedError

    async def rollback_to_block(self, uint32):
        raise NotImplementedError
