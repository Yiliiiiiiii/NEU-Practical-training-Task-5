from __future__ import annotations

from typing import Any


class GlobalAssignmentSolver:
    """Deterministic maximum-weight one-to-one assignment with abstention nodes."""

    MISSING_EDGE_COST = 1_000_000.0
    REQUIRED_FIELD_TIE_PRIORITY = 0.000001

    @classmethod
    def _weight(cls, row: dict[str, Any]) -> float:
        return float(row["features"].final_score) + (
            cls.REQUIRED_FIELD_TIE_PRIORITY if row["target"].required else 0.0
        )

    def solve(self, pair_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        eligible = [row for row in pair_rows if row["features"].negative_score < 1.0]
        target_ids = sorted({row["target"].field_id for row in eligible})
        source_paths = sorted({row["candidate"].source_path for row in eligible})
        reusable_columns = sorted(
            {
                f"reuse:{row['target'].field_id}:{row['candidate'].source_path}"
                for row in eligible
                if row.get("allow_source_reuse") is True
            }
        )
        if not target_ids:
            return []

        best_edges: dict[tuple[str, str], dict[str, Any]] = {}
        for row in sorted(
            eligible,
            key=lambda item: (
                item["target"].field_id,
                item["candidate"].source_path,
                -item["features"].final_score,
                item["candidate"].candidate_id,
            ),
        ):
            key = (row["target"].field_id, row["candidate"].source_path)
            best_edges.setdefault(key, row)

        columns = [
            *(f"source:{path}" for path in source_paths),
            *reusable_columns,
            *(f"dummy:{target_id}" for target_id in target_ids),
        ]
        max_weight = max((self._weight(row) for row in eligible), default=0.0)
        costs: list[list[float]] = []
        for target_id in target_ids:
            row_costs: list[float] = []
            for column in columns:
                if column == f"dummy:{target_id}":
                    row_costs.append(max_weight)
                    continue
                if column.startswith("dummy:"):
                    row_costs.append(self.MISSING_EDGE_COST)
                    continue
                if column.startswith("reuse:"):
                    _, reusable_target, source_path = column.split(":", 2)
                    edge = best_edges.get((target_id, source_path))
                    row_costs.append(
                        max_weight - self._weight(edge)
                        if reusable_target == target_id
                        and edge is not None
                        and edge.get("allow_source_reuse") is True
                        else self.MISSING_EDGE_COST
                    )
                    continue
                source_path = column.removeprefix("source:")
                edge = best_edges.get((target_id, source_path))
                row_costs.append(
                    max_weight - self._weight(edge)
                    if edge is not None
                    else self.MISSING_EDGE_COST
                )
            costs.append(row_costs)

        assignment = self._hungarian(costs)
        selected: list[dict[str, Any]] = []
        for row_index, column_index in enumerate(assignment):
            if column_index < 0:
                continue
            column = columns[column_index]
            if column.startswith("reuse:"):
                _, _, source_path = column.split(":", 2)
            elif column.startswith("source:"):
                source_path = column.removeprefix("source:")
            else:
                continue
            edge = best_edges.get((target_ids[row_index], source_path))
            if edge is not None:
                selected.append(edge)
        return sorted(selected, key=lambda row: row["target"].field_id)

    @staticmethod
    def _hungarian(costs: list[list[float]]) -> list[int]:
        """Return the minimum-cost column for each row; rows must not exceed columns."""
        row_count = len(costs)
        column_count = len(costs[0]) if costs else 0
        if row_count > column_count:
            raise ValueError("assignment matrix must have at least as many columns as rows")
        u = [0.0] * (row_count + 1)
        v = [0.0] * (column_count + 1)
        matched_row = [0] * (column_count + 1)
        predecessor = [0] * (column_count + 1)

        for row in range(1, row_count + 1):
            matched_row[0] = row
            column0 = 0
            minimum = [float("inf")] * (column_count + 1)
            used = [False] * (column_count + 1)
            while True:
                used[column0] = True
                current_row = matched_row[column0]
                delta = float("inf")
                next_column = 0
                for column in range(1, column_count + 1):
                    if used[column]:
                        continue
                    reduced = costs[current_row - 1][column - 1] - u[current_row] - v[column]
                    if reduced < minimum[column]:
                        minimum[column] = reduced
                        predecessor[column] = column0
                    if minimum[column] < delta:
                        delta = minimum[column]
                        next_column = column
                for column in range(column_count + 1):
                    if used[column]:
                        u[matched_row[column]] += delta
                        v[column] -= delta
                    else:
                        minimum[column] -= delta
                column0 = next_column
                if matched_row[column0] == 0:
                    break
            while True:
                previous = predecessor[column0]
                matched_row[column0] = matched_row[previous]
                column0 = previous
                if column0 == 0:
                    break

        result = [-1] * row_count
        for column in range(1, column_count + 1):
            if matched_row[column] != 0:
                result[matched_row[column] - 1] = column - 1
        return result
