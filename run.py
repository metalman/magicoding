#!/usr/bin/env python

import tornado.wsgi
import wsgiref.handlers

import config
from handlers import handlers
from uimodules import ui_modules


settings = {
    "app_title": config.APP_TITLE,
    "author": config.AUTHOR,
    "template_path": config.TEMPLATE_PATH,
    "cookie_secret": config.cookie_secret,
    "xsrf_cookies": True,
    "autoescape": None,
    "ui_modules": ui_modules,
    "disable_comment": config.DISABLE_COMMENT,
}
application = tornado.wsgi.WSGIApplication(handlers, **settings)


if __name__ == "__main__":
    wsgiref.handlers.CGIHandler().run(application)
