# moonsheep
[![Build Status](https://travis-ci.org/themoonsheep/moonsheep.svg?branch=master)](https://travis-ci.org/themoonsheep/moonsheep)
[![Coverage Status](https://coveralls.io/repos/github/themoonsheep/moonsheep/badge.svg?branch=master)](https://coveralls.io/github/themoonsheep/moonsheep?branch=master)

Crowdsource data from PDFs

## Run app

1. Run pybossa app
```
cd pybossa
workon pybossa
redis-server contrib/sentinel.conf --sentinel
python run.py
```
2. Run pybossa webhooks
```
cd pybossa
workon pybossa
python app_context_rqworker.py scheduled_jobs super high medium low email maintenance
```
3. Run your app
```
cd myapp
workon myapp
export PYBOSSA_API_KEY='my-pybossa-api-key'
python runserver 0.0.0.0:8000
```
