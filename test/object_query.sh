#!/bin/sh

#Token creation and deletion
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: ca36ca26233a8178eb870a2e5229e803" -X GET http://localhost:8801/objects/books/4f96499429ddda206c000001
