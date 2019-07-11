from clvm import to_sexp_f

from opacity import binutils

from chiasim.atoms import hexbytes, uint64
from chiasim.hashable import (
    BLSSignature, Body, Coin, Header, HeaderHash,
    Program, ProgramHash, ProofOfSpace, SpendBundle
)


def best_solution_program(bundle: SpendBundle):
    """
    This could potentially do a lot of clever and complicated compression
    optimizations in conjunction with choosing the set of SpendBundles to include.

    For now, we just quote the solutions we know.
    """
    r = []
    for coin_solution in bundle.coin_solutions:
        entry = [coin_solution.coin.coin_name(), coin_solution.solution.code]
        r.append(entry)
    return Program(to_sexp_f([binutils.assemble("#q"), r]))


def collect_best_bundle(known_bundles) -> SpendBundle:
    # this is way too simple
    spend_bundle = SpendBundle.aggregate(known_bundles)
    assert spend_bundle.fees() >= 0
    return spend_bundle


def farm_new_block(
        previous_header: HeaderHash, block_index: int,
        proof_of_space: ProofOfSpace, spend_bundle: SpendBundle,
        coinbase_coin: Coin, coinbase_signature: BLSSignature,
        fees_puzzle_hash: ProgramHash, timestamp: uint64):
    """
    Steps:
        - collect up a consistent set of removals and solutions
        - run solutions to get the additions
        - select a timestamp = max(now, minimum_legal_timestamp)
        - create blank extension data
        - collect up coinbase coin with coinbase signature (if solo mining, we get these locally)
        - return Header, HeaderSignature, Body, Additions and Removals
    """

    program_cost = 0

    assert spend_bundle.validate_signature()
    solution_program = best_solution_program(spend_bundle)
    extension_data = hexbytes(b'')

    block_index_hash = block_index.to_bytes(32, "big")
    fees_coin = Coin(block_index_hash, fees_puzzle_hash, spend_bundle.fees())
    body = Body(
        coinbase_signature, coinbase_coin, fees_coin,
        solution_program, program_cost, spend_bundle.aggregated_signature)

    header = Header(previous_header, timestamp, proof_of_space, body, extension_data)
    return header, body

    # still need to do the following:
    # private_key = private_for_public(proof_of_space.plot_pubkey)
    # header_signature = private_key.sign(std_hash(header.as_bin()))
