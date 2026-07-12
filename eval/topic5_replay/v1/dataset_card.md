# Topic 5 Replay v1

The replay evaluator uses the public announcement conversion request to test
three deterministic contracts: exact replay on the same engine, explicit
Schema-version differences, and explicit engine-version differences. Replay is
read-only with respect to tasks and packages and does not implement scheduling.
