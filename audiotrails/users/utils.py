def user_display(user):
    """Returns default rendering of a user. Used with the
    django_allauth user_display template tag."""
    return user.username
