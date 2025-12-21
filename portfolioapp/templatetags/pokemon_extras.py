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
