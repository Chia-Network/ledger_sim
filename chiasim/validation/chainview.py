import asyncio
import collections
import dataclasses

import clvm

from .consensus import (
    conditions_dict_for_solution,
    created_outputs_for_conditions_dict, hash_key_pairs_for_conditions_dict,
)
from chiasim.hashable import (
    Coin, CoinName, Header, HeaderHash,
    Program, ProgramHash, Signature, Unspent
)
from chiasim.storage import OverlayStorage, OverlayUnspentDB, RAMUnspentDB, RAM_DB, Storage, UnspentDB

from .ConsensusError import ConsensusError, Err


def check_conditions_dict(coin, conditions_dict, context):
    """
    Check all conditions against current state.
    """
    pass


def name_puzzle_conditions_list(body_program):
    """
    Return a list of tuples of (coin_name, solved_puzzle_hash, conditions_dict)
    """

    try:
        sexp = clvm.eval_f(clvm.eval_f, body_program.code, [])
    except clvm.EvalError.EvalError:
        breakpoint()
        raise ConsensusError(Err.INVALID_BLOCK_SOLUTION, body_program)

    npc_list = []
    for name_solution in sexp.as_iter():
        _ = name_solution.as_python()
        if len(_) != 2:
            raise ConsensusError(Err.INVALID_COIN_SOLUTION, name_solution)
        if not isinstance(_[0], bytes) or len(_[0]) != 32:
            raise ConsensusError(Err.INVALID_COIN_SOLUTION, name_solution)
        coin_name = CoinName(_[0])
        if not isinstance(_[1], list) or len(_[1]) != 2:
            raise ConsensusError(Err.INVALID_COIN_SOLUTION, name_solution)
        puzzle_solution_program = name_solution.rest().first()
        puzzle_program = puzzle_solution_program.first()
        puzzle_hash = ProgramHash(Program(puzzle_program))
        try:
            conditions_dict = conditions_dict_for_solution(puzzle_solution_program.rest().first())
        except clvm.EvalError.EvalError:
            raise ConsensusError(Err.INVALID_COIN_SOLUTION, coin_name)

        npc_list.append((coin_name, puzzle_hash, conditions_dict))

    return npc_list


@dataclasses.dataclass
class ChainView:
    genesis_hash: HeaderHash
    tip_hash: HeaderHash
    tip_signature: Signature
    tip_index: int
    unspent_db: UnspentDB

    @classmethod
    def for_genesis_hash(cls, genesis_hash: HeaderHash, unspent_db: UnspentDB):
        return cls(genesis_hash, genesis_hash, Signature.zero(), 0, unspent_db)

    async def check_tip_signature(self, storage):
        if self.tip_hash == self.genesis_hash:
            if self.tip_signature != Signature.zero():
                raise ConsensusError(Err.BAD_GENESIS_SIGNATURE, self.tip_signature)
        else:
            await check_header_signature(self.tip_hash, self.tip_signature, storage)

    async def augment_chain_view(
            self, header, header_signature, storage, new_unspent_db, reward) -> "ChainView":
        tip_index = self.tip_index + 1
        additions, removals = await self.accept_new_block(
            header, header_signature, storage, reward)
        await apply_deltas(
            tip_index, additions, removals, storage, new_unspent_db)
        return self.__class__(
            self.genesis_hash, HeaderHash(header), header_signature,
            tip_index, new_unspent_db)

    async def accept_new_block(
            self, header: Header, header_signature: Signature,
            storage: Storage, coinbase_reward: int):
        return await accept_new_block(
            self, header, header_signature, storage, coinbase_reward)


async def coin_for_coin_name(coin_name, storage):
    coin_blob = await storage.hash_preimage(coin_name)
    if coin_blob:
        return Coin.from_bin(coin_blob)


async def check_header_signature(
        header_hash: HeaderHash, header_signature: Signature, storage: Storage):

    # fetch header for header_hash

    header = await header_hash.obj(storage)
    if header is None:
        raise ConsensusError(Err.MISSING_FROM_STORAGE, header_hash)

    # get proof of space

    pos = await header.proof_of_space_hash.obj(storage)
    if pos is None:
        raise ConsensusError(Err.MISSING_FROM_STORAGE, header.proof_of_space_hash)

    # verify header signature

    hkp = header_signature.aggsig_pair(pos.plot_public_key, header.hash())
    if not header_signature.validate([hkp]):
        raise ConsensusError(Err.BAD_HEADER_SIGNATURE, header_signature)

    return pos


async def accept_new_block(
        chain_view: ChainView, header: Header, header_signature: Signature,
        storage: Storage, coinbase_reward: int):
    """
    Checks the block against the existing ChainView object.
    Returns a list of additions (coins), and removals (coin names).

    Missing blobs must be resolvable by storage.

    If the given block is invalid, a ConsensusError is raised.
    """

    try:
        # verify header extends current view

        if header.previous_hash != chain_view.tip_hash:
            raise ConsensusError(Err.DOES_NOT_EXTEND, header)

        # verify header signature

        pos = await check_header_signature(
            HeaderHash(header), header_signature, storage)

        # get body

        body = await header.body_hash.obj(storage)
        if body is None:
            raise ConsensusError(Err.MISSING_FROM_STORAGE, header.body_hash)

        # verify coinbase signature

        hkp = body.coinbase_signature.aggsig_pair(pos.pool_public_key, body.coinbase_coin.name())
        if not body.coinbase_signature.validate([hkp]):
            raise ConsensusError(Err.BAD_COINBASE_SIGNATURE, body)

        # ensure block program generates solutions

        npc_list = name_puzzle_conditions_list(body.solution_program)

        # build removals list
        removals = tuple(_[0] for _ in npc_list)

        # build additions

        def additions_iter(body, npc_list):
            yield body.coinbase_coin
            yield body.fees_coin
            for coin_name, puzzle_hash, conditions_dict in npc_list:
                for _ in created_outputs_for_conditions_dict(conditions_dict, coin_name):
                    yield _

        additions = tuple(additions_iter(body, npc_list))

        #  watch out for duplicate outputs

        addition_counter = collections.Counter(_.name() for _ in additions)
        for k, v in addition_counter.items():
            if v > 1:
                raise ConsensusError(Err.DUPLICATE_OUTPUT, k)

        #  watch out for double-spends

        removal_counter = collections.Counter(removals)
        for k, v in removal_counter.items():
            if v > 1:
                raise ConsensusError(Err.DOUBLE_SPEND, k)

        # create a temporary overlay DB with the additions

        ram_storage = RAM_DB()
        for _ in additions:
            await ram_storage.add_preimage(_.as_bin())

        ram_db = RAMUnspentDB(additions, chain_view.tip_index + 1)
        overlay_storage = OverlayStorage(ram_storage, storage)
        unspent_db = OverlayUnspentDB(chain_view.unspent_db, ram_db)

        coin_futures = [asyncio.ensure_future(
            coin_for_coin_name(_[0], overlay_storage)) for _ in npc_list]

        # build cpc_list from npc_list
        cpc_list = []
        for coin_future, (coin_name, puzzle_hash, conditions_dict) in zip(coin_futures, npc_list):
            coin = await coin_future
            if coin is None:
                raise ConsensusError(Err.UNKNOWN_UNSPENT, coin_name)
            cpc_list.append((coin, puzzle_hash, conditions_dict))

        # check that the revealed removal puzzles actually match the puzzle hash

        for coin, puzzle_hash, conditions_dict in cpc_list:
            if puzzle_hash != coin.puzzle_hash:
                raise ConsensusError(Err.WRONG_PUZZLE_HASH, coin)

        # check removals against UnspentDB

        for coin, puzzle_hash, conditions_dict in cpc_list:
            if coin in additions:
                # it's an ephemeral coin, created and destroyed in the same block
                continue
            coin_name = coin.name()
            unspent = await unspent_db.unspent_for_coin_name(coin_name)
            if (unspent is None or
                    unspent.confirmed_block_index == 0 or
                    unspent.confirmed_block_index > chain_view.tip_index):
                raise ConsensusError(Err.UNKNOWN_UNSPENT, coin_name)
            if (0 < unspent.spent_block_index <= chain_view.tip_index):
                raise ConsensusError(Err.DOUBLE_SPEND, coin_name)

        # check fees

        fees = 0
        for coin, puzzle_hash, conditions_dict in cpc_list:
            fees -= coin.amount

        for coin in additions:
            fees += coin.amount

        if fees != coinbase_reward:
            raise ConsensusError(Err.BAD_COINBASE_REWARD, body.coinbase_coin)

        # check solution for each CoinSolution pair
        # this is where CHECKLOCKTIME etc. are verified

        context = {}
        hash_key_pairs = []
        for coin, puzzle_hash, conditions_dict in cpc_list:
            check_conditions_dict(coin, conditions_dict, context)
            hash_key_pairs.extend(hash_key_pairs_for_conditions_dict(conditions_dict))

        # verify aggregated signature

        if not body.aggregated_signature.validate(hash_key_pairs):
            raise ConsensusError(Err.BAD_AGGREGATE_SIGNATURE, body)

        return additions, removals

    except ConsensusError:
        raise
    except Exception as ex:
        breakpoint()
        raise ConsensusError(Err.UNKNOWN, ex)


async def apply_deltas(block_index, additions, removals, unspent_db, storage):
    for coin in additions:
        new_unspent = Unspent(block_index, 0)
        await unspent_db.set_unspent_for_coin_name(coin.name(), new_unspent)
        await storage.add_preimage(coin.as_bin())

    for coin_name in removals:
        unspent = await unspent_db.unspent_for_coin_name(coin_name)
        new_unspent = Unspent(unspent.confirmed_block_index, block_index)
        await unspent_db.set_unspent_for_coin_name(coin_name, new_unspent)