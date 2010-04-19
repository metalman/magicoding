#!/usr/bin/env python

import tornado.wsgi
import wsgiref.handlers

import config
from handlers import handlers
from uimodules import ui_modules


settings = {
    "blog_title": config.BLOG_TITLE,
    "template_path": config.TEMPLATE_PATH,
    "cookie_secret": config.cookie_secret,
    "xsrf_cookies": True,
    "ui_modules": ui_modules,
}
application = tornado.wsgi.WSGIApplication(handlers, **settings)


if __name__ == "__main__":
    wsgiref.handlers.CGIHandler().run(application)
