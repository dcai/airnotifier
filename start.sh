#!/bin/bash
set -e

if [ ! -f "/config/airnotifier.conf" ]; then
        cp /airnotifier/airnotifier.conf-sample /config/airnotifier.conf
fi
if [ ! -f "/config/logging.ini" ]; then
        cp /airnotifier/logging.ini-sample /config/logging.ini
fi

if [ -f "airnotifier.conf" ]; then
        rm airnotifier.conf
fi
ln -s /config/airnotifier.conf

if [ -f "logging.ini" ]; then
        rm logging.ini
fi
ln -s /config/logging.ini

if [ -n "$MONGO_SERVER" ]; then
        sed -i "s/mongohost = \"localhost\"/mongohost = \"$MONGO_SERVER\"/g" /config/airnotifier.conf
fi
if [ -n "$MONGO_PORT" ]; then
        sed -i "s/mongoport = 27017/mongoport = $MONGO_PORT/g" /config/airnotifier.conf
fi

echo "Starting Airnotifier ..."
python airnotifier.py >> /var/log/airnotifier/airnotifier.log 2>> /var/log/airnotifier/airnotifier.err
