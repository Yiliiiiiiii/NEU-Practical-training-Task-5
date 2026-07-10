# SchemaPack Contract Gate Report

- status: passed

## Checks

- manifest_contracts: passed
- asset_integrity: passed
- cross_file_consistency: passed
- positive_examples: passed
- badcase_detection: passed
- package_1_1_compatibility: passed
- phase2_mapping_gate: passed
- topic5_alignment_gate: passed

## Warnings

- {'type': 'schema_precision_below_recommended_threshold', 'split': 'dev', 'schema_id': 'meeting_doc', 'auto_precision': 0.8, 'threshold': 0.85}
- {'type': 'schema_precision_below_recommended_threshold', 'split': 'dev', 'schema_id': 'policy_doc', 'auto_precision': 0.8, 'threshold': 0.85}
- {'type': 'schema_precision_below_recommended_threshold', 'split': 'test', 'schema_id': 'meeting_doc', 'auto_precision': 0.8, 'threshold': 0.85}
- {'type': 'schema_precision_below_recommended_threshold', 'split': 'test', 'schema_id': 'policy_doc', 'auto_precision': 0.8, 'threshold': 0.85}
- {'type': 'schema_precision_below_recommended_threshold', 'split': 'blind', 'schema_id': 'meeting_doc', 'auto_precision': 0.8, 'threshold': 0.85}
- {'type': 'schema_precision_below_recommended_threshold', 'split': 'blind', 'schema_id': 'policy_doc', 'auto_precision': 0.8, 'threshold': 0.85}
