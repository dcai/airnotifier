#!/bin/sh

#Token creation and deletion
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: bargainmate" -H "X-AN-APP-KEY: XXX" -X POST http://localhost:8000/users -d "username=dongsheng&password=cds&email=hi@dongsheng.org"
