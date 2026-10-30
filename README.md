# Транспортная задача (метод потенциалов)

Python 3.12+.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск

```bash
python main.py                                   # данные из data/Транспортная_задача_шаблон_данных.xlsx
python main.py data/пример.xlsx                  # свой файл
python main.py data/пример.xlsx -o результат.csv # свой путь и формат результата (xlsx, csv, json)
python main.py data                              # все файлы папки + сводка
python main.py data/несколько_листов.xlsx --sheet МКТЗ
python main.py задача.xlsx --into-input          # листы результата — в исходную книгу
python main.py -h                                # все параметры
```

Результаты сохраняются в `results/<имя файла>_решение.xlsx`.

## Тесты

```bash
python -m unittest discover -s tests -t .
```
