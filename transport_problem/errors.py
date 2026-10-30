class DataValidationError(ValueError):
    def __init__(self, errors: list[str], source: str | None = None):
        self.errors = list(errors)
        self.source = source
        header = f"Ошибки во входных данных ({source})" if source else "Ошибки во входных данных"
        super().__init__(header + ":\n" + "\n".join(f"  • {error}" for error in self.errors))
