import base64
import json
import logging
import os
import secrets

from flask import Flask
from dotenv import load_dotenv
from cachelib import FileSystemCache

from . import gdoc, glab, deadlines, course


def create_app() -> Flask:
    load_dotenv('../.env')  # take environment variables from .env.

    app = Flask(__name__)

    # configuration
    # app.env = os.environ.get('FLASK_ENV', 'development')
    # app.debug = app.env == 'development'
    app.testing = os.environ.get('TESTING', False)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex())

    # logging
    if not app.debug:
        gunicorn_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)
    else:
        app.logger.setLevel(logging.DEBUG)

    # cache
    cache = FileSystemCache(
        os.environ['CACHE_DIR'],
        threshold=0,
        default_timeout=0
    )
    # api objects
    gitlab_api = glab.GitLabApi(
        base_url=os.environ['GITLAB_URL'],
        admin_token=os.environ['GITLAB_ADMIN_TOKEN'],
        course_public_repo=os.environ['GITLAB_COURSE_PUBLIC_REPO'],
        course_students_group=os.environ['GITLAB_COURSE_STUDENTS_GROUP'],
        oauth_client_id=os.environ['GITLAB_CLIENT_ID'],
        oauth_client_secret=os.environ['GITLAB_CLIENT_SECRET'],
    )
    gdoc_api = gdoc.GoogleDocAPI(
        base_url=os.environ['GDOC_URL'],
        gdoc_account=json.loads(base64.decodebytes(os.environ['GDOC_ACCOUNT'].encode())),
        public_worksheet_id=os.environ['GDOC_SPREADSHEET_ID'],
        public_scoreboard_sheet=int(os.environ['GDOC_SCOREBOARD_SHEET']),
        private_worksheet_id=os.environ['GDOC_PRIVATE_SPREADSHEET_ID'],
        private_accounts_sheet=int(os.environ['GDOC_PRIVATE_ACCOUNTS_SHEET']),
        private_review_sheet=int(os.environ['GDOC_PRIVATE_REVIEW_SHEET']),
        cache=cache,
    )
    deadlines_api = deadlines.DeadlinesAPI(cache)

    # get additional info
    registration_secret = os.environ['REGISTRATION_SECRET']
    lms_url = os.environ.get('LMS_URL', 'https://lk.yandexdataschool.ru/')
    tg_invite_link = os.environ.get('TELEGRAM_INVITE_LINK', None)

    # create course
    _course = course.Course(deadlines_api, gdoc_api, gitlab_api, registration_secret, lms_url, tg_invite_link)
    app.course = _course

    # routes
    from . import api, web
    app.register_blueprint(api.bp)
    app.register_blueprint(web.bp)

    return app
