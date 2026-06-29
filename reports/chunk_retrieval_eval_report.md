# Chunk Retrieval Evaluation Report

- Status: completed
- Query count: 4

## Strategy metrics

| Strategy | Recall@1 | Recall@3 | Recall@5 | MRR | nDCG@5 | Source links | Table integrity | Avg tokens | Chunks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed_window | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 229.15 | 39 |
| heading_aware | 0.7500 | 1.0000 | 1.0000 | 0.8333 | 0.8549 | 1.0000 | 1.0000 | 193.93 | 46 |
| source_block_aware | 0.7500 | 0.7500 | 0.7500 | 0.7917 | 0.7299 | 1.0000 | 1.0000 | 41.15 | 213 |
| table_protect | 0.7500 | 1.0000 | 1.0000 | 0.8333 | 0.8549 | 1.0000 | 1.0000 | 200.77 | 44 |

## Failure analysis

- source_block_aware/rq_procurement_supplier_table: no relevant chunk in top 5
