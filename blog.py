#!/usr/bin/env python

import markdown
import functools
import os.path
import tornado.web
import tornado.wsgi
import wsgiref.handlers

from google.appengine.api import users
from google.appengine.ext import db

from lib import htmlconverter

AUTHOR = u'metalman' # or get administrator's nickname from google account
                     # in a request handler: self.current_user.nickname()
POSTS_PER_PAGE = 2
POSTS_PER_ARCHIVE = 3
POSTS_IN_FEED = 10
COMMENTS_PER_PAGE = 2

class BlogIndex(db.Model):
    """ index model for entry model to make faster and for easy paging """
    max_index = db.IntegerProperty(required=True, default=0)

class CommentIndex(db.Model):
    """ index model for coment model to make faster """
    max_index = db.IntegerProperty(required=True, default=0)

class BlogEntry(db.Model):
    """ entry model """
    index = db.IntegerProperty(required=True)
    author = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    html = db.TextProperty(required=True)
    published = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)

class Comment(db.Model):
    """ comment model """
    index = db.IntegerProperty(required=True)
    entry_index = db.IntegerProperty(required=True)
    author = db.StringProperty(required=True)
    website = db.StringProperty()
    content = db.TextProperty(required=True)
    published = db.DateTimeProperty(auto_now_add=True)

def get_entry(index):
    """ get an entry by index """
    # give another param AUTHOR if in multi author
    entry = BlogEntry.get_by_key_name(AUTHOR + str(index),
        parent=db.Key.from_path('BlogIndex', AUTHOR))
    return entry

def get_entries(start_index, batch_size=10):
    """ get entries by start index and batch size. """
    extra = None
    if start_index is None:
        entries = BlogEntry.gql(
            'ORDER BY index DESC').fetch(
            int(batch_size) + 1)
    else:
        start_index = int(start_index)
        entries = BlogEntry.gql(
            'WHERE index <= :1 ORDER BY index DESC',
            int(start_index)).fetch(int(batch_size) + 1)
    if len(entries) > int(batch_size):
        extra = entries[-1]
        entries = entries[:int(batch_size)]
    return entries, extra

def post_entry(title, content, html):
    """ create an entry """
    # give another param AUTHOR if in multi author
    def txn():
        blog_index = BlogIndex.get_by_key_name(AUTHOR)
        if blog_index is None:
            blog_index = BlogIndex(key_name=AUTHOR)
        new_index = blog_index.max_index
        blog_index.max_index += 1
        blog_index.put()
        new_entry = BlogEntry(
            key_name=AUTHOR + str(new_index),
            parent=blog_index,
            index=new_index,
            author=AUTHOR,
            title=title,
            content=content,
            html=html,
        )
        new_entry.put()
        return new_index
    return db.run_in_transaction(txn)

def update_entry(index, title, content, html):
    """ update an entry by index. """
    entry = get_entry(index)
    def txn():
        entry.title = title
        entry.content = content
        entry.html = html
        entry.put()
    db.run_in_transaction(txn)

def get_comments(entry_index=None, start_index=None, batch_size=40):
    """ get comments """
    extra = None
    if entry_index is None:
        comments = Comment.gql(
            'ORDER BY index DESC').fetch(
            int(batch_size) + 1)
    elif start_index is None:
        comments = Comment.gql(
            'WHERE entry_index = :1 ORDER BY index DESC',
            int(entry_index)).fetch(
            int(batch_size) + 1)
    else:
        start_index = int(start_index)
        comments = Comment.gql(
            'WHERE entry_index = :1 AND index <= :2 ORDER BY index DESC',
            int(entry_index), int(start_index)).fetch(int(batch_size) + 1)
    if len(comments) > int(batch_size):
        extra = comments[-1]
        comments = comments[:int(batch_size)]
    return comments, extra

def post_comment(entry_index, author, website, content):
    """ create an comment """
    # give another param AUTHOR if in multi author
    def txn():
        comment_index = CommentIndex.get_by_key_name(AUTHOR)
        if comment_index is None:
            comment_index = CommentIndex(key_name=AUTHOR)
        new_index = comment_index.max_index
        comment_index.max_index += 1
        comment_index.put()
        new_comment = Comment(
            key_name=AUTHOR + str(new_index),
            parent=comment_index,
            index=new_index,
            entry_index=int(entry_index),
            author=author,
            website=website,
            content=content,
        )
        new_comment.put()
    db.run_in_transaction(txn)

def administrator(method):
    """Decorate with this method to restrict to site admins."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.request.method == "GET":
                self.redirect(self.get_login_url())
                return
            raise tornado.web.HTTPError(403)
        elif not self.current_user.administrator:
            if self.request.method == "GET":
                self.redirect("/")
                return
            raise tornado.web.HTTPError(403)
        else:
            return method(self, *args, **kwargs)
    return wrapper


class BaseHandler(tornado.web.RequestHandler):
    """Implements Google Accounts authentication methods."""
    def get_current_user(self):
        user = users.get_current_user()
        if user: user.administrator = users.is_current_user_admin()
        return user

    def get_login_url(self):
        return users.create_login_url(self.request.uri)

    def render_string(self, template_name, **kwargs):
        # Let the templates access the users module to generate login URLs
        return tornado.web.RequestHandler.render_string(
            self, template_name, users=users, **kwargs)


class HomeHandler(BaseHandler):
    def get(self):
        start = self.get_argument("start", None)
        entries, extra = get_entries(start, POSTS_PER_PAGE)
        self.render("home.html", entries=entries, extra=extra)


class EntryHandler(BaseHandler):
    def get(self, index):
        entry = get_entry(index)
        if not entry: raise tornado.web.HTTPError(404)
        # XXX maybe should do comments paging with ajax
        comment_start = self.get_argument("comment_start", None)
        comments, comment_extra = get_comments(index,
            comment_start, COMMENTS_PER_PAGE)
        self.render("entry.html",
            entry=entry, comments=comments, comment_extra=comment_extra)


class ArchiveHandler(BaseHandler):
    def get(self):
        start = self.get_argument("start", None)
        entries, extra = get_entries(start, POSTS_PER_ARCHIVE)
        self.render("archive.html", entries=entries, extra=extra)


class FeedHandler(BaseHandler):
    def get(self):
        start = self.get_argument("start", None)
        entries, extra = get_entries(start, POSTS_IN_FEED)
        self.set_header("Content-Type", "application/atom+xml")
        self.render("feed.xml", entries=entries)


class ComposeHandler(BaseHandler):
    @administrator
    def get(self):
        index = self.get_argument("index", None)
        entry = get_entry(index) if index else None
        self.render("compose.html", entry=entry)

    @administrator
    def post(self):
        index = self.get_argument("index", None)
        if index:
            # edit an entry
            update_entry(
                index=index,
                title=self.get_argument("title"),
                content=self.get_argument("content"),
                html=markdown.markdown(self.get_argument("content")),
            )
        else:
            # create an entry
            index = post_entry(
                title=self.get_argument("title"),
                content=self.get_argument("content"),
                html=markdown.markdown(self.get_argument("content")),
            )
        self.redirect("/entry/" + str(index))

class CommentHandler(BaseHandler):
    def post(self):
        entry_index = self.get_argument("entry_index")
        content=htmlconverter.webtext2html(self.get_argument("content"))
        if not isinstance(content, unicode):
            content = unicode(content)
        post_comment(
            entry_index=entry_index,
            author=self.get_argument("author"),
            website=self.get_argument("website", ""),
            content=content,
        )
        self.redirect("/entry/" + str(entry_index))

class AboutHandler(BaseHandler):
    def get(self):
        self.render("about.html", markdown=self.markdown)

    def markdown(self, path, toc=False):
        if not hasattr(AboutHandler, "_md"):
            AboutHandler._md = {}
        if path not in AboutHandler._md:
            full_path = os.path.join(self.settings["template_path"], path)
            f = open(full_path, "r")
            contents = f.read().decode("utf-8")
            f.close()
            if toc: contents = u"[TOC]\n\n" + contents
            md = markdown.Markdown(extensions=["toc"] if toc else [])
            AboutHandler._md[path] = md.convert(contents).encode("utf-8")
        return AboutHandler._md[path]

class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)

class CommentModule(tornado.web.UIModule):
    def render(self, comment):
        return self.render_string("modules/comment.html", comment=comment)


settings = {
    "blog_title": u"metalman's blog",
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "ui_modules": {"Entry": EntryModule, "Comment": CommentModule},
    "xsrf_cookies": True,
}
application = tornado.wsgi.WSGIApplication([
    (r"/", HomeHandler),
    (r"/archive", ArchiveHandler),
    (r"/feed", FeedHandler),
    (r"/entry/([^/]+)", EntryHandler),
    (r"/compose", ComposeHandler),
    (r"/comment", CommentHandler),
    (r"/about", AboutHandler),
], **settings)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
    main()
