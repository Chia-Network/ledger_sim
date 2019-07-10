import asyncio
import collections
import dataclasses
import time

from chiasim.coin.consensus import (
    additions_for_body, coin_for_coin_name, conditions_dict_for_solution,
    created_outputs_for_conditions_dict, hash_key_pairs_for_conditions_dict,
    removals_for_body, solution_program_output
)
from chiasim.hashable import (
    BLSSignature, Hash, HeaderHash, SpendBundle, Unspent, std_hash
)
from chiasim.storage import RAM_DB, Storage, UnspentDB

from .ConsensusError import ConsensusError


def check_conditions_dict(coin, conditions_dict, chain_view):
    """
    Check all conditions against current state.
    """
    pass


class RAMUnspentDB(UnspentDB):
    def __init__(self, additions, confirmed_block_index):
        self._db = {}
        for _ in additions:
            unspent = Unspent(_.amount, confirmed_block_index, 0)
            self._db[_.coin_name()] = unspent

    async def unspent_for_coin_name(self, coin_name: Hash) -> Unspent:
        return self._db.get(coin_name)


class OverlayUnspentDB(UnspentDB):
    def __init__(self, *db_list):
        self._db_list = db_list

    async def unspent_for_coin_name(self, coin_name: Hash) -> Unspent:
        for db in self._db_list:
            v = await db.unspent_for_coin_name(coin_name)
            if v is not None:
                return v
        return None


class OverlayStorage(Storage):
    def __init__(self, *db_list):
        self._db_list = db_list

    async def hash_preimage(self, hash: Hash) -> bytes:
        for db in self._db_list:
            v = await db.hash_preimage(hash)
            if v is not None:
                return v
        return None


@dataclasses.dataclass
class ChainView:
    genesis_hash: HeaderHash
    tip_hash: HeaderHash
    tip_index: int
    unspent_db: UnspentDB

    @classmethod
    def for_genesis_hash(cls, genesis_hash: HeaderHash, unspent_db: UnspentDB):
        return cls(genesis_hash, genesis_hash, 0, unspent_db)

    async def accept_new_block(
            self, header: HeaderHash, header_signature: BLSSignature, storage: Storage):
        """
        Checks the block against the existing ChainView object.
        Returns a list of additions and removals.

        Missing blobs must be resolvable by storage.

        If the given block is invalid, a ConsensusError is raised.
        """

        try:
            # verify header extends current view

            if header.previous_hash != self.tip_hash:
                raise ConsensusError.DOES_NOT_EXTEND

            # verify header signature

            pos = await header.proof_of_space_hash.obj(storage)
            if pos is None:
                raise ConsensusError.MISSING_FROM_STORAGE
            hkp = header_signature.aggsig_pair(pos.plot_public_key, header.hash())
            if not header_signature.validate([hkp]):
                raise ConsensusError.BAD_HEADER_SIGNATURE

            # verify coinbase signature

            body = await header.body_hash.obj(storage)
            if body is None:
                raise ConsensusError.MISSING_FROM_STORAGE
            hkp = body.coinbase_signature.aggsig_pair(pos.pool_public_key, body.coinbase_coin.hash())
            if not body.coinbase_signature.validate([hkp]):
                raise ConsensusError.BAD_COINBASE_SIGNATURE

            # ensure block program generates solutions

            try:
                coin_name_solution_pairs = solution_program_output(body)
            except Exception:
                breakpoint()
                raise ConsensusError.INVALID_BLOCK_SOLUTION

            # build conditions_dict for each removal

            conditions_dicts = []
            for (coin_name, solution) in coin_name_solution_pairs:
                conditions_dicts.append(conditions_dict_for_solution(solution))

            # get additions and removals

            additions = collections.Counter()
            additions.update([body.coinbase_coin, body.fees_coin])
            for conditions_dict in conditions_dicts:
                for (coin_name, solution), conditions_dict in zip(
                        coin_name_solution_pairs, conditions_dicts):
                    for _ in created_outputs_for_conditions_dict(conditions_dict, coin_name):
                        additions.update([_])

            removals = collections.Counter(_[0] for _ in coin_name_solution_pairs)

            # create a temporary overlay DB with the additions
            ram_storage = RAM_DB()
            for _ in additions:
                await ram_storage.add_preimage(_.coin_name_data().as_bin())

            ram_db = RAMUnspentDB(additions.keys(), self.tip_index + 1)
            overlay_storage = OverlayStorage(ram_storage, storage)
            unspent_db = OverlayUnspentDB(self.unspent_db, ram_db)

            coin_futures = [asyncio.ensure_future(
                coin_for_coin_name(_[0], overlay_storage, unspent_db)) for _ in coin_name_solution_pairs]

            coin_puzzle_solution_tuples = []
            for coin_future, (puzzle, solution) in zip(coin_futures, coin_name_solution_pairs):
                coin = await coin_future
                if coin is None:
                    raise ConsensusError.UNKNOWN_UNSPENT
                coin_puzzle_solution_tuples.append((coin, puzzle, solution))

            # check that the revealed removal puzzles actually match the puzzle hash
            for coin, puzzle, solution in coin_puzzle_solution_tuples:
                revealed_puzzle_hash = std_hash(solution.first().as_bin())
                if revealed_puzzle_hash != coin.puzzle_hash:
                    raise ConsensusError.WRONG_PUZZLE_HASH

            #  watch out for double-spends

            if additions and max(additions.values()) > 1:
                raise ConsensusError.DUPLICATE_OUTPUT

            if removals and max(removals.values()) > 1:
                raise ConsensusError.DOUBLE_SPEND

            # symmetric_difference of additions and removals
            in_both = []
            for _ in additions.keys():
                if _.coin_name() in removals:
                    in_both.append(_)
            for _ in in_both:
                del additions[_]
                del removals[_.coin_name()]

            # check removals against UnspentDB
            for coin_name in removals.values():
                unspent = await unspent_db.unspent_for_coin_name(coin_name)
                if (unspent is None or
                        unspent.confirmed_block_index == 0 or
                        unspent.confirmed_block_index >= self.tip_index):
                    raise ConsensusError.UNKNOWN_UNSPENT
                if (0 < unspent.spent_block_index <= self.tip_index):
                    raise ConsensusError.DOUBLE_SPEND

            # check solution for each CoinSolution pair
            # this is where CHECKLOCKTIME etc. are verified
            hash_key_pairs = []
            for ((coin, puzzle, solution), conditions_dict) in zip(
                    coin_puzzle_solution_tuples, conditions_dicts):
                check_conditions_dict(coin, conditions_dict, self)
                hash_key_pairs.extend(hash_key_pairs_for_conditions_dict(conditions_dict))

            # verify aggregated signature
            if not body.aggregated_signature.validate(hash_key_pairs):
                raise ConsensusError.BAD_AGGREGATE_SIGNATURE

            # update additions and removals in the UnspentDB
            return tuple(additions.keys()), tuple(removals.keys())

        except ConsensusError:
            raise
        except Exception as ex:
            print(ex)
            breakpoint()
            raise ConsensusError.UNKNOWN


class Mempool:
    """
    A mempool contains a list of consistent removals and solutions.
    """
    def __init__(self, tip: HeaderHash, storage: Storage):
        self.reset_tip(tip)
        self._storage = storage
        self._next_block_index = 1

    def reset_tip(self, tip: HeaderHash):
        self._bundles = set()
        self._tip = tip

    def collect_best_bundle(self) -> SpendBundle:
        # this is way too simple
        spend_bundle = SpendBundle.aggregate(self._bundles)
        assert spend_bundle.fees() >= 0
        return spend_bundle

    def minimum_legal_timestamp(self):
        return 0

    def generate_timestamp(self):
        return max(self.minimum_legal_timestamp(), int(time.time()))

    def accept_spend_bundle(self, spend_bundle):
        self._bundles.add(spend_bundle)

    async def validate_spend_bundle(self, spend_bundle):
        # validate that this bundle is correct and consistent
        # with the current mempool state
        if not spend_bundle.validate_signature():
            raise ValueError("bad signature")
        for coin_solution in spend_bundle.coin_solutions:
            coin = coin_solution.coin
            coin_name = coin.coin_name()
            unspent = await self._storage.unspent_for_coin_name(coin_name)
            if unspent is None:
                raise ValueError("unknown spendable %s" % coin_name)
            if unspent.confirmed_block_index >= self._next_block_index:
                raise ValueError("spendable %s not confirmed at index %d" % (
                    coin_name, self._next_block_index - 1))
            if unspent.spent_block_index != 0:
                raise ValueError("spendable %s already spent" % coin_name)

    def next_block_index(self):
        return self._next_block_index

    async def accept_new_block(self, block_index, body):
        additions = additions_for_body(body, self._storage)
        removals = removals_for_body(body)

        if removals and max(collections.Counter(removals).values()) > 1:
            raise ValueError("double spend")

        await self._storage.add_preimage(body.coinbase_coin.coin_name_data().as_bin())
        await self._storage.add_preimage(body.fees_coin.coin_name_data().as_bin())

        async for coin in additions:
            coin_name = coin.coin_name()
            unspent = Unspent(coin.amount, block_index, 0)
            await self._storage.set_unspent_for_coin_name(coin_name, unspent)
            await self._storage.add_preimage(coin.coin_name_data().as_bin())

        for coin_name in removals:
            unspent = await self._storage.unspent_for_coin_name(coin_name)
            unspent = Unspent(unspent.amount, unspent.confirmed_block_index, block_index)
            await self._storage.set_unspent_for_coin_name(coin_name, unspent)

        self._next_block_index = block_index + 1
