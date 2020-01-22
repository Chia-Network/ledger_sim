import clvm

from chiasim.hashable import Program


def run_program_with_eval_cost(program, env, max_cost=None):
    program = clvm.to_sexp_f(program)
    env = clvm.to_sexp_f(env)
    cost, r = clvm.eval_cost(clvm.eval_cost, program, env, max_cost=max_cost)
    return Program(r)


def run_program_with_eval_f(program, env, max_cost=None):
    program = clvm.to_sexp_f(program)
    env = clvm.to_sexp_f(env)
    return 1, Program(clvm.eval_f(clvm.eval_f, program, env))


if hasattr(clvm, "eval_cost"):
    run_program = run_program_with_eval_cost
else:
    run_program = run_program_with_eval_f
