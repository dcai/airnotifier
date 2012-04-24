#!/bin/sh

#Token creation and deletion
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: ca36ca26233a8178eb870a2e5229e803" -X POST http://localhost:8801/objects/books -d '{"book": "A tale of two cities", "stock": 5, "pages": 200}'
echo ""
