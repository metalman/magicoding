############################
# blog configure
############################
from os.path import join, dirname

APP_TITLE = u"Magic coding!"
AUTHOR = u'zhangkaizhao'
AUTHOR_EMAIL = u'zhangkaizhao@gmail.com'

# cookie_secret:
#import hashlib
#cookie_secret = hashlib.sha1("zhangkaizhao").hexdigest()
cookie_secret="5e4b388cec80152c7bb967fb5b63ba62750a13a0"

TEMPLATE_PATH = join(dirname(__file__), "templates")

POSTS_PER_PAGE = 10
POSTS_PER_ARCHIVE = 20
POSTS_IN_FEED = 10
COMMENTS_PER_PAGE = 40

DISABLE_COMMENT = True
