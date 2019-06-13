import binascii
import dataclasses

import blspy
import clvm

from opacity import binutils

from chiasim.atoms import bytes32
from chiasim.coin.Conditions import conditions_to_sexp, make_create_coin_condition
from chiasim.hashable import Coin, CoinSolution, Program, SpendBundle, std_hash
from chiasim.hashable.BLSSignature import BLSSignature, BLSPublicKey


@dataclasses.dataclass
class BLSPrivateKey:

    pk: blspy.PrivateKey

    def sign(self, message_hash: bytes32) -> BLSSignature:
        return BLSSignature(self.pk.sign_prepend_prehashed(message_hash).serialize())

    def public_key(self) -> BLSPublicKey:
        return BLSPublicKey(self.pk.get_public_key())


def prv_key_for_seed(seed):
    eprv = blspy.ExtendedPrivateKey.from_seed(seed)
    return eprv.get_private_key()


def pub_key_for_seed(seed):
    eprv = blspy.ExtendedPrivateKey.from_seed(seed)
    return eprv.get_public_key()


def make_simple_puzzle_program(pub_key):
    # want to return ((aggsig pub_key SOLN) + SOLN)
    # (cons (list aggsig PUBKEY (sha256 x0)) (call (unwrap (f (a))) (r (a))))
    aggsig = 50
    STD_SCRIPT = f"(c (c (q {aggsig}) (c (q 0x%s) (c (sha256 (wrap (f (a)))) (q ())))) (e (f (a)) (r (a))))"
    puzzle_script = binutils.assemble(STD_SCRIPT % binascii.hexlify(pub_key.serialize()).decode("utf8"))
    return clvm.to_sexp_f(puzzle_script)


def trace_eval(eval_f, args, env):
    print("%s [%s]" % (binutils.disassemble(args), binutils.disassemble(env)))
    r = clvm.eval_f(eval_f, args, env)
    print("%s [%s] => %s\n" % (
        binutils.disassemble(args), binutils.disassemble(env), binutils.disassemble(r)))
    return r


def make_solution_to_simple_puzzle_program(puzzle_program, conditions):
    conditions_program = conditions_to_sexp(conditions)
    solution_program_solved = conditions_program.cons(clvm.to_sexp_f([[]]))
    puzzle_hash_solution = clvm.to_sexp_f([puzzle_program, solution_program_solved])
    return puzzle_hash_solution


def build_conditions():
    pub_key_0 = pub_key_for_seed(b"foo")
    pub_key_1 = pub_key_for_seed(b"bar")

    puzzle_program_0 = make_simple_puzzle_program(pub_key_0)
    puzzle_program_1 = make_simple_puzzle_program(pub_key_1)

    conditions = [make_create_coin_condition(std_hash(pp.as_bin()), amount) for pp, amount in [
        (puzzle_program_0, 1000), (puzzle_program_1, 2000),
    ]]
    return conditions


def prv_key_for_pub_key(pub_key, d):
    return d.get(pub_key)


def build_spend_bundle():
    prvkey = prv_key_for_seed(b"foo")
    pubkey = prvkey.get_public_key()

    lookup = {pubkey.serialize(): prvkey}

    puzzle = Program(make_simple_puzzle_program(pubkey))
    parent = bytes(([0] * 31) + [1])
    coin = Coin(parent, puzzle, 50000)
    conditions = build_conditions()
    solution = Program(make_solution_to_simple_puzzle_program(puzzle.code, conditions))
    coin_solution = CoinSolution(coin, solution)

    signatures = []
    for _ in coin_solution.hash_key_pairs():
        print(_)
        prvkey = prv_key_for_pub_key(_.public_key, lookup)
        signature = BLSPrivateKey(prvkey).sign(_.message_hash)
        signatures.append(signature)

    signature = signatures[0].aggregate(signatures)
    spend_bundle = SpendBundle([coin_solution], signature)
    return spend_bundle
