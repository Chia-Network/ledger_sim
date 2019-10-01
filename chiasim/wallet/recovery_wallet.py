from chiasim.wallet.wallet import Wallet
from chiasim.validation.Conditions import ConditionOpcode, make_create_coin_condition
from chiasim.atoms import hexbytes
from chiasim.hashable import Program, ProgramHash
from clvm_tools import binutils
from clvm import to_sexp_f


class RecoveryWallet(Wallet):
    def __init__(self):
        super().__init__()
        self.backup_public_key = self.extended_secret_key.public_child(self.next_address).get_public_key()
        self.backup_private_key = self.extended_secret_key.private_child(self.next_address).get_private_key()
        self.next_address += 1

    def get_new_puzzle(self):
        aggsig = ConditionOpcode.AGG_SIG[0]
        mintime = ConditionOpcode.ASSERT_MIN_TIME[0]
        TEMPLATE = (f"(c (c (q {aggsig}) (c (q 0x%s) (c (sha256 (wrap (f (a)))) (q ())))) "
                    f"(e (f (a)) (f (r (a)))))")
        secure_key_puzzle = TEMPLATE % hexbytes(self.backup_public_key.serialize())
        CLAWBACK_TEMPLATE = (f"(c (c (q {aggsig}) (c (q 0x%s) (c (sha256 (wrap (f (a)))) (q ())))) "
                             f"(c (q {mintime}) (c (q 0x%s) (q ())))"
                             f"(e (f (a)) (f (r (a)))))")
        duration = 555
        clawback_puzzle = CLAWBACK_TEMPLATE % (hexbytes(self.backup_public_key.serialize()), hexbytes(duration))
        escrow_puzzle = "(i (= (f (r (f (r (r (a)))))) (q 0)) " + secure_key_puzzle + clawback_puzzle + ")"
        escrow_puzzlehash = ProgramHash(Program(binutils.assemble(escrow_puzzle)))
        increased_amount = 125
        conditions = [make_create_coin_condition(escrow_puzzlehash, increased_amount)]
        sexp = to_sexp_f([binutils.assemble("#q"), conditions])
        recovery_puzzle = binutils.disassemble(sexp)
        puzzle = "(i (= (f (r (f (r (r (a)))))) (q 0)) " + secure_key_puzzle + recovery_puzzle + ")"

        return puzzle
