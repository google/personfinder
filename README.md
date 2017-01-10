README
======

This folder contains a Dockerfile and some utilities that simplify the creation
of a Docker container for Personfinder development and testing.

Steps to create the container
-----------------------------

1. Setup the environment for Docker (see Docker's webpage)
2. Build Person Finder Docker image

    From `personfinder/docker` folder, run

        $ docker build -t <image-name> .

    e.g.

        $ docker build -t personfinder-image .

    This will take a while and will create the docker image.

3. Create the container

    Run the following command

    $ ./run-container.sh <image-name> [<container-name>]

    e.g. (Container's name is optional)

        $ ./run-container.sh personfinder-image personfinder-container

    This will create and run at the same time the container image. To manage
    the container's lifecycle (start, stop, destroy, etc.) please refer to the
    Docker's documentation.

4. Run the Person Finder local server and test it from host's web browser

    In the SHELL created inside the Person Finder container, run the following
    command to run the Person Finder local server:

        # gae-run-app.sh

    You will be able to access the server from the Host's web browser at
    https://<container-ip-address>:8000


5. Initialize the datastore:

    Open one more SHELL inside the running container by running the following
    command on the Host (Docker version 1.3.0 or higher, for older Docker
    versions, docker's "attach" command should do the job as well).

        $ docker exec -it <container-name> /bin/bash

    then, inside the container, run the following (password is "root")

        # setup_datastore.sh


NOTES
-----

The Personfinder's source code folder is shared among host and Docker container,
in order to let the developer choose the development tools (e.g. IDE) which
he/she prefers. In the Docker container, the Personfider's source code will be
available in `/opt/personfinder` folder.
