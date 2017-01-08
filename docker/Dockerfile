FROM python:2.7
LABEL authors="Carlo Lobrano <c.lobrano@gmail.com>, Mathieu Tortuyaux <mathieu.tortuyaux@gmail.com>"

# Get rid of debconf complaining about noninteractive mode
ENV DEBIAN_FRONTEND noninteractive
ENV PATH $PATH:/opt/google_appengine
ENV APPENGINE_DIR /opt/google_appengine/
ENV PERSONFINDER_DIR /opt/personfinder
ENV INIT_DATASTORE 0

RUN apt-get update
RUN apt-get install -y  unzip \
                        git \
                        wget \
                        time \
                        gettext

# Installing latest app engine sdk for Python
WORKDIR   /opt/
RUN wget  https://storage.googleapis.com/appengine-sdks/featured/google_appengine_1.9.25.zip
RUN unzip google_appengine_1.9.25.zip

# Add command to bin path
ADD gae-run-app.sh      /usr/bin/
ADD setup_datastore.sh  /usr/bin/

# Move into main directory
RUN mkdir -p /opt/personfinder
WORKDIR /opt/personfinder

# Installing requirement (PIL, pytest, lxml)
ADD requirements.txt /opt/personfinder/
RUN pip install --requirement requirements.txt

CMD ["/sbin/my_init"]

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
