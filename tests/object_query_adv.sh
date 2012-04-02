#!/bin/sh

#Token creation and deletion
echo "Searching books has more then 1000 pages"
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -G --data-urlencode 'where={"pages":{"$gt":1000}}' -X GET http://localhost:8000/objects/books
echo ""
echo "Searching books has less than 1000 pages"
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -G --data-urlencode 'where={"pages":{"$lt":1000}}' -X GET http://localhost:8000/objects/books
echo ""
