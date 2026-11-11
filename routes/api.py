"""
routes/api.py – REST API Endpoints
=====================================
All routes in this file return JSON (not HTML). They are called from the
frontend via jQuery $.ajax() so the page can update without a full reload.

All routes require the user to be logged in (@login_required), unless stated.
Permission errors return HTTP 403. Validation errors return HTTP 400.

Endpoint summary:
  POST   /api/topic/<id>/subscribe         – Subscribe or unsubscribe
  POST   /api/post/<id>/like               – Like or dislike a post
  DELETE /api/post/<id>/media/<media_id>   – Delete an uploaded media file
  POST   /api/comment/<id>/like            – Like or dislike a comment
  POST   /api/post/<id>/comment            – Add a top-level comment
  POST   /api/comment/<id>/reply           – Add a reply to a comment
  PUT    /api/comment/<id>                 – Edit a comment
  DELETE /api/post/<id>                    – Delete a post
  DELETE /api/comment/<id>                 – Delete a comment
  POST   /api/post/<id>/pin               – Toggle pin on a post
  POST   /api/comment/<id>/pin            – Toggle pin on a comment
  POST   /api/topic/<id>/ban              – Ban or unban a user from a topic
  POST   /api/topic/<id>/mod              – Promote or demote a moderator
  POST   /api/topic/<id>/tags             – Create a tag for a topic
  DELETE /api/topic/<id>/tags/<tag_id>    – Delete a tag from a topic
  DELETE /api/topic/<id>/delete           – Delete an entire topic
"""

from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user

from models import (
    db, Post, Comment, Topic, LikeDislike,
    Subscription, Moderator, BannedUser, User
)

# Create the blueprint (all routes prefixed with /api)
api_bp = Blueprint('api', __name__, url_prefix='/api')


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION
# ══════════════════════════════════════════════════════════════

@api_bp.route('/topic/<int:topic_id>/subscribe', methods=['POST'])
@login_required
def toggle_subscribe(topic_id):
    """
    Toggle subscription to a topic.
    If already subscribed → unsubscribe.
    If not subscribed → subscribe.
    Returns JSON with the new status.
    """

    topic = Topic.query.get_or_404(topic_id)

    # Banned users can only unsubscribe (not subscribe)
    if current_user.is_banned_from(topic):
        existing = Subscription.query.filter_by(
            user_id=current_user.id, topic_id=topic_id
        ).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({
                'status'          : 'unsubscribed',
                'subscriber_count': topic.subscriber_count
            })
        else:
            return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403

    # Topic creator cannot unsubscribe from their own topic
    if topic.creator_id == current_user.id:
        return jsonify({'status': 'error', 'message': 'Creators cannot leave their own topic.'}), 400

    existing = Subscription.query.filter_by(
        user_id=current_user.id, topic_id=topic_id
    ).first()

    if existing:
        # Already subscribed → unsubscribe
        db.session.delete(existing)
        db.session.commit()
        return jsonify({
            'status'          : 'unsubscribed',
            'subscriber_count': topic.subscriber_count
        })
    else:
        # Not subscribed → subscribe
        sub = Subscription(user_id=current_user.id, topic_id=topic_id)
        db.session.add(sub)
        db.session.commit()
        return jsonify({
            'status'          : 'subscribed',
            'subscriber_count': topic.subscriber_count
        })


# ══════════════════════════════════════════════════════════════
# LIKE / DISLIKE – POSTS
# ══════════════════════════════════════════════════════════════

@api_bp.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    """
    Like or dislike a post.
    Request body (JSON): { "value": 1 }  for like, or { "value": -1 } for dislike.
    If the user already has the same vote → remove it (toggle off).
    If the user has the opposite vote → change it.
    """

    post  = Post.query.get_or_404(post_id)
    topic = Topic.query.get(post.topic_id)
    
    if current_user.is_banned_from(topic):
        return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403
        
    data  = request.get_json() or {}
    value = data.get('value', 1)   # 1 = like, -1 = dislike

    if value not in (1, -1):
        return jsonify({'status': 'error', 'message': 'Invalid value.'}), 400

    existing = LikeDislike.query.filter_by(
        user_id=current_user.id, post_id=post_id
    ).first()

    if existing:
        if existing.value == value:
            # Same vote → remove (toggle off)
            db.session.delete(existing)
            user_vote = 0
        else:
            # Opposite vote → change
            existing.value = value
            user_vote = value
    else:
        # No previous vote → create new
        new_like = LikeDislike(user_id=current_user.id, post_id=post_id, value=value)
        db.session.add(new_like)
        user_vote = value

    db.session.commit()

    return jsonify({
        'status'       : 'success',
        'likes_count'  : post.like_count,
        'dislikes_count': post.dislike_count,
        'user_vote'    : user_vote
    })

# ══════════════════════════════════════════════════════════════
# DELETE MEDIA
# ══════════════════════════════════════════════════════════════

@api_bp.route('/post/<int:post_id>/media/<int:media_id>', methods=['DELETE'])
@login_required
def delete_post_media(post_id, media_id):
    """
    DELETE /api/post/<post_id>/media/<media_id>
    Delete a single uploaded media file from a post.
    Removes the file from disk and the PostMedia record from the database.
    Only the post author or a super admin can do this.
    """
    import os
    from flask import current_app
    from models import PostMedia
    
    post = Post.query.get_or_404(post_id)
    # Only author or super admin
    if post.user_id != current_user.id and not current_user.is_super_admin:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    media = PostMedia.query.filter_by(id=media_id, post_id=post_id).first()
    if not media:
        return jsonify({'status': 'error', 'message': 'Media not found'}), 404

    # Remove file from disk
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], media.file_path.replace('uploads/', ''))
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(media)
    db.session.commit()

    return jsonify({'status': 'success'})


# ══════════════════════════════════════════════════════════════
# LIKE / DISLIKE – COMMENTS
# ══════════════════════════════════════════════════════════════

@api_bp.route('/comment/<int:comment_id>/like', methods=['POST'])
@login_required
def like_comment(comment_id):
    """Like or dislike a comment. Same toggle logic as post likes."""

    comment = Comment.query.get_or_404(comment_id)
    post    = Post.query.get(comment.post_id)
    topic   = Topic.query.get(post.topic_id)
    
    if current_user.is_banned_from(topic):
        return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403
        
    data    = request.get_json() or {}
    value   = data.get('value', 1)

    if value not in (1, -1):
        return jsonify({'status': 'error', 'message': 'Invalid value.'}), 400

    existing = LikeDislike.query.filter_by(
        user_id=current_user.id, comment_id=comment_id
    ).first()

    if existing:
        if existing.value == value:
            db.session.delete(existing)
            user_vote = 0
        else:
            existing.value = value
            user_vote = value
    else:
        new_like = LikeDislike(user_id=current_user.id, comment_id=comment_id, value=value)
        db.session.add(new_like)
        user_vote = value

    db.session.commit()

    return jsonify({
        'status'        : 'success',
        'likes_count'   : comment.like_count,
        'dislikes_count': comment.dislike_count,
        'user_vote'     : user_vote
    })


# ══════════════════════════════════════════════════════════════
# COMMENTS
# ══════════════════════════════════════════════════════════════

@api_bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    """
    Add a top-level comment to a post.
    Returns the new comment's HTML snippet via JSON.
    """

    post  = Post.query.get_or_404(post_id)
    topic = Topic.query.get(post.topic_id)

    # Permission checks
    if current_user.is_banned_from(topic):
        return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403


    data    = request.get_json() or {}
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'status': 'error', 'message': 'Comment cannot be empty.'}), 400

    comment = Comment(
        content  = content,
        post_id  = post_id,
        user_id  = current_user.id,
        parent_id= None
    )
    db.session.add(comment)
    db.session.commit()

    # Return comment data so JavaScript can render it in the DOM
    return jsonify({
        'status'    : 'success',
        'comment_id': comment.id,
        'content'   : comment.content,
        'username'  : current_user.username,
        'profile_pic': current_user.profile_pic,
        'created_at': comment.created_at.strftime('%b %d, %Y')
    })


@api_bp.route('/comment/<int:comment_id>/reply', methods=['POST'])
@login_required
def add_reply(comment_id):
    """
    Add a reply to an existing comment (depth 2 max).
    Replies are children of top-level comments.
    """

    parent  = Comment.query.get_or_404(comment_id)
    post    = Post.query.get(parent.post_id)
    topic   = Topic.query.get(post.topic_id)

    # Don't allow replying to a reply (max depth = 2)
    if parent.parent_id is not None:
        return jsonify({'status': 'error', 'message': 'Max reply depth reached.'}), 400

    if current_user.is_banned_from(topic):
        return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403

    data    = request.get_json() or {}
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'status': 'error', 'message': 'Reply cannot be empty.'}), 400

    reply = Comment(
        content  = content,
        post_id  = post.id,
        user_id  = current_user.id,
        parent_id= comment_id
    )
    db.session.add(reply)
    db.session.commit()

    return jsonify({
        'status'    : 'success',
        'comment_id': reply.id,
        'content'   : reply.content,
        'username'  : current_user.username,
        'profile_pic': current_user.profile_pic,
        'created_at': reply.created_at.strftime('%b %d, %Y')
    })


@api_bp.route('/comment/<int:comment_id>', methods=['PUT'])
@login_required
def edit_comment(comment_id):
    """
    Edit a comment. Only the author can do this.
    """
    comment = Comment.query.get_or_404(comment_id)
    post    = Post.query.get(comment.post_id)
    topic   = Topic.query.get(post.topic_id)

    if current_user.is_banned_from(topic):
        return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403

    if comment.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Permission denied.'}), 403

    data    = request.get_json() or {}
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'status': 'error', 'message': 'Comment cannot be empty.'}), 400

    comment.content = content
    db.session.commit()

    return jsonify({'status': 'success', 'content': comment.content})


# ══════════════════════════════════════════════════════════════
# DELETE – POSTS & COMMENTS
# ══════════════════════════════════════════════════════════════

@api_bp.route('/post/<int:post_id>', methods=['DELETE'])
@login_required
def delete_post(post_id):
    """
    Delete a post via AJAX.
    Allowed: post author, topic creator/moderator, super_admin.
    """

    post  = Post.query.get_or_404(post_id)
    topic = Topic.query.get(post.topic_id)

    if current_user.is_banned_from(topic):
        return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403

    if post.user_id != current_user.id and not current_user.can_moderate(topic):
        return jsonify({'status': 'error', 'message': 'Permission denied.'}), 403

    db.session.delete(post)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Post deleted.'})


@api_bp.route('/comment/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """
    Delete a comment via AJAX.
    Allowed: comment author, topic creator/moderator, super_admin.
    """

    comment = Comment.query.get_or_404(comment_id)
    post    = Post.query.get(comment.post_id)
    topic   = Topic.query.get(post.topic_id)

    if current_user.is_banned_from(topic):
        return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403

    if comment.user_id != current_user.id and not current_user.can_moderate(topic):
        return jsonify({'status': 'error', 'message': 'Permission denied.'}), 403

    db.session.delete(comment)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Comment deleted.'})


# ══════════════════════════════════════════════════════════════
# PIN / UNPIN
# ══════════════════════════════════════════════════════════════

@api_bp.route('/post/<int:post_id>/pin', methods=['POST'])
@login_required
def pin_post(post_id):
    """Toggle pinned status on a post. Moderators/creator only."""

    post  = Post.query.get_or_404(post_id)
    topic = Topic.query.get(post.topic_id)

    if current_user.is_banned_from(topic):
        return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403

    if not current_user.can_moderate(topic):
        return jsonify({'status': 'error', 'message': 'Permission denied.'}), 403

    post.is_pinned = not post.is_pinned
    db.session.commit()

    return jsonify({'status': 'success', 'is_pinned': post.is_pinned})


@api_bp.route('/comment/<int:comment_id>/pin', methods=['POST'])
@login_required
def pin_comment(comment_id):
    """Toggle pinned status on a comment. Moderators/creator only."""

    comment = Comment.query.get_or_404(comment_id)
    post    = Post.query.get(comment.post_id)
    topic   = Topic.query.get(post.topic_id)

    if current_user.is_banned_from(topic):
        return jsonify({'status': 'error', 'message': 'You are banned from this topic.'}), 403

    if not current_user.can_moderate(topic):
        return jsonify({'status': 'error', 'message': 'Permission denied.'}), 403

    comment.is_pinned = not comment.is_pinned
    db.session.commit()

    return jsonify({'status': 'success', 'is_pinned': comment.is_pinned})


# ══════════════════════════════════════════════════════════════
# BAN / PROMOTE
# ══════════════════════════════════════════════════════════════

@api_bp.route('/topic/<int:topic_id>/ban', methods=['POST'])
@login_required
def ban_user(topic_id):
    """
    Ban or unban a user from a topic.
    Request body: { "user_id": 3, "reason": "spam" }
    """
    data    = request.get_json() or {}
    user_id = data.get('user_id')
    reason  = data.get('reason', '')

    topic  = Topic.query.get_or_404(topic_id)
    target = User.query.get_or_404(user_id)

    if not current_user.can_moderate(topic):
        return jsonify({'status': 'error', 'message': 'Permission denied.'}), 403

    if target.id == topic.creator_id:
        return jsonify({'status': 'error', 'message': 'Cannot ban the topic creator.'}), 403

    if target.is_moderator_of(topic) or target.is_super_admin:
        return jsonify({'status': 'error', 'message': 'Cannot ban this user.'}), 400

    existing = BannedUser.query.filter_by(user_id=user_id, topic_id=topic_id).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'unbanned'})
    else:
        ban = BannedUser(user_id=user_id, topic_id=topic_id, banned_by=current_user.id)
        # Note: BannedUser model currently does not store the 'reason' field based on models.py
        # If we added a reason field we would store it here.
        db.session.add(ban)
        db.session.commit()
        return jsonify({'status': 'banned'})



@api_bp.route('/topic/<int:topic_id>/mod', methods=['POST'])
@login_required
def promote_user(topic_id):
    """
    Promote or demote a user to/from moderator in a topic.
    Request body: { "user_id": 3, "action": "promote" }
    """
    data    = request.get_json() or {}
    user_id = data.get('user_id')
    action  = data.get('action') # 'promote' or 'demote'

    topic  = Topic.query.get_or_404(topic_id)
    target = User.query.get_or_404(user_id)

    if topic.creator_id != current_user.id and not current_user.is_super_admin:
        return jsonify({'status': 'error', 'message': 'Only the topic creator can modify moderators.'}), 403

    existing = Moderator.query.filter_by(user_id=user_id, topic_id=topic_id).first()

    if action == 'demote' and existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'demoted'})
    elif action == 'promote' and not existing:
        mod = Moderator(user_id=user_id, topic_id=topic_id)
        db.session.add(mod)
        db.session.commit()
        return jsonify({'status': 'promoted'})
    
    return jsonify({'status': 'success'})


# ══════════════════════════════════════════════════════════════
# TAGS (AJAX)
# ══════════════════════════════════════════════════════════════

@api_bp.route('/topic/<int:topic_id>/tags', methods=['POST'])
@login_required
def create_tag(topic_id):
    """
    POST /api/topic/<topic_id>/tags
    Create a new tag for a topic. Moderators and creators only.
    Request body (JSON): { "name": "Discussion" }
    Returns the new tag's id and name on success.
    """
    topic = Topic.query.get_or_404(topic_id)

    if not current_user.can_moderate(topic):
        return jsonify({'status': 'error', 'message': 'Permission denied.'}), 403

    data = request.get_json() or {}
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'status': 'error', 'message': 'Tag name cannot be empty.'}), 400
        
    from models import Tag
    tag = Tag(name=name, topic_id=topic.id)
    db.session.add(tag)
    db.session.commit()

    return jsonify({'status': 'success', 'tag_id': tag.id, 'name': tag.name})

@api_bp.route('/topic/<int:topic_id>/tags/<int:tag_id>', methods=['DELETE'])
@login_required
def delete_tag(topic_id, tag_id):
    """
    DELETE /api/topic/<topic_id>/tags/<tag_id>
    Delete a tag from a topic. Moderators and creators only.
    Also removes the tag from all posts it was applied to (via post_tags cascade).
    """
    topic = Topic.query.get_or_404(topic_id)

    if not current_user.can_moderate(topic):
        return jsonify({'status': 'error', 'message': 'Permission denied.'}), 403

    from models import Tag
    tag = Tag.query.get_or_404(tag_id)
    if tag.topic_id == topic.id:
        db.session.delete(tag)
        db.session.commit()
        return jsonify({'status': 'success'})
        
    return jsonify({'status': 'error', 'message': 'Tag not found.'}), 404


# ══════════════════════════════════════════════════════════════
# DELETE TOPIC (Creator only, with confirmation)
# ══════════════════════════════════════════════════════════════

@api_bp.route('/topic/<int:topic_id>/delete', methods=['DELETE'])
@login_required
def delete_topic(topic_id):
    """
    Delete an entire topic and all associated data.
    Only the topic creator can perform this action.
    """
    topic = Topic.query.get_or_404(topic_id)

    if current_user.id != topic.creator_id:
        return jsonify({'status': 'error', 'message': 'Only the topic creator can delete this topic.'}), 403

    db.session.delete(topic)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Topic deleted.', 'redirect': '/'})
