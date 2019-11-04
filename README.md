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