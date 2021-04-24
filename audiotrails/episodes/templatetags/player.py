from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def is_playing(context, episode):
    return context["request"].player.is_playing(episode)


@register.simple_tag(takes_context=True)
def get_player(context):
    return context["request"].player.get_player_info()
