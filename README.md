# Sweet / Anne

Anne is a small dataset language. Sweet compiles it (parse -> AST -> semantic analysis -> logical IR ->
optimizer -> Polars lazy backend).

    sweet program.anne -o outdir     # run; explicit save() exports land in outdir/
    sweet program.anne --check       # compile only (parse + type-check), no execution
    sweet                            # REPL (same compiler and executor)

Datasets are immutable and lazy. `data x = read "f.csv";` never executes anything; `show`, `describe`,
`shape`, `save` do. Dataset methods: filter select derive sort limit head tail drop_missing group_by
(+ summarize) join collect. Actions: show schema describe columns shape explain save.

Optimizations implemented by Sweet: constant folding, adjacent-filter fusion. Projection and predicate
pushdown are NOT implemented by Sweet; Polars' own lazy optimizer does them.

Join notes: key columns must exist on both sides with the same type; null keys never match; clashing
non-key columns from the right side get a `_right` suffix; full joins coalesce the key columns.
Only null is treated as missing by drop_missing (not NaN).
