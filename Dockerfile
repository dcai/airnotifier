FROM python:3.7
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive TERM=linux
EXPOSE 8801

RUN apt-get update && \
            apt-get install -y --no-install-recommends git ca-certificates build-essential python3-dev libc6 python3-openssl libcurl4-openssl-dev curl python3-pycurl

RUN apt-get -y install nano
RUN pip3 install --upgrade pip
RUN export PYCURL_SSL_LIBRARY=openssl
RUN pip3 install --no-cache-dir --compile pycurl
RUN pip3 install pipenv pymongo tornado

RUN apt-get upgrade -y

RUN apt install -y logrotate
COPY logrotate_airnotifier /etc/logrotate.d/airnotifier
RUN mkdir -p /var/log/airnotifier/archive

RUN git clone --branch master https://github.com/massicos/airnotifier.git /airnotifier
RUN mkdir -p /var/airnotifier/pemdir && \
    mkdir -p /var/log/airnotifier

VOLUME ["/airnotifier", "/var/log/airnotifier", "/var/airnotifier/pemdir"]
WORKDIR /airnotifier

RUN pipenv install --deploy

ADD start.sh /airnotifier
RUN chmod a+x /airnotifier/start.sh
ENTRYPOINT /airnotifier/start.sh