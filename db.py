#!/usr/bin/env python

from google.appengine.ext import db
from google.appengine.api import memcache

from config import AUTHOR

__all__ = [
    'get_max_index',
    'get_entries', 'post_entry', 'update_entry',
    'get_comments', 'post_comment',
    'get_tags',
]

class MaxIndex(db.Model):
    """ index model to make searching faster and for easy paging """
    max_index = db.IntegerProperty(required=True, default=0)

class Entry(db.Model):
    """ entry model """
    index = db.IntegerProperty(required=True)
    author = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    html = db.TextProperty(required=True)
    tags = db.StringListProperty()
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

class Tag(db.Model):
    """ tag model. no need index because few """
    name = db.StringProperty(required=True)
    count = db.IntegerProperty(default=0)   # number of posts

def get_max_index(key_name):
    max_index = MaxIndex.get_by_key_name(key_name)
    if max_index is None:
        max_index = MaxIndex(key_name=key_name)
    return max_index.max_index

def get_entry(index):
    """ get an entry by index """
    entry = Entry.get_by_key_name('entries' + str(index),
        parent=db.Key.from_path('MaxIndex', 'entries'))
    return entry

def get_entries(start_index, batch_size=10, **kwargs):
    """ get entries by start index and batch size. """
    extra = None

    if kwargs and kwargs.has_key('tag'):
        tag = kwargs.pop('tag')
    else:
        tag = None

    if start_index is None:
        if tag is None:
            entries = Entry.gql(
                'ORDER BY index DESC').fetch(
                int(batch_size) + 1)
        else:
            entries = Entry.gql(
                'WHERE tags = :1 ORDER BY index DESC',
                tag).fetch(
                int(batch_size) + 1)
    else:
        start_index = int(start_index)
        if tag is None:
            entries = Entry.gql(
                'WHERE index <= :1 ORDER BY index DESC',
                int(start_index)).fetch(int(batch_size) + 1)
        else:
            entries = Entry.gql(
                'WHERE index <= :1 AND tags = :2 ORDER BY index DESC',
                int(start_index), tag).fetch(int(batch_size) + 1)
    if len(entries) > int(batch_size):
        extra = entries[-1]
        entries = entries[:int(batch_size)]
    return entries, extra

def post_entry(title, content, html, tags):
    """ create an entry """
    if tags:
        for tag in tags:
            old_tag = Tag.gql("WHERE name = :1", tag).get()
            new_tag = old_tag and old_tag or Tag(name=tag)
            new_tag.count += 1
            new_tag.put()
    def txn():
        entries_index = MaxIndex.get_by_key_name('entries')
        if entries_index is None:
            entries_index = MaxIndex(key_name='entries')
        new_index = entries_index.max_index
        entries_index.max_index += 1
        entries_index.put()
        new_entry = Entry(
            key_name='entries' + str(new_index),
            parent=entries_index,
            index=new_index,
            author=AUTHOR,
            title=title,
            content=content,
            html=html,
            tags=tags,
        )
        new_entry.put()
        return new_index
    return db.run_in_transaction(txn)

def update_entry(index, title, content, html, tags):
    """ update an entry by index. """
    entry = get_entry(index)
    entry_tags = entry.tags
    removed_entry_tags = set(entry_tags) - set(tags)
    added_entry_tags = set(tags) - set(entry_tags)
    keeped_entry_tags = set(tags).intersection(set(entry_tags))
    for tag in tags:
        old_tag = Tag.gql("WHERE name = :1", tag).get()
        new_tag = old_tag and old_tag or Tag(name=tag)
        if tag in added_entry_tags:
            new_tag.count += 1
        new_tag.put()
    for tag in removed_entry_tags:
        old_tag = Tag.gql("WHERE name = :1", tag).get()
        if old_tag:
            old_tag_count = old_tag.count
            if old_tag.count < 2:
                old_tag.delete()
            else:
                old_tag.count -= 1
                old_tag.put()
    def txn():
        entry.title = title
        entry.content = content
        entry.html = html
        entry.tags = tags
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
    def txn():
        comments_index = MaxIndex.get_by_key_name('comments')
        if comments_index is None:
            comments_index = MaxIndex(key_name='comments')
        new_index = comments_index.max_index
        comments_index.max_index += 1
        comments_index.put()
        new_comment = Comment(
            key_name='comments' + str(new_index),
            parent=comments_index,
            index=new_index,
            entry_index=int(entry_index),
            author=author,
            website=website,
            content=content,
        )
        new_comment.put()
    db.run_in_transaction(txn)
    memcache.incr(u'entry-%s-comments-count' % entry_index)

def get_tags():
    """ number of tags is few, no more than 1000. """
    tags = db.Query(Tag)
    return tags and tags or []
