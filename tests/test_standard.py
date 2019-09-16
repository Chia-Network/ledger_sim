import asyncio
from unittest import TestCase

from chiasim.hack.keys import (
    build_spend_bundle, conditions_for_payment, public_key_bytes_for_index,
    puzzle_hash_for_index, private_key_for_index
)
from chiasim.hashable import Coin, ProgramHash, SpendBundle
from chiasim.puzzles import (
    p2_conditions, p2_delegated_conditions, p2_m_of_n_delegate_direct
)
from chiasim.remote.client import RemoteError
from chiasim.validation.Conditions import make_assert_my_coin_id_condition
from chiasim.wallet.BLSPrivateKey import BLSPrivateKey
from .test_puzzles import farm_spendable_coin, make_client_server


def run_test(puzzle_hash, payments, solution_maker, fuzz_signature=None):
    run = asyncio.get_event_loop().run_until_complete

    remote = make_client_server()

    coin = farm_spendable_coin(remote, puzzle_hash)
    solution = solution_maker(coin, remote)
    spend_bundle = build_spend_bundle(coin, solution)
    if fuzz_signature:
        spend_bundle = fuzz_signature(spend_bundle)

    # push it
    r = run(remote.push_tx(tx=spend_bundle))
    if isinstance(r, RemoteError):
        raise r
    assert r["response"].startswith("accepted")
    print(r)

    # confirm it
    farm_spendable_coin(remote)

    # get unspents
    r = run(remote.all_unspents())
    print("unspents = %s" % r.get("unspents"))
    unspents = r["unspents"]

    # ensure all outputs are there
    for puzzle_hash, amount in payments:
        expected_coin = Coin(coin.name(), puzzle_hash, amount)
        name = expected_coin.name()
        assert name in unspents
        unspent = run(remote.unspent_for_coin_name(coin_name=name))
        assert unspent.spent_block_index == 0


class TestStandard(TestCase):
    def test_pay_to_pubkey(self):
        self.do_pubkey()

    def test_pay_to_pubkey_wrong_coin(self):
        with self.assertRaises(RemoteError) as raised:
            self.do_pubkey(lambda remote, puzzle_hash:
                           farm_spendable_coin(remote, puzzle_hash))
            self.fail("expected RemoteError")
        self.assertTrue(raised.exception.args[0].startswith("exception: (<Err.ASSERT_MY_COIN_ID_FAILED"))

    @staticmethod
    def do_pubkey(fuzz_coin=None):
        payments = [
            (puzzle_hash_for_index(0), 1000),
            (puzzle_hash_for_index(1), 2000),
        ]
        conditions = conditions_for_payment(payments)
        pk = public_key_bytes_for_index(1)
        puzzle_program = p2_delegated_conditions.puzzle_for_pk(pk)
        puzzle_hash = ProgramHash(puzzle_program)

        def solution_maker(coin, remote):
            if fuzz_coin:
                coin = fuzz_coin(remote, puzzle_hash)
            id_condition = make_assert_my_coin_id_condition(coin.name())
            return p2_delegated_conditions.solution_for_conditions(puzzle_program,
                                                                   conditions + [id_condition])

        run_test(puzzle_hash, payments, solution_maker)

    def test_pay_to_multisig(self):
        selectors = [1, [], 1]
        self.do_multisig(selectors)

        selectors = [1, 1, []]
        self.do_multisig(selectors)

    def test_pay_to_multisig_wrong_coin(self):
        selectors = [1, [], 1]
        with self.assertRaises(RemoteError) as raised:
            self.do_multisig(selectors,
                             lambda remote, puzzle_hash:
                             farm_spendable_coin(remote, puzzle_hash))
            self.fail("expected RemoteError")
        self.assertTrue(raised.exception.args[0].startswith("exception: (<Err.ASSERT_MY_COIN_ID_FAILED"))

    def test_pay_to_multisig_wrong_signature(self):
        selectors = [1, [], 1]
        with self.assertRaises(RemoteError) as raised:
            def fuzz_signature(spend_bundle: SpendBundle):
                bls_private_key = BLSPrivateKey(private_key_for_index(0))
                signature = bls_private_key.sign(b'\x11' * 32)
                return SpendBundle(spend_bundle.coin_solutions, signature)

            self.do_multisig(selectors, fuzz_signature=fuzz_signature)
            self.fail("expected RemoteError")
        self.assertTrue(raised.exception.args[0].startswith("exception: bad signature"))

    @staticmethod
    def do_multisig(selectors, fuzz_coin=None, fuzz_signature=None):
        payments = [
            (puzzle_hash_for_index(0), 1000),
            (puzzle_hash_for_index(1), 2000),
        ]
        conditions = conditions_for_payment(payments)
        pks = [public_key_bytes_for_index(_) for _ in range(1, 4)]
        M = 2
        puzzle_program = p2_m_of_n_delegate_direct.puzzle_for_m_of_public_key_list(M, pks)
        puzzle_hash = ProgramHash(puzzle_program)

        def solution_maker(coin, remote):
            print(coin.name())
            if fuzz_coin:
                coin = fuzz_coin(remote, puzzle_hash)
                print(coin.name())
            id_condition = make_assert_my_coin_id_condition(coin.name())
            delegated_puzzle = p2_conditions.puzzle_for_conditions(conditions + [id_condition])
            delegated_solution = p2_delegated_conditions.solution_for_conditions(delegated_puzzle,
                                                                                 [])
            delegated_code = delegated_solution.code

            solution = p2_m_of_n_delegate_direct.solution_for_delegated_puzzle(
                M, pks, selectors, delegated_puzzle, delegated_code)
            return solution

        run_test(puzzle_hash, payments, solution_maker, fuzz_signature)
