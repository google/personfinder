A directory for third-party libraries.

To update contents of this directory, run this command at the root directory:
```
$ pip install --upgrade -r requirements.txt -t app/vendors
```

Do not manually modify contents of this directory. If we need to apply a patch to any library, the library should go directly into app directory, not app/vendors.
