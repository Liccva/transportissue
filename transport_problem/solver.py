from collections import deque

from .models import EPSILON, TransportTable

Cell = tuple[int, int]


def solve_transport_problem(table: TransportTable) -> None:
    costs = table.transport_coefficients
    m, n = len(table.suppliers), len(table.consumers)

    def build_initial_plan() -> tuple[list[list[float]], set[Cell]]:
        plan = [[0.0] * n for _ in range(m)]
        basis: set[Cell] = set()
        supply = [s.resources for s in table.suppliers]
        demand = [c.resources for c in table.consumers]
        active_rows, active_cols = set(range(m)), set(range(n))

        while active_rows and active_cols:
            i, j = min(
                ((r, c) for r in active_rows for c in active_cols),
                key=lambda cell: (costs[cell], cell),
            )
            volume = min(supply[i], demand[j])
            plan[i][j] = volume
            basis.add((i, j))
            supply[i] -= volume
            demand[j] -= volume

            row_exhausted = supply[i] <= demand[j]
            if (row_exhausted and len(active_rows) > 1) or len(active_cols) == 1:
                active_rows.discard(i)
                demand[j] = max(demand[j], 0.0)
            else:
                active_cols.discard(j)
                supply[i] = max(supply[i], 0.0)
        return plan, basis

    def compute_potentials(basis: set[Cell]) -> tuple[list[float], list[float]]:
        u: list[float | None] = [None] * m
        v: list[float | None] = [None] * n
        u[0] = 0.0
        rows_cells: dict[int, list[int]] = {i: [] for i in range(m)}
        cols_cells: dict[int, list[int]] = {j: [] for j in range(n)}
        for i, j in basis:
            rows_cells[i].append(j)
            cols_cells[j].append(i)

        queue = deque([("row", 0)])
        while queue:
            kind, index = queue.popleft()
            if kind == "row":
                for j in rows_cells[index]:
                    if v[j] is None:
                        v[j] = costs[index, j] - u[index]
                        queue.append(("col", j))
            else:
                for i in cols_cells[index]:
                    if u[i] is None:
                        u[i] = costs[i, index] - v[index]
                        queue.append(("row", i))

        if any(p is None for p in u) or any(p is None for p in v):
            raise RuntimeError("Базисные клетки не образуют связный план — потенциалы не определены")
        return u, v

    def find_entering_cell(
        basis: set[Cell], u: list[float], v: list[float], use_bland: bool
    ) -> Cell | None:
        best_cell, best_delta = None, -EPSILON
        for i in range(m):
            for j in range(n):
                if (i, j) in basis:
                    continue
                delta = costs[i, j] - (u[i] + v[j])
                if delta < best_delta:
                    if use_bland:
                        return i, j
                    best_cell, best_delta = (i, j), delta
        return best_cell

    def find_cycle(basis: set[Cell], start: Cell) -> list[Cell]:
        i0, j0 = start
        adjacency: dict[tuple[str, int], list[tuple[str, int]]] = {}
        for i, j in basis:
            adjacency.setdefault(("row", i), []).append(("col", j))
            adjacency.setdefault(("col", j), []).append(("row", i))

        source, target = ("col", j0), ("row", i0)
        parent: dict[tuple[str, int], tuple[str, int] | None] = {source: None}
        queue = deque([source])
        while queue and target not in parent:
            node = queue.popleft()
            for neighbour in adjacency.get(node, []):
                if neighbour not in parent:
                    parent[neighbour] = node
                    queue.append(neighbour)
        if target not in parent:
            raise RuntimeError(f"Не удалось построить цикл пересчёта для клетки {start}")

        cycle = [start]
        node = target
        while parent[node] is not None:
            previous = parent[node]
            row_node, col_node = (node, previous) if node[0] == "row" else (previous, node)
            cycle.append((row_node[1], col_node[1]))
            node = previous
        return cycle

    def pivot(plan: list[list[float]], basis: set[Cell], cycle: list[Cell]) -> float:
        minus_cells = cycle[1::2]
        theta = min(plan[i][j] for i, j in minus_cells)
        leaving = min(
            (cell for cell in minus_cells if plan[cell[0]][cell[1]] - theta <= EPSILON),
        )
        for k, (i, j) in enumerate(cycle):
            plan[i][j] += theta if k % 2 == 0 else -theta
            if abs(plan[i][j]) <= EPSILON:
                plan[i][j] = 0.0
        basis.remove(leaving)
        basis.add(cycle[0])
        plan[leaving[0]][leaving[1]] = 0.0
        return theta

    plan, basis = build_initial_plan()
    use_bland = False
    max_iterations = 100 * (m * n + 1)
    for _ in range(max_iterations):
        u, v = compute_potentials(basis)
        entering = find_entering_cell(basis, u, v, use_bland)
        if entering is None:
            break
        theta = pivot(plan, basis, find_cycle(basis, entering))
        use_bland = theta <= EPSILON
    else:
        raise RuntimeError("Превышено допустимое число итераций метода потенциалов")

    for i in range(m):
        for j in range(n):
            table.supply_volumes[i, j] = plan[i][j]
