# moonsheep
[![Build Status](https://travis-ci.org/themoonsheep/moonsheep.svg?branch=master)](https://travis-ci.org/themoonsheep/moonsheep)
[![Coverage Status](https://coveralls.io/repos/github/themoonsheep/moonsheep/badge.svg?branch=master)](https://coveralls.io/github/themoonsheep/moonsheep?branch=master)

Crowdsource data from PDFs

TODO update pending

## Run app
```
cd myapp
workon myapp
python runserver 0.0.0.0:8000
```


## Importing documents

Configuring backend:
1. Create a Model that will have an `url` field and annotate it with `@document` 
specifying which tasks should be created when importing document, ie.:

```python
from moonsheep.registry import document

@document(on_import_create=['opora.tasks.FindTableTask'])
class Report(models.Model):
    """
    The whole document to transcript
    """
    # initial data
    url = models.URLField(verbose_name=_("report URL"), unique=True)

    # all other fields should have null=True set so such object may be created just based on url.
    # later tasks will fill in other details 
```

If several tasks should be created for one document just list them:
```python
@document(on_import_create=['kmonitor_ad.tasks.Section1PersonalData', 'kmonitor_ad.tasks.Section2Properties', 'kmonitor_ad.tasks.Section3Movables'])
```

Then import documents. Right now only the import from HTTP index listings via command line is supported:

```bash
python manage.py moonsheep_import_http --host http://user@host/root  dir1 dir2/file1
python manage.py moonsheep_import_http http://user@host/root/dir1
python manage.py moonsheep_import_http http://user@host/root/dir1 -f *.pdf --dry-run
```

Options:
- `--host` specify host for all files/dirs specified later
- `-f` include files matching pattern
- `--dry-run` - see which files will be imported without actually importing them

## Users & authentication

Moonsheep user is a custom class substituting `auth.User` as explained here: https://docs.djangoproject.com/en/2.2/topics/auth/customizing/#substituting-a-custom-user-model

It uses email as an unique key and supports a range of authentication methods that can be configured by setting `MOONSHEEP['USER_AUTHENTICATION']` to:
- `nickname` Auto-generated pseudonymous nicknames so volunteers can follow their statistics without leaving email or creating an account 
    
   In order to setup such authentication you need to add to your project's urls an entry dedicated to choosing randomly a nickname:
   ```python
   from moonsheep.views import ChooseNicknameView

   urlpatterns = [an url
     # name needs to be set to 'choose-nickname'
     path('get-a-nickname', ChooseNicknameView.as_view(template_name='nickname.html'), name='choose-nickname'),
   ]
   ``` 
- `anonymous` Users are created on the fly and automatically logged in so we know which contributions comes from who, but we don't store any identifying information. 
