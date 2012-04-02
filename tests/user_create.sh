#!/bin/sh

#Token creation and deletion
echo "Creating three users"
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -X POST http://localhost:8000/users -d "username=dongsheng&password=cds&email=hi@dongsheng.org"
echo ""
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -X POST http://localhost:8000/users -d "username=admin&password=cds&email=admin@dongsheng.org"
echo ""
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -X POST http://localhost:8000/users -d "username=tom&password=cds&email=hi@dongsheng.org"
echo ""
curl -i -H "Accept: application/json" -H "X-AN-APP-NAME: moodle" -H "X-AN-APP-KEY: b2b56dbb-fd1f-4749-9116-edbcbaf34f1d" -X POST http://localhost:8000/users -d "username=manager&password=cds&email=manager@dongsheng.org"
echo ""

echo "Done"
