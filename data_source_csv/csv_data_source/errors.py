class CsvPluginError(ValueError):
    """Base error for CSV data-source plugin failures."""


class CsvParameterError(CsvPluginError):
    """Raised for invalid or missing plugin parameters."""


class CsvParsingError(CsvPluginError):
    """Raised for CSV content/format parsing problems."""
