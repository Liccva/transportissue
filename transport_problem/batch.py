import csv
import glob
import json
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

from .data_loader import DataLoader
from .errors import DataValidationError
from .models import TransportTable, format_number
from .result_writer import ResultWriter
from .solver import solve_transport_problem

SUMMARY_HEADERS = ["Файл", "Статус", "Поставщиков", "Потребителей", "Фиктивный участник",
                   "Стоимость перевозок", "Файл результата", "Ошибка"]


@dataclass
class BatchResult:
    source: Path
    output: Path | None = None
    table: TransportTable | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def collect_inputs(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        if Path(pattern).is_dir():
            found = Path(pattern).iterdir()
        elif glob.has_magic(pattern):
            found = map(Path, glob.glob(pattern, recursive=True))
        else:
            paths.append(Path(pattern))
            continue
        paths.extend(sorted(
            p for p in found
            if p.is_file() and p.suffix.lower() == ".xlsx" and not p.name.startswith("~$")
        ))
    return list(dict.fromkeys(p.resolve() for p in paths))


def output_paths(inputs: list[Path], output_dir: Path, suffix: str) -> list[Path]:
    stems = [p.stem for p in inputs]
    return [
        output_dir / f"{p.stem}{f'_{i + 1}' if stems.count(p.stem) > 1 else ''}_решение{suffix}"
        for i, p in enumerate(inputs)
    ]


def solve_file(source: Path, output: Path, *, sheet: str | None = None, into_input: bool = False) -> BatchResult:
    result = BatchResult(source)
    try:
        if not source.is_file():
            raise FileNotFoundError(f"Файл не найден: {source}")
        result.table = DataLoader.load_data(source, sheet=sheet)
        solve_transport_problem(result.table)
        output = source if into_input else output
        output.parent.mkdir(parents=True, exist_ok=True)
        ResultWriter.save_results(result.table, output, source, template_sheet=sheet, into_template=into_input)
        result.output = output
    except DataValidationError as error:
        result.error = "; ".join(error.errors)
    except Exception as error:
        result.error = str(error) or type(error).__name__
    return result


def summary_rows(results: list[BatchResult]) -> list[list[object]]:
    rows = []
    for r in results:
        t = r.table
        if not r.ok or t is None:
            rows.append([r.source.name, "Ошибка", None, None, None, None, None, r.error])
            continue
        fictive = "нет"
        if t.fictive is not None:
            kind = "поставщик" if t.fictive in t.suppliers else "потребитель"
            fictive = f"{kind}, {format_number(t.fictive.resources)}"
        rows.append([
            r.source.name, "OK",
            len(t.suppliers) - (t.fictive in t.suppliers),
            len(t.consumers) - (t.fictive in t.consumers),
            fictive, t.transportation_costs, r.output.name, None,
        ])
    return rows


def write_summary(results: list[BatchResult], path: Path) -> None:
    rows = summary_rows(results)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = [dict(zip(SUMMARY_HEADERS, row)) for row in rows]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif suffix == ".csv":
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(SUMMARY_HEADERS)
            writer.writerows(
                [format_number(v).replace(".", ",") if isinstance(v, float) else v for v in row] for row in rows
            )
    else:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Сводка"
        sheet.append(SUMMARY_HEADERS)
        for row in rows:
            sheet.append(row)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for column, width in zip("ABCDEFGH", [32, 10, 13, 14, 20, 20, 40, 80]):
            sheet.column_dimensions[column].width = width
            for cell in sheet[column]:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        sheet.freeze_panes = "A2"
        workbook.save(path)
