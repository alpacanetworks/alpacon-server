# Alpacon Server

Alpaca Infra Platform (AIP) aims to redesign the ways to access and manage server infrastructure. This project, `alpacon` is the API server for Alpaca Infra Platform.

This document describes the procedures to install, develop, test, and deploy `alpacon`. Please note that this README is for development environment setup, not for production.

## Installation

### Clone the source code

The source code for this project can be fetched from the main repository. We also use several submodules to import useful libraries. Please checkout them as well. For more about git submodules, you can refer to [here](https://git-scm.com/book/en/v2/Git-Tools-Submodules).

```bash
$ git clone <repository url>
$ git submodule update --init
```

Please use your username and password to access the repositories.

### Install required packages

`alpacon` is a [Django](https://www.djangoproject.com/) project, which runs on Python. Install the latest version of Python3 depending on your operating system. We also use `postgresql` as a database and `redis` as a message broker.

For Python environment isolation, it is highly recommended to use `virtualenv`. `virtualenv` lets you have separate python environments for different projects to avoid dependency collision. Install `virtualenv` via `pip`.

#### macOS

```bash
$ brew install python3 postgresql redis gettext node
$ brew services start postgresql
$ brew services start redis
$ pip3 install -U virtualenv
```

> After postgresql installation, 
 you need to have postgresql@(Your VERSION) in your $PATH  
 
 ```bash
 $ echo 'export PATH="/usr/local/opt/postgresql@(Your VERSION)/bin:$PATH"' >> ~/.zshrc
 ```

#### Ubuntu

```bash
$ sudo apt update
$ sudo apt upgrade
$ sudo apt install python3 python3-pip postgresql redis-server
```

```bash
$ sudo -HE pip3 install virtualenv
```

### Prepare database

Create a database named `alpacon` and test the connectivity.

#### Create a database

```sh
createdb alpacon
```

This will create a new database, `alpacon` using the current login user.

#### Check availability

Check the availability of the database and the user as follows.

```sh
$ psql alpacon
```

You should be able to see postgresql prompt without any erorr.

```
psql (14.3)
Type "help" for help.

alpacon=# 
```

As Django's ORM translates Python-based model classes into SQL automatically, 
you usually do not have to write SQL on your own.

#### Setup virtualenv

Go into the project directory and run the following commands.

```bash
$ cd alpacon
$ virtualenv --python=python3 env
$ source env/bin/activate
```

#### Install packages

The required packages are written in `requirements.txt`. Use `pip` to install them automatically.

```bash
(env)$ pip install -r requirements.txt
```

if `pip` fails with linking `ssl` library, you need to provide the
ssl path via `LDFLAGS` variable.

```bash
$ LDFLAGS=-L/usr/local/Cellar/openssl/1.0.2s/lib pip install -r requirements.txt
```

Install node packages.

```bash
(env)$ npm install
```

#### Configure

Copy sample settings and populate them for your purposes.

```bash
$ cp alpacon/sample_local_settings.py alpacon/local_settings.py
```

Review and adapt the variables as you need. Note that the sample settings are for development. It is not safe to use those settings in production.

Make sure you have configured following elements.

- `SECRET_KEY`: Obtain a new secret key by the following commands. Copy and paste the random string to the `local_settings.py`.

```
(env) % python
Python 3.8.13 (default, Mar 16 2022, 20:38:07) 
[Clang 13.0.0 (clang-1300.0.29.30)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> from django.core.management import utils
>>> utils.get_random_secret_key()
'ksw2etfi8%j6r0^tqb070+t8*ky3l8z$n%%6r4sf(m=1jhkuz$'
>>> 
```

- `DATABASES`: We use `postgresql`.

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'localhost',
        'NAME': 'alpacon',
    },
}
```

- `LANGUAGE_CODE`: Possible choices are `ko` and `en-us`. We use `en` for deployment.
- `TIME_ZONE`: Set the server time zone. (e.g., `Asia/Seoul`)

We suppose you are running the development server locally, `localhost:8000`. If this is not the case, you may need to adapt more configuration. (e.g., `ALLOWED_HOSTS`, `URL_PREFIX`, and `AUTH_LDAP_SERVER_URI`)

If you have completed configuration, go to the next steps to initialize the application.

#### Migrate database and populate test dataset

```bash
(env)$ python manage.py migrate
(env) $ django-admin compilemessages --ignore env
```

```bash
(env)$ python manage.py populatetestdata
```

The above command creates an admin user, `admin`, and more test users.

- `username`: `admin`
- `password`: `admin`

Also, a server instance will be created with following information, which you can use when configuring `alpamon`.

- `name`: `test`
- `id`: `7a50ea6c-2138-4d3f-9633-e50694c847c4`
- `key`: `dkfvkzk`

If you do not want to populate test dataset, you can skip the command above. In this case, `python manage.py createsuperuser` will help you creating your own test account.

### Run

Open two terminals. One for serving Web, another for the background workers.

#### Terminal 1

This command opens TCP 8000 on localhost to handle HTTP and WebSocket requests.

```bash
(env)$ python manage.py runserver
```

#### Terminal 2

This command runs background workers which affect command execution and periodic health checks.

```bash
(env)$ celery -A alpacon worker -l debug -B -Q celery,cmd,watchdog,cleanup
```

### Open a Web browser and enjoy!

```
http://localhost:8000/
```

Login with a test account, `admin`/`admin`.

The Web interface at localhost:8000 is not maintained any more. Please use `alpacon-react` front-end application. You can still use http://localhost:8000/api/ to browse API. Make sure to use different Web browsers when accessing `alpacon-server` and `alpacon-react` as session cookies cannot be shared between two apps.

## Test

### Testing API with curl

You can use curl to test API locally.

```
curl -X POST http://localhost:8000/api/.../ -H 'Content-Type: application/json' -H 'Authorization: xxxxxx' -d '{"test": 1, ...}'
```

### Testing email server

Following command launches a testing email server to receive SMTP emails sent by alpacon for testing purposes. If you are using console email backend, you don't need to run the following. The email will be printed to the console.

```sh
python -m smtpd -n -c DebuggingServer localhost:1025
```

### Testing background tasks

Make sure your redis service is running on your host. Background tasks are used to fetch latest information from external sources periodically, and to send emails without blocking user requests. You generally don't have to run celery worker unless you are testing the mentioned tasks.

```
(alpacon) $ celery -A alpacon worker -l debug -B -Q celery,cmd,watchdog,cleanup
```
