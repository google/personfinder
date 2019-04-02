"""Module for site-specific settings.

Some "constants" are expected to be the same for any Person Finder installation
(for example, the set of languages that are handled as right-to-left languages
would not change); those are stored in the const module. However, others things
might vary from one installation to another: for example, an organization that
runs Person Finder at a subdirectory instead of root would need to set the
OPTIONAL_PATH_PREFIX value here.

TODO(nworden): move more values here as appropriate (e.g.,
DEFAULT_LANGUAGE_CODE)
"""

OPTIONAL_PATH_PREFIX = 'personfinder/'
