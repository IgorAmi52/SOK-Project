class JsonDataSourceError(Exception):
    pass


class JsonInputError(JsonDataSourceError):
    pass


class JsonReferenceResolutionError(JsonDataSourceError):
    pass
