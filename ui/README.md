# UI

This directory is for the React (non-lite/AMP) UI.

## Development server

The easiest way to develop the UI is to run two local servers:

1. Run the Django (backend) server as usual, at port 8000.
2. Run the UI with `tools/ui run`. It will talk to the backend at port 8000.

Changes you make to the JS and CSS will take effect when you refresh the page.
If you make other changes (e.g., to install a new module or modify the Webpack
config) you'll likely need to restart the server.

Currently, it is necessary to change `USE_REACT_UI` in `app/main.py` to `True`.
Please be careful not to commit this change.

## Deployment

You can run `tools/ui buildtoae` to compile the React app into
bundles (one for each language Person Finder supports, i.e., `en-bundle.js`,
`es-bundle.js`, etc.) and automatically move them (and static resources, like
icons) to the Django app's static directory.

## CSS

We use Sass to produce the CSS for the React UI. The source .scss files are
almost exactly like CSS files, but you can use variables and other neat things,
and it's particularly helpful to use it with the Material Web libraries (as you
can define values used by the Material CSS).

Most of our files (with the exception of `all.scss`) have names that start with
underscores. That's a signal to the Sass compiler that it's a partial file,
meant only for import from another file, so that the compiler doesn't generate a
standalone CSS file for it.

## Translations

We use react-intl, by Yahoo, for translations:
https://github.com/yahoo/react-intl/

By convention, we define the message used in a file in a constant at the top,
like so:

```javascript
const messages = defineMessages({
  repoRecordCount: {
    id: 'RepoHome.repoRecordCount',
    defaultMessage: 'Currently tracking {recordCount} records.',
    description: ('A message displaying how many data records we have in the '
        + 'database.'),
  },
  ... (more messages may follow)
});
```

Typically, that message is then used in a `FormattedMessage` component, like
this:

```javascript
<FormattedMessage
  {...messages.repoRecordCount}
  values={{"recordCount": 123}} />
```

In cases where a component cannot be used (for example, if it needs to be passed
as an argument to another function that expects a string), you can call
`intl.formatMessage` to get a regular string:

```javascript
this.props.intl.formatMessage(messages.repoRecordCount, {"recordCount": 123})
```

Another place you'll need to do it this way is for button texts: the React
Material Button component evidently doesn't like having other components as the
text, so you have to give it a string.

## Static files

For now, our static files are placed in /static/static for development. The
reason for this is that the Webpack dev server looks for static files in the
static directory and serves them from the root directory. However, in prod, we
don't serve static files from root; we serve them from a subdirectory, and
that's where the HTML React produces should point to. So, we reproduce the prod
directory structure inside the static directory Webpack uses.
