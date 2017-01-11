FROM phusion/baseimage
LABEL authors="Carlo Lobrano <c.lobrano@gmail.com>, Mathieu Tortuyaux <mathieu.tortuyaux@gmail.com>"

CMD ["/sbin/my_init"]

# Get rid of debconf complaining about noninteractive mode
ENV DEBIAN_FRONTEND noninteractive
ENV PATH $PATH:/opt/google_appengine
ENV APPENGINE_DIR /opt/google_appengine/
ENV PERSONFINDER_DIR /opt/personfinder
ENV INIT_DATASTORE 0

RUN apt-get update && apt-get install -y \
	build-essential \
	unzip \
	python2.7 \
	libpython2.7-dev \
	git \
	time \
	gettext \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

# Install app engine
WORKDIR   /opt/
ADD https://storage.googleapis.com/appengine-sdks/featured/google_appengine_1.9.25.zip /opt/
RUN unzip -qq google_appengine_1.9.25.zip && rm google_appengine_1.9.25.zip

ADD gae-run-app.sh      /usr/bin/
ADD setup_datastore.sh  /usr/bin/


COPY . /opt/personfinder
WORKDIR /opt/personfinder/

# Clean up
RUN rm -rf /tmp/* /var/tmp/*

