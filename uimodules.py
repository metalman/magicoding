import tornado.web

from db import get_tags

__all__ = ['ui_modules']

class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)

class CommentModule(tornado.web.UIModule):
    def render(self, comment):
        return self.render_string("modules/comment.html", comment=comment)

class TagsModule(tornado.web.UIModule):
    def render(self):
        return self.render_string("modules/tags.html", tags=get_tags())

ui_modules={
    "Entry": EntryModule,
    "Comment": CommentModule,
    "Tags": TagsModule,
}
