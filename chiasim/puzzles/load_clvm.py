import pkg_resources

from clvm_tools import binutils
import stage_2

from chiasim.hashable import Program


def load_clvm(filename):
    eval_f = stage_2.EVAL_F
    clvm_text = pkg_resources.resource_string(__name__, filename).decode("utf8")
    clvm_source = binutils.assemble(clvm_text)
    clvm_compiled = eval_f(eval_f, stage_2.run, Program.to([clvm_source]))
    return Program.to(clvm_compiled)
