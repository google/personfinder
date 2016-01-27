Want to contribute? Great! First, read this page (including the small print at the end).

### Before you contribute
Before we can use your code, you must sign the
[Google Individual Contributor License Agreement](https://cla.developers.google.com/about/google-individual)
(CLA), which you can do online. The CLA is necessary mainly because you own the
copyright to your changes, even after your contribution becomes part of our
codebase, so we need your permission to use and distribute your code. We also
need to be sure of various other things—for instance that you'll tell us if you
know that your code infringes on other people's patents. You don't have to sign
the CLA until after you've submitted your code for review and a member has
approved it, but you must do it before we can put your code into our codebase.
Before you start working on a larger contribution, you should get in touch with
us first through the issue tracker with your idea so that we can help out and
possibly guide you. Coordinating up front makes it much easier to avoid
frustration later on.

### Set up your development environment
See [GettingStarted](https://github.com/google/personfinder/wiki/GettingStarted).

### Code reviews
All submissions, including submissions by project members, require review. We
use Github pull requests for this purpose.

#### For Person Finder team members

1. Make sure that you are [a member of the team](https://github.com/orgs/google/teams/personfinder). Ask @gimite to add you if you are not.
1. Install hub commandline tool.
    <br/>https://github.com/github/hub
1. Find an issue to work on, or create a new one.
   <br/>https://github.com/google/personfinder/issues
1. Create a new branch, prefixed with your username.
   <br/>`$ git checkout -b $USER-your-new-feature`
1. Make changes and commit. Repeat the step until you are ready for code review.
   <br/>`$ git commit -a`
1. Push your local changes to the remote repository.
   <br/>`$ git push -u origin $USER-your-new-feature`
1. Create a new pull request. (-i is optional, but strongly encouraged.)
   <br/>`$ hub pull-request -i <issue #>`
1. The pull request will be reviewed by one of the code reviewers (*) and
   merged to the master branch after addressing reviewer's comments.
   (@gimite or @skywhale as of 2015/10).

#### For non-team members

1. Find an issue to work on, or create a new one.
   <br/>https://github.com/google/personfinder/issues
1. Fork [google/personfinder project](https://github.com/google/personfinder) on Github.
1. Make changes and push to your fork. Repeat the step until you are ready for code review.
   <br/>`$ git commit -a`
   <br/>`$ git push -u origin $YOUR_BRANCH`
1. Create a new pull request.
1. The pull request will be reviewed by one of the code reviewers (*) and
   merged to the master branch after addressing reviewer's comments.
   (@gimite or @skywhale as of 2015/10).

### The small print
Contributions made by corporations are covered by a different agreement than
the one above, the
[Software Grant and Corporate Contributor License Agreement](https://cla.developers.google.com/about/google-corporate).
