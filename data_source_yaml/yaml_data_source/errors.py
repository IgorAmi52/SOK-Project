class YamlDataSourceError(Exception):
    pass


class YamlInputError(YamlDataSourceError):
    pass


class YamlReferenceResolutionError(YamlDataSourceError):
    pass
