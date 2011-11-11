
def redirect(handler):
    subdomain = get_subdomain(handler)
    if not subdomain and handler.subdomain_required:
        return handler.error(400, 'No subdomain specified')


def get_subdomain(handler):
    """Determines the subdomain of the request."""
    if handler.ignore_subdomain:
        return None

    # The 'subdomain' query parameter always overrides the hostname
    if strip(handler.request.get('subdomain', '')):
        return strip(handler.request.get('subdomain'))

    levels = handler.request.headers.get('Host', '').split('.')
    if levels[-2:] == ['appspot', 'com'] and len(levels) >= 4:
        # foo.person-finder.appspot.com -> subdomain 'foo'
        # bar.kpy.latest.person-finder.appspot.com -> subdomain 'bar'
        return levels[0]

    # Use the 'default_subdomain' setting, if present.
    return config.get('default_subdomain')
