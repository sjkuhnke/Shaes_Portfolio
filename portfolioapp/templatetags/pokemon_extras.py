from django import template

register = template.Library()


@register.filter
def stat_name(index):
    """Convert stat index to name"""
    stat_names = ['HP', 'Attack', 'Defense', 'Sp. Atk', 'Sp. Def', 'Speed']
    try:
        return stat_names[int(index)]
    except (IndexError, ValueError):
        return 'Unknown'


@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter(name='zip')
def zip_lists(a, b):
    """Zip two lists together"""
    return zip(a, b)


@register.filter
def as_int(value):
    """Convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return value


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary in a template"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def pluralize(value, arg='s'):
    """Return plural suffix if value is not 1"""
    try:
        if int(value) == 1:
            return ''
        return arg
    except (ValueError, TypeError):
        return arg
