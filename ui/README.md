# UI

This directory is for the React (non-lite/AMP) UI.

## Development server

Before you get started with development of the React UI, you need to install a
couple things. First, you need Node.js and NPM (the Node.js package manager,
often included with Node.js). You can refer to the Node.js website for
instructions on [downloading Node.js directly](https://nodejs.org/en/download/)
or [via a package manager](https://nodejs.org/en/download/package-manager/).

Once you have Node.js and NPM, you can run `npm install` from the `ui` directory
to get the dependencies for our React app.

Once you have everything, the easiest way to develop the UI is to run two local
servers:

1. Run the Django (backend) server as usual, at port 8080 (default).
2. Enable the React UI support (currently disabled by default) in the backend by
   setting `enable_react_ui` config to True:
    ```
    $ ./tools/console localhost:8080
    > config.set(enable_react_ui=True)
    ```
3. Run the UI with `tools/ui run`. It will talk to the backend at port 8080 when
   it needs to make API calls. There is currently an issue with uploaded photos:
   the Webpack dev server is not set up to proxy requests for photo URLs, but it
   also can't serve the photos on its own, so photos will not correctly appear
   on a local server when you run the UI dev server with Webpack.

Changes you make to the JS and CSS will take effect when you refresh the page.
If you make other changes (e.g., to install a new module or modify the Webpack
config) you'll likely need to restart the server.

## Testing

Tests can be run with `tools/ui test` or (from within the `ui` directory) `npm
run test`. The test file for a file `X.js` should be co-located with `X.js` and
should be called `X_test.js`.

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
