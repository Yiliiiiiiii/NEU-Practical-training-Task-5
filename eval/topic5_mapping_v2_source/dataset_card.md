# Topic 5 Mapping Benchmark v2

This is the versioned, independently authored source for the immutable public benchmark (version 2.0.0). Six distinct schema families each contain 15 reviewed document scenarios. Schemas, aliases, UIR documents, positive annotations, negative-pair decisions, no-match decisions, and splits are standalone files; the builder copies this contract byte-for-byte and never derives gold from engine predictions.

The scenarios cover Chinese and English labels, abbreviations and long labels, metadata/key-value/table/paragraph candidates, reordered fields, missing optional fields, multiple date roles, budget versus award, issuer versus organizer, contact versus attendee, and compatible-type distractors. Values use family-specific titles, organizations, people, decisions, places, policy numbers, and amounts rather than a numeric template. Candidate-bearing attributes intentionally contain no field names or target hints.

`grant_program` is absent from dev and is the schema-held-out test family. Source/organization holdout is derived from the actual UIR metadata and split files. Gold records are marked `independent_frozen_author_label`; external blind evidence remains `not_run` until separately annotated input is supplied.

Files under the built v2 dataset are immutable after the baseline freeze. Corrections require v3.
