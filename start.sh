#!/bin/bash
set -e

export LOGDIR=/var/log/airnotifier
export LOGFILE=$LOGDIR/airnotifier.log
export LOGFILE_ERR=$LOGDIR/airnotifier.err

if [ ! -f "./config.py" ]; then
  cp config.py-sample config.py
fi

sed -i 's/https = True/https = False/g' ./config.py

if [ ! -f "./logging.ini" ]; then
  cp logging.ini-sample logging.ini
fi

sed -i "s/mongouri = \"mongodb:\/\/localhost:27017\/\"/mongouri = \"mongodb:\/\/${MONGO_SERVER-localhost}:${MONGO_PORT-27017}\"/g" ./config.py

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
