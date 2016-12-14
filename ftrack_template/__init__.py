import os
import uuid
import imp

import lucidity
import ftrack_api

from .template import Template


def discover_templates(paths=None, recursive=True):
    '''Taken from lucidity.

    Search *paths* for mount points and load templates from them.
    *paths* should be a list of filesystem paths to search for mount points.
    If not specified will try to use value from environment variable
    :envvar:`FTRACK_TEMPLATE_PATH`.
    A mount point is a Python file that defines a 'register' function. The
    function should return a list of instantiated
    :py:class:`~ftrack_template.template.Template` objects.
    If *recursive* is True (the default) then all directories under a path
    will also be searched.
    '''
    templates = []
    if paths is None:
        paths = os.environ.get('FTRACK_TEMPLATES_PATH', '').split(os.pathsep)
    for path in paths:
        for base, directories, filenames in os.walk(path):
            for filename in filenames:
                _, extension = os.path.splitext(filename)
                if extension != '.py':
                    continue
                module_path = os.path.join(base, filename)
                module_name = uuid.uuid4().hex
                module = imp.load_source(module_name, module_path)
                try:
                    registered = module.register()
                except AttributeError:
                    pass
                else:
                    if registered:
                        templates.extend(registered)
            if not recursive:
                del directories[:]
    return templates


def recurse_attribute_list(entity, attribute_list, padding=3, result=None):

    if result is None:
        result = {}

    key = attribute_list[0]
    value = entity[key]
    if isinstance(entity[key], int):
        value = str(value).zfill(padding)
    result[key] = value
    del attribute_list[0]

    if attribute_list:
        result[key] = recurse_attribute_list(
            entity[key], attribute_list
        )

    return result


def get_entity_data(entity, keys):

    # Collect parents from entity
    entity_data = {}
    items = []

    if isinstance(entity, ftrack_api.entity.component.Component):
        if entity["container"]:
            items = entity["container"]["version"]["link"]
        else:
            items = entity["version"]["link"]
    if "link" in entity.keys():
        items = entity["link"]

    for item in items[:-1]:
        parent = entity.session.get(item["type"], item["id"])
        context_type = type(parent).entity_type.lower()
        entity_data[context_type] = parent

    entity_type = type(entity).entity_type.lower()
    entity_data[entity_type] = entity
    if entity_type == "assetversion":
        entity_data["task"] = entity["task"]
    if isinstance(entity, ftrack_api.entity.component.Component):
        if entity["container"]:
            entity_data["assetversion"] = entity["container"]["version"]
            entity_data["task"] = entity["container"]["version"]["task"]
            entity_data["asset"] = entity["container"]["version"]["asset"]
            entity_data["container"] = entity["container"]
        else:
            entity_data["assetversion"] = entity["version"]
            entity_data["task"] = entity["version"]["task"]
            entity_data["asset"] = entity["version"]["asset"]

        entity_data["component"] = entity

    # Collect attribute paths
    data = {}
    for key in keys:
        if key.startswith("#"):
            items = key.split(".")
            context_type = items[0].replace("#", "")

            if context_type in entity_data:
                attribute_data = recurse_attribute_list(
                    entity_data[context_type], items[1:]
                )

                data_item = data.get(items[0], {})
                data_item.update(attribute_data)
                data[items[0]] = data_item

    return data


def format(data, templates, entity=None,
           return_mode="best_match"):  # @ReservedAssignment

    keys = set()
    for template in templates:
        keys.update(template.keys())

    data.update(get_entity_data(entity, keys))
    valid_templates = []
    for template in templates:
        try:
            path = template.format(data)
        except lucidity.error.FormatError:
            continue
        else:
            valid_templates.append((path, template))

    if valid_templates:
        if return_mode == "best_match":
            match_count = 0
            best_match = None
            for template in valid_templates:
                if match_count < len(template[1].keys()):
                    match_count = len(template[1].keys())
                    best_match = template

            if best_match:
                return best_match

        if return_mode == "all":
            return valid_templates

    raise lucidity.error.FormatError(
        'Data {0!r} was not formattable by any of the supplied templates.'
        .format(data)
    )
