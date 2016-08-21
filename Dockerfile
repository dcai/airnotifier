FROM python:2.7

ENV DEBIAN_FRONTEND=noninteractive TERM=linux

EXPOSE 8801
VOLUME ["/config", "/var/airnotifier", "/var/log/airnotifier"]

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    mkdir -p /var/airnotifier/pemdir

RUN git clone https://github.com/airnotifier/airnotifier.git /airnotifier

WORKDIR /airnotifier

RUN pip install -r requirements.txt
RUN sed -i 's/https = True/https = False/g' airnotifier.conf-sample

ADD start.sh /airnotifier
ENTRYPOINT /airnotifier/start.sh