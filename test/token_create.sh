#!/bin/sh

#Token creation and deletion
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: 31bde27540b03bb221f14a815a690582" -X POST http://localhost:8801/tokens/9116fc350fbcb47a0ed078e214b7f13a9e9cb02105d16d76381c700e1da6c2be?device=android

