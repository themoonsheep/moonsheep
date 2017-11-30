# moonsheep
Crowdsource data from PDFs

## Run app
### Launch pybossa app
```
cd pybossa
workon pybossa
redis-server contrib/sentinel.conf --sentinel
python run.py
```
### Launch pybossa webhooks
```
cd pybossa
workon pybossa
python app_context_rqworker.py scheduled_jobs super high medium low email maintenance
```
### Launch your app
```
cd myapp
workon myapp
python runserver 0.0.0.0:8000
```