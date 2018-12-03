from archii import config


def extension(document):
    meta_config = config.get().meta_config
    if document.extension in meta_config.documents:
        return 1
    if document.extension in meta_config.presentations:
        return 2
    if document.extension in meta_config.spreadsheets:
        return 3
    if document.extension in meta_config.hypertext:
        return 4
    return 0
