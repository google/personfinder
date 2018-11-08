This directory contains resource files e.g., HTML templates and images.

There are two types of resources; static and dynamic.

* Static resources: Files under "static" subdirectory. These files are
  directly served via HTTP. e.g., static/hoge.html is visible at
  http://$HOSTNAME/$REPO/hoge.html.

* Dynamic resources: Everything else in this directory. These files are used
  in code, typically via utils.BaseHandler.render() or functions in
  **resources** module. Dynamic resources are not directly visible via HTTP
  for security reason.

You can use these special suffixes of file names for both types of resources:

* ".template" to interpret them as Django template.

* ":" followed by a language name e.g., ":ja" to indicate that it is a
  localized version of the resource.

Also see app/resources.py which covers some more details.
