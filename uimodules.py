import tornado.web
from google.appengine.api import memcache

from config import COMMENTS_PER_PAGE
from db import get_tags, get_comments

__all__ = ['ui_modules']

class EntryModule(tornado.web.UIModule):
    def comments_count_str(self, entry_index):
        extra_comment = None
        comments_count_key = u"entry-%s-comments-count" % entry_index
        comments_count = memcache.get(comments_count_key) # read from memcache
        if comments_count is None:
            # read from db
            comments, extra_comment = get_comments(entry_index,
                batch_size=COMMENTS_PER_PAGE)
            comments_count = len(comments)  # this is no more than batch_size
            # set comments count to memcache
            if not extra_comment:
                memcache.add(comments_count_key, str(comments_count))
        if int(comments_count) == 1:
            return u"1 comment"
        elif extra_comment:
            return u"More than %s comments" % comments_count
        else:
            return u"%s comments" % comments_count

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
