#!/usr/bin/env python

import markdown
import functools
import os.path
import tornado.web
import tornado.escape

from google.appengine.api import users

from lib import htmlconverter
import config, db

__all__ = ['handlers']


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
        entries, extra = db.get_entries(start, config.POSTS_PER_PAGE)
        self.render("home.html", entries=entries, extra=extra)


class EntryHandler(BaseHandler):
    def get(self, index):
        entry = db.get_entry(index)
        if not entry: raise tornado.web.HTTPError(404)
        # XXX maybe should do comments paging with ajax
        comment_start = self.get_argument("comment_start", None)
        comments, comment_extra = db.get_comments(index,
            comment_start, config.COMMENTS_PER_PAGE)
        self.render("entry.html",
            entry=entry, comments=comments, comment_extra=comment_extra)


class ArchiveHandler(BaseHandler):
    def get(self):
        start = self.get_argument("start", None)
        entries, extra = db.get_entries(start, config.POSTS_PER_ARCHIVE)
        self.render("archive.html", entries=entries, extra=extra)


class TagHandler(BaseHandler):
    def get(self, tag):
        start = self.get_argument("start", None)
        tag = tornado.escape.url_unescape(tag)
        entries, extra = db.get_entries(start, config.POSTS_PER_PAGE, tag=tag)
        if not entries: raise tornado.web.HTTPError(404)
        self.render("home.html", entries=entries, extra=extra)


class FeedHandler(BaseHandler):
    def get(self):
        start = self.get_argument("start", None)
        entries, extra = db.get_entries(start, config.POSTS_IN_FEED)
        self.set_header("Content-Type", "application/atom+xml")
        self.render("feed.xml", entries=entries)


class ComposeHandler(BaseHandler):
    @administrator
    def get(self):
        index = self.get_argument("index", None)
        entry = db.get_entry(index) if index else None
        tags = db.get_tags()
        tags = tags and " ".join([t.name for t in tags]) or ""
        self.render("compose.html", entry=entry, tags=tags)

    @administrator
    def post(self):
        index = self.get_argument("index", None)
        tags = self.get_argument("tags", None)
        tags = tags and [t for t in set(tags.lower().split())] or []
        if index:
            # edit an entry
            db.update_entry(
                index=index,
                title=self.get_argument("title"),
                content=self.get_argument("content"),
                html=markdown.markdown(self.get_argument("content")),
                tags=tags,
            )
        else:
            # create an entry
            index = db.post_entry(
                title=self.get_argument("title"),
                content=self.get_argument("content"),
                html=markdown.markdown(self.get_argument("content")),
                tags=tags,
            )
        self.redirect("/entry/" + str(index))


class CommentHandler(BaseHandler):
    def post(self):
        entry_index = self.get_argument("entry_index")
        website=self.get_argument("website", "")
        if website:
            website = tornado.escape.url_escape(website)
            if not website.startswith("http://") or not website.startswith("https://"):
                website = u"http://" + website
        content = self.get_argument("content")
        if not isinstance(content, unicode):
            content = unicode(content, 'utf-8')
        if len(content) > 1000: raise tornado.web.HTTPError(404)
        content=unicode(htmlconverter.webtext2html(content), 'utf-8')
        db.post_comment(
            entry_index=entry_index,
            author=self.get_argument("author"),
            website=website,
            content=content,
        )
        self.redirect("/entry/" + str(entry_index) + '#comment')


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


handlers = [
    (r"/", HomeHandler),
    (r"/archive", ArchiveHandler),
    (r"/tag/([^/]+)", TagHandler),
    (r"/feed", FeedHandler),
    (r"/entry/([^/]+)", EntryHandler),
    (r"/compose", ComposeHandler),
    (r"/comment", CommentHandler),
    (r"/about", AboutHandler),
]
