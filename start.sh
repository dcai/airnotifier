#!/bin/bash
set -e

export LOGDIR=/var/log/airnotifier
export LOGFILE=$LOGDIR/airnotifier.log
export LOGFILE_ERR=$LOGDIR/airnotifier.err

if [ ! -f "/config/config.py" ]; then
  cp config.py-sample config.py
fi

sed -i 's/https = True/https = False/g' ./config.py

if [ ! -f "/config/logging.ini" ]; then
  cp logging.ini-sample logging.ini
fi

if [ -n "$MONGO_SERVER" ]; then
  sed -i "s/mongohost = \"localhost\"/mongohost = \"$MONGO_SERVER\"/g" ./config.py
fi
if [ -n "$MONGO_PORT" ]; then
  sed -i "s/mongoport = 27017/mongoport = $MONGO_PORT/g" ./config.py
fi

if [ ! -f "$LOGFILE" ]; then
  touch "$LOGFILE"
fi

if [ ! -f "$LOGFILE_ERR" ]; then
  touch "$LOGFILE_ERR"
fi

echo "Installing AirNotifier ..."
pipenv run ./install.py
echo "Starting AirNotifier ..."
pipenv run ./app.py >> "$LOGFILE" 2>> "$LOGFILE_ERR"
