import math
from abc import ABC, abstractmethod
from collections.abc import Sequence
from numbers import Real

from tabulate import tabulate

EPSILON = 1e-9


def format_number(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def _is_number(value) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


class Storage(ABC):
    def __init__(self, name: str, resources: float):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Наименование должно содержать по крайней мере один символ")
        if not _is_number(resources) or resources < 0:
            raise ValueError(
                f"Объём ресурсов '{name}' должен быть неотрицательным числом, получено: {resources!r}"
            )
        self.name: str = name
        self.resources: float = float(resources)

    @abstractmethod
    def __str__(self) -> str: ...

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r}, {format_number(self.resources)})"


class Supplier(Storage):
    def __str__(self) -> str:
        return f"Поставщик {self.name} (объём запасов: {format_number(self.resources)})"


class Consumer(Storage):
    def __str__(self) -> str:
        return f"Потребитель {self.name} (объём потребления: {format_number(self.resources)})"


class Matrix:
    def __init__(self, items: Sequence[Sequence[float]]):
        rows = [list(row) for row in items]
        if rows and any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("Все строки матрицы должны иметь одинаковую длину")
        for i, row in enumerate(rows):
            self._validate_values(row, f"строке {i}")
        self.items: list[list[float]] = rows

    @classmethod
    def zeros(cls, num_rows: int, num_cols: int) -> "Matrix":
        return cls([[0.0] * num_cols for _ in range(num_rows)])

    @staticmethod
    def _validate_values(values: Sequence[float], location: str) -> None:
        for value in values:
            if not _is_number(value) or value < 0:
                raise ValueError(
                    f"Элементы матрицы должны быть неотрицательными числами, "
                    f"в {location} получено: {value!r}"
                )

    @property
    def num_rows(self) -> int:
        return len(self.items)

    @property
    def num_cols(self) -> int:
        return len(self.items[0]) if self.items else 0

    def __getitem__(self, index: tuple[int, int]) -> float:
        i, j = index
        return self.items[i][j]

    def __setitem__(self, index: tuple[int, int], value: float) -> None:
        self._validate_values([value], f"ячейке {index}")
        i, j = index
        self.items[i][j] = value

    def add_row(self, values: Sequence[float]) -> None:
        values = list(values)
        if self.items and len(values) != self.num_cols:
            raise ValueError(f"Длина строки должна быть равна {self.num_cols}")
        self._validate_values(values, "добавляемой строке")
        self.items.append(values)

    def add_column(self, values: Sequence[float]) -> None:
        values = list(values)
        if len(values) != self.num_rows:
            raise ValueError(f"Длина столбца должна быть равна {self.num_rows}")
        self._validate_values(values, "добавляемом столбце")
        for row, value in zip(self.items, values):
            row.append(value)

    def __repr__(self) -> str:
        return f"Matrix({self.items!r})"


class TransportTable:
    FICTIVE_NAME = "Фиктивный"

    def __init__(
        self,
        suppliers: Sequence[Supplier],
        consumers: Sequence[Consumer],
        transport_coefficients: Matrix,
    ):
        if not all(isinstance(s, Supplier) for s in suppliers):
            raise TypeError("Все элементы suppliers должны иметь тип Supplier")
        if not all(isinstance(c, Consumer) for c in consumers):
            raise TypeError("Все элементы consumers должны иметь тип Consumer")
        if not isinstance(transport_coefficients, Matrix):
            raise TypeError("transport_coefficients должен иметь тип Matrix")
        if not suppliers or not consumers:
            raise ValueError("Должен быть задан хотя бы один поставщик и один потребитель")

        self.suppliers: list[Supplier] = list(suppliers)
        self.consumers: list[Consumer] = list(consumers)
        self.transport_coefficients: Matrix = transport_coefficients
        self.fictive: Supplier | Consumer | None = None

        self._validate_dimensions()
        self._balance()

        self.supply_volumes: Matrix = Matrix.zeros(
            self.transport_coefficients.num_rows, self.transport_coefficients.num_cols
        )

    def _validate_dimensions(self) -> None:
        if self.transport_coefficients.num_rows != len(self.suppliers):
            raise ValueError(
                f"Количество строк матрицы тарифов ({self.transport_coefficients.num_rows}) "
                f"не совпадает с количеством поставщиков ({len(self.suppliers)})"
            )
        if self.transport_coefficients.num_cols != len(self.consumers):
            raise ValueError(
                f"Количество столбцов матрицы тарифов ({self.transport_coefficients.num_cols}) "
                f"не совпадает с количеством потребителей ({len(self.consumers)})"
            )

    def _balance(self) -> None:
        difference = self.total_supply - self.total_demand
        if math.isclose(difference, 0, abs_tol=EPSILON):
            return
        if difference > 0:
            self.fictive = Consumer(self.FICTIVE_NAME, difference)
            self.consumers.append(self.fictive)
            self.transport_coefficients.add_column([0] * len(self.suppliers))
        else:
            self.fictive = Supplier(self.FICTIVE_NAME, -difference)
            self.suppliers.append(self.fictive)
            self.transport_coefficients.add_row([0] * len(self.consumers))

    @property
    def total_supply(self) -> float:
        return sum(s.resources for s in self.suppliers)

    @property
    def total_demand(self) -> float:
        return sum(c.resources for c in self.consumers)

    @property
    def transportation_costs(self) -> float:
        return sum(
            self.transport_coefficients[i, j] * self.supply_volumes[i, j]
            for i in range(len(self.suppliers))
            for j in range(len(self.consumers))
        )

    def represent(self) -> None:
        headers = ["Поставщики \\ Потребители", *(c.name for c in self.consumers), "Запасы"]
        rows = []
        for i, supplier in enumerate(self.suppliers):
            volumes = [
                format_number(self.supply_volumes[i, j]) if self.supply_volumes[i, j] > EPSILON else "-"
                for j in range(len(self.consumers))
            ]
            rows.append([supplier.name, *volumes, format_number(supplier.resources)])
        rows.append(
            [
                "Потребление",
                *(format_number(c.resources) for c in self.consumers),
                format_number(self.total_supply),
            ]
        )
        print(tabulate(rows, headers=headers, tablefmt="grid", stralign="center", numalign="center"))
        print(f"Суммарная стоимость перевозок: {format_number(self.transportation_costs)}")
