class YamlDataSourceError(Exception):
    """Base exception for all YAML data-source errors."""


class YamlInputError(YamlDataSourceError):
    """Raised when the YAML input file is missing, unreadable, or malformed."""


class YamlReferenceResolutionError(YamlDataSourceError):
    """Raised when one or more YAML object references cannot be resolved."""
