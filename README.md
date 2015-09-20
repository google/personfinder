# Person Finder

Person Finder is a searchable missing person database written in Python and
hosted on App Engine.

Person Finder implements the PFIF data model and provides PFIF import and export
as well as PFIF Atom feeds. It was initially created by Google volunteers in
response to the Haiti earthquake in January 2010, and today contains
contributions from many volunteers inside and outside of Google. It was used
again for the earthquakes in Chile, Yushu, and Japan, and now runs at
http://google.org/personfinder/.

## How to Contribute

The following steps are for Person Finder team members. Fork and send pull
request in the standard way if you are not a team member.

1. Set up the developement environment.
  1. Set up your Git client. Make sure to set your name and email.
    <br/>https://help.github.com/articles/set-up-git/
  2. Install hub commandline tool.
    <br/>https://github.com/github/hub
  3. Clone the PF repository.
    <br/>`$ git clone https://github.com/google/personfinder.git pf`
2. Find an issue to work on, or create a new one.
   <br/>https://github.com/google/personfinder/issues
3. Create a new branch, prefixed with your username.
   <br/>`$ git checkout -b $USER-your-new-feature`
4. Make changes and commit. Repeat the step until you are ready for code review.
   <br/>`$ git commit -a`
5. Push your local changes to the remote repository.
   <br/>`$ git push -u origin $USER-your-new-feature`
6. Create a new pull request. (-i is optional, but strongly encouraged.)
   <br/>`$ hub pull-request -i <issue #>`
7. The pull request will be reviewed by one of the code reviewers (*) and
   merged to the master branch after addressing reviewer's comments.
   (ichikawa@google.com or ryok@google.com as of 2015/01/30).

## How to launch

1. Download Google App Engine SDK - https://cloud.google.com/appengine/downloads
2. Launch App Engine SDK and create a new project
3. Clone the repository and copy it to your App Engine project
4. In the file app.yaml make changes (change the name of your project and version)
5. Assemble your project by pressing Deploy
