README
======

This folder contains a Dockerfile and some utilities that simplify the creation of a Docker container for Personfinder development and testing.

Steps to create the container
-----------------------------

1. Setup the environment for Docker (see Docker's webpage)
2. From `personfinder/docker` folder, run

    $ docker build -t <image-name> .

    e.g.

    $ docker build -t personfinder-image .

    This will take a while and will create the docker image.

3. Create the container running

    $ ./run-container.sh <image-name> [<container-name>]

    e.g.

    $ ./run-container.sh personfinder-image personfinder-container  # Container's name is optional

    This will create and run the container image.

4. Run the Personfinder local server and test it from host's web browser (https://<container-ip-address>:8000

    $ gae-run-app.sh

5. To initialize the datastore, open one more Shell inside the running container with the following command

    $ docker exec -it <container-name> /bin/bash

    then run (password is "root")

    $ setup_datastore.sh


NOTES
-----

The Personfinder's source code folder is shared among host and Docker container, in order to let the developer choose the development tools (e.g. IDE) which he/she prefers. In the Docker container, the Personfider's source code will be available in `/opt/personfinder` folder.
