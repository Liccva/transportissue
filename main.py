import argparse
import sys
from pathlib import Path

from tabulate import tabulate

from transport_problem.batch import (
    SUMMARY_HEADERS, collect_inputs, output_paths, solve_file, summary_rows, write_summary,
)

PROJECT_DIR = Path(__file__).parent
DEFAULT_DATA_PATH = PROJECT_DIR / "data" / "Транспортная_задача_шаблон_данных.xlsx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Решение транспортной задачи методом потенциалов")
    parser.add_argument("inputs", nargs="*", default=[str(DEFAULT_DATA_PATH)],
                        help="файлы .xlsx, папки или шаблоны вида data/*.xlsx")
    parser.add_argument("-o", "--output", type=Path, help="файл результата (для одного входного файла)")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_DIR / "results",
                        help="папка для результатов (по умолчанию results/)")
    parser.add_argument("-f", "--format", choices=["xlsx", "csv", "json"], default="xlsx",
                        help="формат результатов и сводки (по умолчанию xlsx)")
    parser.add_argument("--sheet", help="лист книги Excel с исходными данными (по умолчанию первый)")
    parser.add_argument("--into-input", action="store_true",
                        help="добавить листы с результатами в исходную книгу Excel")
    parser.add_argument("-q", "--quiet", action="store_true", help="не выводить таблицы планов")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inputs = collect_inputs(args.inputs)
    if not inputs or (args.output and len(inputs) > 1):
        print("Нет входных файлов." if not inputs else "Ключ -o допустим только для одного входного файла.",
              file=sys.stderr)
        return 2

    outputs = [args.output] if args.output else output_paths(inputs, args.output_dir, f".{args.format}")
    results = [solve_file(source, output, sheet=args.sheet, into_input=args.into_input)
               for source, output in zip(inputs, outputs)]
    for result in results:
        print(f"=== {result.source.name} ===")
        if not result.ok:
            print("Ошибка:\n  • " + result.error.replace("; ", "\n  • ") + "\n")
            continue
        if not args.quiet:
            result.table.represent()
        else:
            print(f"Стоимость перевозок: {result.table.transportation_costs:g}")
        print(f"Результаты сохранены: {result.output}\n")

    if len(results) > 1:
        summary_path = args.output_dir / f"сводка.{args.format}"
        write_summary(results, summary_path)
        rows = [[*row[:-1], (row[-1] or "")[:60]] for row in summary_rows(results)]
        print(tabulate(rows, headers=SUMMARY_HEADERS, missingval=""))
        print(f"\nСводка сохранена: {summary_path}")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
