from chiasim.hashable import Program, ProgramHash
from binascii import hexlify
from clvm_tools import binutils
from chiasim.puzzles.puzzle_utilities import pubkey_format
from chiasim.validation.Conditions import ConditionOpcode


# this is for wallet A to generate the permitted puzzlehashes and sign them ahead of time
# returns a tuple of (puzhash, signature)
# not sure about how best to communicate/store who/what the puzzlehashes are, or if this is even important
def ap_generate_signatures(puzhashes, oldpuzzlehash, a_wallet, a_pubkey_used):
    puzhash_signature_list = []
    for p in puzhashes:
        signature = a_wallet.sign(p, a_pubkey_used)
        puzhash_signature_list.append((p, signature))
    return puzhash_signature_list


# we use it to merge the outputs of two programs that create lists
def merge_two_lists(list1=None, list2=None):
    if (list1 is None) or (list2 is None):
        return None
    ret = "(e (q (e (f (a)) (a))) (c (q (e (i (e (i (f (r (a))) (q (q ())) (q (q 1))) (a)) (q (f (c (f (r (r (a)))) (q ())))) (q (e (f (a)) (c (f (a)) (c (r (f (r (a)))) (c (c (f (f (r (a)))) (f (r (r (a))))) (q ()))))))) (a))) (c " + list1 + " (c " + list2 + " (q ())))))"
    return ret


# this creates our authorised payee puzzle
def ap_make_puzzle(a_pubkey_serialized, b_pubkey_serialized):
    a_pubkey = pubkey_format(a_pubkey_serialized)
    b_pubkey = pubkey_format(b_pubkey_serialized)

    # Mode one is for spending to one of the approved destinations
    # Solution contains (option 1 flag, list of (output puzzle hash (C/D), amount), my_primary_input, wallet_puzzle_hash)
    sum_outputs = "(e (q (e (f (a)) (a))) (c (q (e (i (e (i (f (r (a))) (q (q ())) (q (q 1))) (a)) (q (q 0)) (q (+ (f (r (f (f (r (a)))))) (e (f (a)) (c (f (a)) (c (r (f (r (a)))) (q ()))))))) (a))) (c (f (r (a))) (q ()))))"
    mode_one_me_string = "(c (q 0x%s) (c (sha256 (f (r (r (a)))) (f (r (r (r (a))))) (uint64 %s)) (q ())))" % (
        hexlify(ConditionOpcode.ASSERT_MY_COIN_ID).decode('ascii'), sum_outputs)
    aggsig_outputs = "(e (q (e (f (a)) (a))) (c (q (e (i (e (i (f (r (a))) (q (q ())) (q (q 1))) (a)) (q (q ())) (q (c (c (q 0x%s) (c (q %s) (c (f (f (f (r (a))))) (q ())))) (e (f (a)) (c (f (a)) (c (r (f (r (a)))) (q ()))))))) (a))) (c (f (r (a))) (q ()))))" % (
        hexlify(ConditionOpcode.AGG_SIG).decode('ascii'), a_pubkey)
    aggsig_entire_solution = "(c (q 0x%s) (c (q %s) (c (sha256 (wrap (a))) (q ()))))" % (
        hexlify(ConditionOpcode.AGG_SIG).decode('ascii'), b_pubkey)
    create_outputs = "(e (q (e (f (a)) (a))) (c (q (e (i (e (i (f (r (a))) (q (q ())) (q (q 1))) (a)) (q (q ())) (q (c (c (q 0x%s) (c (f (f (f (r (a))))) (c (f (r (f (f (r (a)))))) (q ())))) (e (f (a)) (c (f (a)) (c (r (f (r (a)))) (q ()))))))) (a))) (c (f (r (a))) (q ()))))" % (
        hexlify(ConditionOpcode.CREATE_COIN).decode('ascii'))
    mode_one = "(c " + aggsig_entire_solution + \
        " (c " + mode_one_me_string + " " + aggsig_outputs + "))"
    mode_one = merge_two_lists(create_outputs, mode_one)

    # Mode two is for aggregating in another coin and expanding our single coin wallet
    # Solution contains (option 2 flag, wallet_puzzle_hash, consolidating_coin_primary_input, consolidating_coin_puzzle_hash, consolidating_coin_amount, my_primary_input, my_amount)
    create_consolidated = '(c (q 0x%s) (c (f (r (a))) (c (+ (f (r (r (r (r (a)))))) (f (r (r (r (r (r (r (a))))))))) (q ()))))' % hexlify(
        ConditionOpcode.CREATE_COIN).decode('ascii')
    mode_two_me_string = "(c (q 0x%s) (c (sha256 (f (r (r (r (r (r (a))))))) (f (r (a))) (uint64 (f (r (r (r (r (r (r (a)))))))))) (q ())))" % (
        hexlify(ConditionOpcode.ASSERT_MY_COIN_ID).decode('ascii'))
    create_lock = "(c (q 0x%s) (c (sha256 (wrap (c (q 7) (c (c (q 5) (c (c (q 1) (c (sha256 (f (r (r (a)))) (f (r (r (r (a))))) (uint64 (f (r (r (r (r (a)))))))) (q ()))) (c (q (q ())) (q ())))) (q ()))))) (c (uint64 (q 0)) (q ()))))" % hexlify(
        ConditionOpcode.CREATE_COIN).decode('ascii')
    mode_two = '(c ' + mode_two_me_string + ' (c ' + aggsig_entire_solution + \
        ' (c ' + create_lock + ' (c ' + create_consolidated + ' (q ())))))'

    puz = "(e (i (= (f (a)) (q 1)) (q " + mode_one + ") (q " + mode_two + ")) (a))"
    # temporary - will eventually be puz
    return Program(binutils.assemble(puz))


def ap_make_aggregation_puzzle(wallet_puzzle):
    # If Wallet A wants to send further funds to Wallet B then they can lock them up using this code
    # Solution will be (my_id wallet_coin_primary_input wallet_coin_amount)
    me_is_my_id = '(c (q 0x%s) (c (f (a)) (q ())))' % (
        hexlify(ConditionOpcode.ASSERT_MY_COIN_ID).decode('ascii'))
    # lock_puzzle is the hash of '(r (c (q "merge in ID") (q ())))'
    lock_puzzle = '(sha256 (wrap (c (q 7) (c (c (q 5) (c (c (q 1) (c (f (a)) (q ()))) (c (q (q ())) (q ())))) (q ())))))'
    parent_coin_id = "(sha256 (f (r (a))) (q 0x%s) (uint64 (f (r (r (a))))))" % hexlify(
        wallet_puzzle).decode('ascii')
    input_of_lock = '(c (q 0x%s) (c (sha256 %s %s (uint64 (q 0))) (q ())))' % (hexlify(
        ConditionOpcode.ASSERT_COIN_CONSUMED).decode('ascii'), parent_coin_id, lock_puzzle)
    puz = '(c ' + me_is_my_id + ' (c ' + input_of_lock + ' (q ())))'
    return Program(binutils.assemble(puz))


# returns the ProgramHash of a new puzzle
def ap_get_new_puzzlehash(a_pubkey_serialized, b_pubkey_serialized):
    return ProgramHash(ap_make_puzzle(a_pubkey_serialized, b_pubkey_serialized))


def ap_get_aggregation_puzzlehash(wallet_puzzle):
    return ProgramHash(ap_make_aggregation_puzzle(wallet_puzzle))


# this allows wallet A to approve of new puzzlehashes/spends from wallet B that weren't in the original list
def ap_sign_output_newpuzzlehash(newpuzzlehash, a_wallet, a_pubkey_used):
    signature = a_wallet.sign(newpuzzlehash, a_pubkey_used)
    return signature
