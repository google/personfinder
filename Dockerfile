FROM phusion/baseimage
LABEL authors="Carlo Lobrano <c.lobrano@gmail.com>, Mathieu Tortuyaux <mathieu.tortuyaux@gmail.com>"

CMD ["/sbin/my_init"]

# Get rid of debconf complaining about noninteractive mode
ENV DEBIAN_FRONTEND noninteractive
ENV PATH $PATH:/opt/google_appengine
ENV APPENGINE_DIR /opt/google_appengine/
ENV PERSONFINDER_DIR /opt/personfinder/
ENV INIT_DATASTORE 0

RUN apt-get update && apt-get install -y \
	build-essential \
	unzip \
	python2.7 \
	libpython2.7-dev \
	curl \
	git \
	time \
	gettext \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && /usr/bin/python2.7 get-pip.py
RUN pip install pytest==3.7.4 lxml cssselect pillow==4.1.0 mock modernize

# Just apt-get installing nodejs doesn't work; these commands come from:
# https://askubuntu.com/questions/720784/how-to-install-latest-node-inside-a-docker-container
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash
RUN apt-get install -y nodejs

# Install app engine
WORKDIR   /opt/
ADD https://storage.googleapis.com/appengine-sdks/featured/google_appengine_1.9.62.zip /opt/
RUN unzip -qq google_appengine_1.9.62.zip && rm google_appengine_1.9.62.zip

ADD docker/gae-run-app.sh      /usr/bin/
ADD docker/setup_datastore.sh  /usr/bin/

RUN echo "opt_in: false\ntimestamp: $(date +%s)\n" > /root/.appcfg_nag

WORKDIR /opt/personfinder/

# Clean up
RUN rm -rf /tmp/* /var/tmp/*

