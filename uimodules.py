import tornado.web
from google.appengine.api import memcache

from db import get_tags, get_comments_count

__all__ = ['ui_modules']

class EntryModule(tornado.web.UIModule):
    def comments_count_str(self, entry_index):
        count, extra = get_comments_count(entry_index)
        if int(count) == 1:
            return u"1 comment"
        elif extra:
            return u"More than %s comments" % count
        else:
            return u"%s comments" % count

    def render(self, entry):
        return self.render_string("modules/entry.html", \
            entry=entry, \
            comments_count_str=self.comments_count_str(entry.index))

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
