# Contributing
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
See [Getting Started](https://github.com/google/personfinder/wiki/GettingStarted).

### Code reviews
All submissions, including submissions by project members, require review. We
use Github pull requests for this purpose.

#### For Person Finder team members

1. Make sure that you are [a member of the team](https://github.com/orgs/google/teams/personfinder). Ask @gimite to add you if you are not.
1. Find an issue to work on, or create a new one, in [the issue list](https://github.com/google/personfinder/issues).
    * If it is the first time for you to contribute to this project, I recommend you to start from one of the issues marked as [low hanging](https://github.com/google/personfinder/issues?q=is%3Aissue+is%3Aopen+label%3A%22low+hanging%22).
1. Comment on the issue that you will work on the issue (to avoid conflict).
1. Create a new branch, prefixed with your username.
   <br/>`$ git checkout -b $USER-your-new-feature`
1. Make changes and commit. Repeat the step until you are ready for code review.
   <br/>`$ git commit -a`
1. Make sure the unit tests and the server tests pass.
   <br/>`$ tools/all_tests`
1. Push your local changes to the remote repository.
   <br/>`$ git push -u origin $USER-your-new-feature`
1. Create a new pull request. If you go to https://github.com/google/personfinder, it should show a button to suggest creating a pull request for your branch. Or, you can install [hub commandline tool](https://github.com/github/hub) and run:
   <br/>`$ hub pull-request -i <issue #>`
   <br/>(-i is optional, but strongly encouraged.)
1. The pull request will be reviewed by one of the code reviewers (*) and
   merged to the master branch after addressing reviewer's comments.
   (@gimite as of 2016/8).

#### For non-team members

1. Find an issue to work on, or create a new one, in [the issue list](https://github.com/google/personfinder/issues).
    * If it is the first time for you to contribute to this project, I recommend you to start from one of the issues marked as [low hanging](https://github.com/google/personfinder/issues?q=is%3Aissue+is%3Aopen+label%3A%22low+hanging%22).
1. Comment on the issue that you will work on the issue (to avoid conflict).
1. Fork [google/personfinder project](https://github.com/google/personfinder) on Github.
1. Make changes and push to your fork. Repeat the step until you are ready for code review.
   <br/>`$ git commit -a`
   <br/>`$ git push -u origin $YOUR_BRANCH`
1. Make sure the unit tests and the server tests pass.
1. Create a new pull request.
1. The pull request will be reviewed by one of the code reviewers (*) and
   merged to the master branch after addressing reviewer's comments.
   (@gimite as of 2016/8).

#### For code reviewers

1. Assign yourself as a reviewer of the pull request if it doesn't have one.
1. Review the code and leave comments. Check that it follows [Google Python Style Guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md) and/or the [Google JavaScript Style Guide](https://google.github.io/styleguide/jsguide.html) (except the parts related to the Closure compiler, which we don't use).
1. Approve the pull request once you are happy.
1. Confirm that all system checks have passed. If CLA check is failing, point the author to this page and ask them to sign CLA.
1. Choose and click [Squash and merge] to pull the change. That's the best option to keep the Git commit tree clean.

### The small print
Contributions made by corporations are covered by a different agreement than
the one above, the
[Software Grant and Corporate Contributor License Agreement](https://cla.developers.google.com/about/google-corporate).
