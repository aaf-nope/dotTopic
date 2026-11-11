"""
models.py – dotTopic Database Models
======================================
This file defines every database table used by the application.
Each Python class here maps to one SQL table via SQLAlchemy (the ORM).

SQLAlchemy lets us work with the database using Python objects instead of
writing raw SQL. For example, User.query.filter_by(username='alice').first()
is equivalent to: SELECT * FROM user WHERE username = 'alice' LIMIT 1.

Tables defined here:
  - User         : registered accounts
  - Topic        : communities (like subreddits)
  - Subscription : which users follow which topics
  - Moderator    : which users moderate which topics
  - Post         : text/media posts inside topics
  - PostMedia    : images or videos attached to a post
  - Comment      : replies to posts (supports 2-level nesting)
  - LikeDislike  : vote records (like/dislike) for posts and comments
  - Tag          : labels that belong to a topic, applied to posts
  - BannedUser   : records of users banned from specific topics
  - post_tags    : junction table linking posts to tags (many-to-many)
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# The shared db object – created here, attached to the Flask app in app.py.
# All models use db.Column, db.relationship, etc. from this object.
db = SQLAlchemy()


# ══════════════════════════════════════════════════════════════
# JUNCTION TABLE: Post ↔ Tag  (many-to-many relationship)
# A post can have multiple tags, and a tag can be on multiple posts.
# SQLAlchemy handles this automatically via the 'secondary' parameter
# on the Post.tags relationship below.
# ══════════════════════════════════════════════════════════════

post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id',  db.Integer, db.ForeignKey('tag.id'),  primary_key=True)
)


# ══════════════════════════════════════════════════════════════
# USER MODEL
# Represents a registered account. UserMixin adds the is_authenticated,
# is_active, and get_id() helpers required by Flask-Login.
# ══════════════════════════════════════════════════════════════

class User(UserMixin, db.Model):
    """
    A registered user account.

    Fields:
      id            – unique auto-incrementing integer primary key
      username      – unique display name (max 80 chars)
      email         – unique email address (used for login)
      password_hash – Werkzeug-hashed password (never store plaintext)
      profile_pic   – filename relative to /static/ (always has a default)
      created_at    – when the account was created
      is_super_admin – True only for the site owner account
    """
    __tablename__ = 'user'

    id            = db.Column(db.Integer,     primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_pic   = db.Column(db.String(256), default='default_pfp.png')  # always valid
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)
    is_super_admin = db.Column(db.Boolean,   default=False)

    def __init__(self, **kwargs):
        """Standard SQLAlchemy init – passes keyword arguments to the parent."""
        super().__init__(**kwargs)

    # ── Relationships ──────────────────────────────────────────
    # 'cascade=all, delete-orphan' means: if this user is deleted,
    # all their posts, comments, etc. are also deleted automatically.

    posts         = db.relationship('Post',         backref='author', lazy=True,
                                    cascade='all, delete-orphan')
    comments      = db.relationship('Comment',      backref='author', lazy=True,
                                    cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='user',   lazy=True,
                                    cascade='all, delete-orphan')
    moderated     = db.relationship('Moderator',    backref='user',   lazy=True,
                                    cascade='all, delete-orphan')
    likes         = db.relationship('LikeDislike',  backref='user',   lazy=True,
                                    cascade='all, delete-orphan')

    # ── Password helpers ───────────────────────────────────────

    def set_password(self, password):
        """
        Hash the plaintext password with Werkzeug and store the hash.
        Called during registration and when a user changes their password.
        Never store plaintext passwords – always use this method.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Return True if the provided plaintext password matches the stored hash.
        Called during login to verify credentials.
        """
        return check_password_hash(self.password_hash, password)

    # ── Permission helpers ─────────────────────────────────────

    def is_subscribed_to(self, topic):
        """Return True if this user has a Subscription record for the given topic."""
        return Subscription.query.filter_by(
            user_id=self.id, topic_id=topic.id
        ).first() is not None

    def is_moderator_of(self, topic):
        """Return True if there is a Moderator record linking this user to the topic."""
        return Moderator.query.filter_by(
            user_id=self.id, topic_id=topic.id
        ).first() is not None

    def is_banned_from(self, topic):
        """Return True if there is a BannedUser record for this user in the topic."""
        return BannedUser.query.filter_by(
            user_id=self.id, topic_id=topic.id
        ).first() is not None

    def can_moderate(self, topic):
        """
        Return True if this user has moderation power in the given topic.
        This is True if the user is any of:
          - the topic's creator
          - an assigned moderator
          - the site super-admin
        Used by both route handlers and the API to gate privileged actions.
        """
        return (
            self.id == topic.creator_id
            or self.is_moderator_of(topic)
            or self.is_super_admin
        )

    def __repr__(self):
        return f'<User {self.username}>'


# ══════════════════════════════════════════════════════════════
# TOPIC MODEL
# A topic is a community (similar to a subreddit). It has a creator,
# optional moderators, and a collection of posts. Topics have a photo
# (icon) and a banner image shown at the top of the topic page.
# ══════════════════════════════════════════════════════════════

class Topic(db.Model):
    """
    A community / forum category.

    Fields:
      id          – unique integer primary key
      name        – URL-safe name, e.g. 'gaming' (unique, lowercase)
      description – short text shown on the topic page
      photo       – icon image filename in /static/ (always has a default)
      banner      – banner image filename in /static/ (always has a default)
      creator_id  – FK to user.id – the user who created this topic
      created_at  – when the topic was created
    """
    __tablename__ = 'topic'

    id          = db.Column(db.Integer,     primary_key=True)
    name        = db.Column(db.String(50),  unique=True, nullable=False)
    description = db.Column(db.Text)
    photo       = db.Column(db.String(256), default='default_topic.png')   # topic icon
    banner      = db.Column(db.String(256), default='default_banner.png')  # header banner
    creator_id  = db.Column(db.Integer,     db.ForeignKey('user.id'), nullable=False)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)

    def __init__(self, **kwargs):
        """Standard SQLAlchemy init."""
        super().__init__(**kwargs)

    # ── Relationships ──────────────────────────────────────────
    creator       = db.relationship('User',         foreign_keys=[creator_id])
    posts         = db.relationship('Post',         backref='topic', lazy=True,
                                    cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='topic', lazy=True,
                                    cascade='all, delete-orphan')
    moderators    = db.relationship('Moderator',    backref='topic', lazy=True,
                                    cascade='all, delete-orphan')
    tags          = db.relationship('Tag',          backref='topic', lazy=True,
                                    cascade='all, delete-orphan')
    banned_users  = db.relationship('BannedUser',   backref='topic', lazy=True,
                                    cascade='all, delete-orphan')

    @property
    def subscriber_count(self):
        """Return the number of users currently subscribed to this topic."""
        return Subscription.query.filter_by(topic_id=self.id).count()

    def __repr__(self):
        return f'<Topic .{self.name}>'


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION MODEL  (User ↔ Topic)
# Records that a user is following a topic. The home page uses
# subscriptions to build the "subscribed feed".
# ══════════════════════════════════════════════════════════════

class Subscription(db.Model):
    """
    A record that a user has subscribed to a topic.
    One row = one user following one topic.
    """
    __tablename__ = 'subscription'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'),  nullable=False)
    topic_id   = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# ══════════════════════════════════════════════════════════════
# MODERATOR MODEL  (User ↔ Topic)
# Records that a user has been promoted to moderator of a topic.
# A topic creator can promote any subscriber to moderator.
# Moderators can pin/delete posts, ban users, and manage tags.
# ══════════════════════════════════════════════════════════════

class Moderator(db.Model):
    """
    A record that a user is a moderator of a topic.
    One row = one user moderating one topic.
    Distinct from topic.creator_id – the creator always has mod powers,
    but is not stored in this table.
    """
    __tablename__ = 'moderator'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'),  nullable=False)
    topic_id   = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# ══════════════════════════════════════════════════════════════
# POST MODEL
# A post belongs to one topic and one user (author).
# Posts can be pinned (shown at top), have attached media, and be tagged.
# ══════════════════════════════════════════════════════════════

class Post(db.Model):
    """
    A post inside a topic.

    Fields:
      id         – unique integer primary key
      title      – required post title (max 200 chars)
      content    – optional body text
      topic_id   – FK to topic.id
      user_id    – FK to user.id (the author)
      is_pinned  – True if a moderator has pinned this post to the top
      created_at – creation timestamp
      updated_at – auto-updated timestamp when the post is edited
    """
    __tablename__ = 'post'

    id         = db.Column(db.Integer,      primary_key=True)
    title      = db.Column(db.String(200),  nullable=False)
    content    = db.Column(db.Text)
    topic_id   = db.Column(db.Integer,      db.ForeignKey('topic.id'), nullable=False)
    user_id    = db.Column(db.Integer,      db.ForeignKey('user.id'),  nullable=False)
    is_pinned  = db.Column(db.Boolean,      default=False)
    created_at = db.Column(db.DateTime,     default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,     onupdate=datetime.utcnow)  # auto-set on edit

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ── Relationships ──────────────────────────────────────────
    comments = db.relationship('Comment',     backref='post', lazy=True,
                               cascade='all, delete-orphan')
    media    = db.relationship('PostMedia',   backref='post', lazy=True,
                               cascade='all, delete-orphan')
    likes    = db.relationship('LikeDislike', backref='post', lazy=True,
                               foreign_keys='LikeDislike.post_id',
                               cascade='all, delete-orphan')
    # Many-to-many with Tag via the post_tags junction table
    tags     = db.relationship('Tag', secondary=post_tags, lazy='subquery',
                               backref=db.backref('posts', lazy=True))

    # ── Computed properties ───────────────────────────────────
    # These are read-only Python properties that run a DB query each time
    # they are accessed. Used in templates like {{ post.like_count }}.

    @property
    def like_count(self):
        """Count how many users have liked this post (+1 votes)."""
        return LikeDislike.query.filter_by(post_id=self.id, value=1).count()

    @property
    def dislike_count(self):
        """Count how many users have disliked this post (-1 votes)."""
        return LikeDislike.query.filter_by(post_id=self.id, value=-1).count()

    @property
    def comment_count(self):
        """Count top-level comments only (replies are not counted separately)."""
        return Comment.query.filter_by(post_id=self.id, parent_id=None).count()

    def __repr__(self):
        return f'<Post {self.title[:30]}>'


# ══════════════════════════════════════════════════════════════
# POST MEDIA MODEL  (images/videos attached to a post)
# Each PostMedia row is one uploaded file linked to a post.
# The file is stored on disk under static/uploads/post_media/.
# ══════════════════════════════════════════════════════════════

class PostMedia(db.Model):
    """
    An image or video attached to a post.

    Fields:
      id        – unique integer primary key
      post_id   – FK to post.id
      file_path – relative path from /static/ (e.g. 'uploads/post_media/abc.jpg')
      alt_text  – accessibility text (auto-filled from filename)
      file_type – 'image' or 'video', used to render the correct HTML tag
    """
    __tablename__ = 'post_media'

    id        = db.Column(db.Integer,     primary_key=True)
    post_id   = db.Column(db.Integer,     db.ForeignKey('post.id'), nullable=False)
    file_path = db.Column(db.String(256), nullable=False)
    alt_text  = db.Column(db.String(200), default='')
    file_type = db.Column(db.String(10),  default='image')  # 'image' or 'video'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f'<PostMedia {self.file_path}>'


# ══════════════════════════════════════════════════════════════
# COMMENT MODEL  (supports 2-level threading via parent_id)
# Comments with parent_id=None are top-level comments on a post.
# Comments with a parent_id are replies to another comment.
# Maximum reply depth is 2 (reply-to-reply is not allowed).
# ══════════════════════════════════════════════════════════════

class Comment(db.Model):
    """
    A comment or reply on a post.

    Fields:
      id         – unique integer primary key
      content    – the comment text
      post_id    – FK to post.id (which post this comment is on)
      user_id    – FK to user.id (the author)
      parent_id  – FK to comment.id; None for top-level, set for replies
      is_pinned  – True if a moderator pinned this comment to the top
      created_at – creation timestamp

    Threading:
      The 'replies' relationship lets you do comment.replies to get all
      direct replies to a comment. Templates iterate this to show threads.
    """
    __tablename__ = 'comment'

    id         = db.Column(db.Integer,  primary_key=True)
    content    = db.Column(db.Text,     nullable=False)
    post_id    = db.Column(db.Integer,  db.ForeignKey('post.id'),    nullable=False)
    user_id    = db.Column(db.Integer,  db.ForeignKey('user.id'),    nullable=False)
    parent_id  = db.Column(db.Integer,  db.ForeignKey('comment.id'), nullable=True)
    is_pinned  = db.Column(db.Boolean,  default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # Self-referential: a Comment can have child Comments (replies)
    replies = db.relationship(
        'Comment',
        backref=db.backref('parent', remote_side='Comment.id'),
        lazy=True,
        cascade='all, delete-orphan'
    )

    # LikeDislike records for this comment
    likes = db.relationship('LikeDislike', backref='comment', lazy=True,
                            foreign_keys='LikeDislike.comment_id',
                            cascade='all, delete-orphan')

    @property
    def like_count(self):
        """Count +1 votes on this comment."""
        return LikeDislike.query.filter_by(comment_id=self.id, value=1).count()

    @property
    def dislike_count(self):
        """Count -1 votes on this comment."""
        return LikeDislike.query.filter_by(comment_id=self.id, value=-1).count()

    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'


# ══════════════════════════════════════════════════════════════
# LIKE/DISLIKE MODEL
# One row = one vote by one user on one post OR one comment.
# post_id and comment_id are mutually exclusive: exactly one is set,
# the other is NULL. value is +1 for like, -1 for dislike.
# ══════════════════════════════════════════════════════════════

class LikeDislike(db.Model):
    """
    A single like or dislike vote by a user.

    Either post_id or comment_id is set (never both, never neither).
    value: +1 = like, -1 = dislike.

    The API route for voting checks if a record already exists:
    - Same value again → delete the row (toggle off)
    - Opposite value  → update the row (change vote)
    - No row yet      → insert a new row
    """
    __tablename__ = 'like_dislike'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'),    nullable=False)
    post_id    = db.Column(db.Integer, db.ForeignKey('post.id'),    nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    value      = db.Column(db.Integer, nullable=False)  # +1 or -1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# ══════════════════════════════════════════════════════════════
# TAG MODEL
# Tags belong to a specific topic and can be applied to posts
# in that topic. Example: the 'gaming' topic has tags like
# 'Review', 'Discussion', 'Indie'. Stored in the post_tags table.
# ══════════════════════════════════════════════════════════════

class Tag(db.Model):
    """
    A label that belongs to one topic and can be applied to posts.

    Fields:
      id       – unique integer primary key
      name     – display label, e.g. 'Review' (max 30 chars)
      topic_id – FK to topic.id (tags are scoped to one topic)

    Tags are linked to posts via the post_tags junction table (many-to-many).
    """
    __tablename__ = 'tag'

    id       = db.Column(db.Integer,    primary_key=True)
    name     = db.Column(db.String(30), nullable=False)
    topic_id = db.Column(db.Integer,    db.ForeignKey('topic.id'), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self):
        return f'<Tag {self.name}>'


# ══════════════════════════════════════════════════════════════
# BANNED USER MODEL  (user banned from a specific topic)
# A moderator can ban a user from their topic. The banned user can
# still read the topic but cannot post, comment, or like.
# ══════════════════════════════════════════════════════════════

class BannedUser(db.Model):
    """
    A record that a user is banned from a specific topic.

    Fields:
      id         – unique integer primary key
      user_id    – FK to user.id (the user who was banned)
      topic_id   – FK to topic.id (the topic they are banned from)
      banned_by  – FK to user.id (which moderator issued the ban)
      created_at – when the ban was issued
    """
    __tablename__ = 'banned_user'

    id         = db.Column(db.Integer,  primary_key=True)
    user_id    = db.Column(db.Integer,  db.ForeignKey('user.id'),  nullable=False)
    topic_id   = db.Column(db.Integer,  db.ForeignKey('topic.id'), nullable=False)
    banned_by  = db.Column(db.Integer,  db.ForeignKey('user.id'),  nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # Expose the banned user's User object so templates can use banned_user.user.username
    user = db.relationship('User', foreign_keys=[user_id])
