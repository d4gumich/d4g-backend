# Data4Good Flask Website (Hosted on Python Anywhere), frontend on github

[![Build Status](https://travis-ci.com/d4gumich/data4good-django.svg?branch=master)](https://travis-ci.com/d4gumich/data4good-django)
![GitHub repo size](https://img.shields.io/github/repo-size/d4gumich/data4good-django.svg)
![GitHub](https://img.shields.io/github/license/d4gumich/data4good-django.svg)
![GitHub last commit](https://img.shields.io/github/last-commit/d4gumich/data4good-django.svg)
![](https://img.shields.io/badge/django-✓-blue.svg)
![](https://img.shields.io/badge/semantic_uI-✓-blue.svg)

[Website](https://www.data4good.center/)


## Project Layout
| Key Folder | Parent Folder | Description |
| - | - | - |
| d4g | d4g | Holds the settings.py and root urls | 
| home | home/templates/ | Holds the root HTML that has the style | 
| web | d4g| Holds all the templates and python files for website | 


## Development

This project is built with [Django](https://www.djangoproject.com/) and hosted on [Python Anywhere](https://www.pythonanywhere.com).


## Setup

### Django
In order to configure this project, please follow these steps:

1. Clone the repository onto your local system.
```
$ git clone https://github.com/d4gumich/data4good-django.git
```

2. Set up the virtual environment and install required packages by doing the following:

* Create a new virtual environment:
```
$ virtualenv myenv
```

* Activate the virtual environment
```
$ source myenv/bin/activate
```

* Change directories into the data4good-django directory. Verify that there are no modules installed by pip (freeze), and then do a pip install from requirements.txt. You should see the following list of modules (as of 11/17/2020):
```
(myenv) $ pip freeze
(myenv) $ pip install -r requirements.txt
(myenv) $ pip freeze

certifi==2019.11.28
chardet==3.0.4
codecov==2.0.15
coverage==5.0.3
Django==2.1.1
django-appconf==1.0.4
django-compressor==2.4
django-sass-processor==0.7.4
django-storages==1.9.1
django2-semantic-ui==1.2.2
docutils==0.15.2
idna==2.8
jmespath==0.10.0
joblib==0.17.0
libsass==0.19.4
numpy==1.19.4
pandas==1.1.4
python-dateutil==2.8.1
python-dotenv==0.14.0
pytz==2019.3
rcssmin==1.0.6
requests==2.23.0
rjsmin==1.1.0
s3transfer==0.3.3
scikit-learn==0.23.2
scipy==1.5.4
six==1.13.0
sqlparse==0.3.1
threadpoolctl==2.1.0
```
In case of error with the rjsmin and rcssmin packages, follow the solution given in this link https://github.com/django-compressor/django-compressor/issues/807

3. Start running the server and navigate to http://127.0.0.1:8000/ in your browser:
```
python manage.py runserver
```


## Deploy on PythonAnywhere
* Commit local changes to forked repository on a feature branch.
* Make a pull request to merge changes into the master branch of the upstream repo.
* Ensure automated checks pass and merge the pull request.
* Log into Python Anywhere and navigate to the console environment running data4good-virtualenv.
* Ensure you are inside the data4good-django folder and on the master branch.
* Do a 'git pull' to sync the repo with the latest merged changes on github.
* Navigate to the Web console and hit the “reload” button. 
* Navigate to the data4good.center website and refresh the page; changes should be live on the hosted website once the reloading in the Web console is complete.


## Run Locally
Just activate your virtual environment and run

```
$ source myenv/bin/activate
```

```
$ python manage.py runserver
```

## Versioning
This project uses [standard versioning](https://github.com/conventional-changelog/standard-version) to automatically update the CHANGELOG.md. Follow the instructions (with a global install) so that you can be able to use:
```
standard-version
```
to bump the version


## Troubleshooting
- https://github.com/jiansoung/issues-list/issues/13
