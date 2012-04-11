#!/bin/sh

#Token creation and deletion
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -X POST http://localhost:8000/objects/books -d '{"book": "A tale of two cities", "stock": 5, "pages": 200}'
echo ""
