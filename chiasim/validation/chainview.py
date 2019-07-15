import asyncio
import collections
import dataclasses

import clvm

from .consensus import (
    coin_for_coin_name, conditions_dict_for_solution,
    created_outputs_for_conditions_dict, hash_key_pairs_for_conditions_dict,
)
from chiasim.hashable import (
    BLSSignature, CoinName, HeaderHash, Program, ProgramHash
)
from chiasim.storage import OverlayStorage, OverlayUnspentDB, RAMUnspentDB, RAM_DB, Storage, UnspentDB

from .ConsensusError import ConsensusError, Err


def check_conditions_dict(coin, conditions_dict, chain_view):
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
    tip_index: int
    unspent_db: UnspentDB

    @classmethod
    def for_genesis_hash(cls, genesis_hash: HeaderHash, unspent_db: UnspentDB):
        return cls(genesis_hash, genesis_hash, 0, unspent_db)

    async def accept_new_block(
            self, header: HeaderHash, header_signature: BLSSignature, storage: Storage):
        """
        Checks the block against the existing ChainView object.
        Returns a list of additions (coins), and removals (coin names).

        Missing blobs must be resolvable by storage.

        If the given block is invalid, a ConsensusError is raised.
        """

        try:
            # verify header extends current view

            if header.previous_hash != self.tip_hash:
                raise ConsensusError(Err.DOES_NOT_EXTEND, header)

            # get proof of space

            pos = await header.proof_of_space_hash.obj(storage)
            if pos is None:
                raise ConsensusError(Err.MISSING_FROM_STORAGE, header.proof_of_space_hash)

            # verify header signature

            hkp = header_signature.aggsig_pair(pos.plot_public_key, header.hash())
            if not header_signature.validate([hkp]):
                raise ConsensusError(Err.BAD_HEADER_SIGNATURE, header_signature)

            # get body

            body = await header.body_hash.obj(storage)
            if body is None:
                raise ConsensusError(Err.MISSING_FROM_STORAGE, header.body_hash)

            # verify coinbase signature

            hkp = body.coinbase_signature.aggsig_pair(pos.pool_public_key, body.coinbase_coin.hash())
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

            addition_counter = collections.Counter(additions)
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
                await ram_storage.add_preimage(_.coin_name_data().as_bin())

            ram_db = RAMUnspentDB(additions, self.tip_index + 1)
            overlay_storage = OverlayStorage(ram_storage, storage)
            unspent_db = OverlayUnspentDB(self.unspent_db, ram_db)

            coin_futures = [asyncio.ensure_future(
                coin_for_coin_name(_[0], overlay_storage, unspent_db)) for _ in npc_list]

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
                coin_name = coin.coin_name()
                unspent = await unspent_db.unspent_for_coin_name(coin_name)
                if (unspent is None or
                        unspent.confirmed_block_index == 0 or
                        unspent.confirmed_block_index >= self.tip_index):
                    raise ConsensusError(Err.UNKNOWN_UNSPENT, coin_name)
                if (0 < unspent.spent_block_index <= self.tip_index):
                    raise ConsensusError(Err.DOUBLE_SPEND, coin_name)

            # check solution for each CoinSolution pair
            # this is where CHECKLOCKTIME etc. are verified
            hash_key_pairs = []
            for coin, puzzle_hash, conditions_dict in cpc_list:
                check_conditions_dict(coin, conditions_dict, self)
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
