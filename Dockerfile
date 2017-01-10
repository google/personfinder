FROM python:2.7
LABEL authors="Carlo Lobrano <c.lobrano@gmail.com>, Mathieu Tortuyaux <mathieu.tortuyaux@gmail.com>"

# Get rid of debconf complaining about noninteractive mode
ENV DEBIAN_FRONTEND noninteractive
ENV PATH $PATH:/opt/google_appengine
ENV APPENGINE_DIR /opt/google_appengine/
ENV PERSONFINDER_DIR /opt/personfinder
ENV INIT_DATASTORE 0

RUN apt-get update && apt-get install -y \ 
			build-essential \
			unzip \
                        git \
                        time \
                        gettext \
			python2.7 \
			libpython2.7-dev \
			python-pip \
			&& apt-get clean \
			&& rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

# Installing latest app engine sdk for Python
WORKDIR   /opt/
ADD https://storage.googleapis.com/appengine-sdks/featured/google_appengine_1.9.25.zip /opt/
RUN unzip -qq google_appengine_1.9.25.zip && rm google_appengine_1.9.25.zip

# Add command to bin path
ADD gae-run-app.sh      /usr/bin/
ADD setup_datastore.sh  /usr/bin/


COPY . /opt/personfinder
WORKDIR /opt/personfinder

RUN pip install -b app/lib --requirement requirements.txt

CMD ["/sbin/my_init"]

# Clean up 
RUN rm -rf /tmp/* /var/tmp/*
