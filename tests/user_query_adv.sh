#!/bin/sh

#Token creation and deletion
echo "Searching username = dongsheng"
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -G --data-urlencode 'where={"username":"dongsheng"}' -X GET http://localhost:8000/users
echo ""
