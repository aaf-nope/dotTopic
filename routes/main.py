"""
routes/main.py – Main Routes (Home & Search)
==============================================
Chapter 17: Flask routes and Jinja2 rendering.
Chapter 20: Query parameters (?q=, ?feed=).

Routes:
  GET /        – Home page (random or subscribed feed)
  GET /search  – Search results page
"""

from flask import Blueprint, render_template, request
from flask_login import current_user
from sqlalchemy import func

from models import db, Post, Topic, Subscription, Moderator, LikeDislike

# Create the blueprint (no prefix – these are root-level routes)
main_bp = Blueprint('main', __name__)


# ──────────────────────────────────────────────────────────────
# HOME PAGE  (route: /)
# ──────────────────────────────────────────────────────────────

@main_bp.route('/')
def home():
    """
    Display the home page.
    - Logged out: shows a random selection of posts.
    - Logged in: defaults to subscribed feed, can toggle to random.
    """

    # Determine which feed to show (toggle via ?feed=random or ?feed=subscribed)
    feed_type = request.args.get('feed', 'subscribed')

    posts = []
    subscribed_topics = []
    created_topics = []
    moderated_topics = []

    if current_user.is_authenticated:
        # Get the list of topics this user has subscribed to (for right sidebar)
        subscribed_topics = (
            Topic.query
            .join(Subscription, Subscription.topic_id == Topic.id)
            .filter(Subscription.user_id == current_user.id)
            .all()
        )

        # Get topics created by this user
        created_topics = Topic.query.filter_by(creator_id=current_user.id).all()

        # Get topics moderated by this user (where they are not the creator)
        moderated_topics = (
            Topic.query
            .join(Moderator, Moderator.topic_id == Topic.id)
            .filter(Moderator.user_id == current_user.id)
            .all()
        )

        if feed_type == 'random' or not subscribed_topics:
            # Random feed: pick 20 random posts from the whole site
            posts = Post.query.order_by(func.random()).limit(20).all()
            feed_type = 'random'
        else:
            # Subscribed feed: show posts from topics this user follows
            topic_ids = [t.id for t in subscribed_topics]
            posts = (
                Post.query
                .filter(Post.topic_id.in_(topic_ids))
                .order_by(Post.created_at.desc())
                .limit(30)
                .all()
            )

    else:
        # Logged-out visitors always see the random feed
        posts = Post.query.order_by(func.random()).limit(20).all()
        feed_type = 'random'

    # Attach user_vote to each post for like/dislike button state
    if current_user.is_authenticated and posts:
        user_likes = {
            like.post_id: like.value
            for like in LikeDislike.query
            .filter_by(user_id=current_user.id)
            .filter(LikeDislike.post_id.in_([p.id for p in posts]))
            .all()
        }
    else:
        user_likes = {}
    for post in posts:
        post.user_vote = user_likes.get(post.id, 0)

    return render_template(
        'home.html',
        posts            = posts,
        feed_type        = feed_type,
        subscribed_topics= subscribed_topics,
        created_topics   = created_topics,
        moderated_topics = moderated_topics
    )


# ──────────────────────────────────────────────────────────────
# SEARCH PAGE  (route: /search?q=...)
# ──────────────────────────────────────────────────────────────

@main_bp.route('/search')
def search():
    """
    Search for posts and topics matching the query string.
    Splits the query into individual words and matches any word.
    Sorts results by relevance (number of matching words).
    """
    q = request.args.get('q', '').strip()

    if not q:
        return render_template('search.html', query='', matching_topics=[], matching_posts=[])

    words = q.split()

    # Build OR filters for topics
    topic_filters = []
    for word in words:
        topic_filters.append(Topic.name.ilike(f'%{word}%'))
        topic_filters.append(Topic.description.ilike(f'%{word}%'))
    
    matching_topics = Topic.query.filter(db.or_(*topic_filters)).all()

    # Build OR filters for posts
    post_filters = []
    for word in words:
        post_filters.append(Post.title.ilike(f'%{word}%'))
        post_filters.append(Post.content.ilike(f'%{word}%'))
    
    matching_posts = Post.query.filter(db.or_(*post_filters)).order_by(Post.created_at.desc()).all()

    # Relevance sorting: count how many words match in the topic/post
    matching_topics = sorted(matching_topics, key=lambda t: sum(
        1 for word in words if word.lower() in t.name.lower() or word.lower() in (t.description or '').lower()
    ), reverse=True)

    matching_posts = sorted(matching_posts, key=lambda p: sum(
        1 for word in words if word.lower() in p.title.lower() or word.lower() in (p.content or '').lower()
    ), reverse=True)

    # Attach user_vote to each matching post for like/dislike button state
    if current_user.is_authenticated and matching_posts:
        user_likes = {
            like.post_id: like.value
            for like in LikeDislike.query
            .filter_by(user_id=current_user.id)
            .filter(LikeDislike.post_id.in_([p.id for p in matching_posts]))
            .all()
        }
    else:
        user_likes = {}
    for post in matching_posts:
        post.user_vote = user_likes.get(post.id, 0)

    return render_template(
        'search.html',
        query=q,
        matching_topics=matching_topics,
        matching_posts=matching_posts
    )
