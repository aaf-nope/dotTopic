"""
routes/topics.py – Topic & Post Routes
========================================
Handles everything related to topics (communities) and the posts inside them.

Routes:
  GET  /t/<name>                        – Show a topic's posts
  GET  /t/new                           – Show the create-topic form
  POST /t/new                           – Submit and create a new topic
  GET  /t/<name>/post/<id>              – Single post with comment thread
  POST /t/<name>/post/new               – Create a new post (from modal, supports media)
  POST /t/<name>/post/<id>/edit         – Edit an existing post's text and tags
  POST /t/<name>/post/<id>/delete       – Delete a post (server-side form submit)
  GET  /t/<name>/post/<id>/delete       – Delete route redirect (page-level delete button)
  POST /t/<name>/edit_images            – Upload new topic photo or banner
  POST /t/<name>/edit_description       – Update the topic's description (AJAX)
  POST /t/<name>/tags                   – Add or delete a topic tag (form-based)
  POST /t/<name>/reset_images           – Reset topic images to defaults (AJAX)

Key helpers:
  _save_upload(file_obj, subfolder)  – Save a single uploaded file and return its path
"""

import os
import uuid

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user

from models import db, Topic, Post, PostMedia, Comment, Tag, Subscription, LikeDislike

# Create the blueprint
topics_bp = Blueprint('topics', __name__)


# ──────────────────────────────────────────────────────────────
# HELPER: save an uploaded file safely
# ──────────────────────────────────────────────────────────────

def _save_upload(file_obj, subfolder):
    """
    Save an uploaded file to static/uploads/<subfolder>/.
    Returns the relative path (used to serve via /static/uploads/...).
    Returns None if the file is invalid or empty.
    """
    if not file_obj or file_obj.filename == '':
        return None

    # Get the file extension and check it's allowed
    ext = file_obj.filename.rsplit('.', 1)[-1].lower()
    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        return None

    # Generate a unique filename to avoid collisions
    unique_name = f'{uuid.uuid4().hex}.{ext}'

    # Build the full save path (static/uploads/<subfolder>/)
    save_dir  = os.path.join(current_app.config['UPLOAD_FOLDER'], 'uploads', subfolder)
    save_path = os.path.join(save_dir, unique_name)

    os.makedirs(save_dir, exist_ok=True)
    file_obj.save(save_path)

    # Return path relative to /static/ so templates can use url_for('static', ...)
    return f'uploads/{subfolder}/{unique_name}'


# ──────────────────────────────────────────────────────────────
# TOPIC PAGE  (route: /t/<name>)
# ──────────────────────────────────────────────────────────────

@topics_bp.route('/t/<string:topic_name>')
def topic_page(topic_name):
    """
    Display a topic page with its posts.
    Sorting is controlled by the ?sort= query parameter.
    """

    # Find the topic (404 if not found)
    topic = Topic.query.filter_by(name=topic_name).first_or_404()

    # Check subscription & moderation status for Jinja2 conditionals
    is_subscribed = False
    is_moderator  = False
    is_banned     = False

    if current_user.is_authenticated:
        is_subscribed = current_user.is_subscribed_to(topic)
        is_moderator  = current_user.can_moderate(topic)
        is_banned     = current_user.is_banned_from(topic)

    # ── Sorting logic (Chapter 17: request.args) ──────────────

    sort_option = request.args.get('sort', 'newest')
    tag_filter  = request.args.get('tag', '').strip()

    base_query = Post.query.filter_by(topic_id=topic.id)
    if tag_filter:
        base_query = base_query.filter(Post.tags.any(Tag.name == tag_filter))

    if sort_option == 'oldest':
        posts_query = base_query.order_by(
            Post.is_pinned.desc(), Post.created_at.asc()
        )
    elif sort_option == 'top':
        # Subquery to count likes per post – simple approach
        posts_query = base_query.order_by(
            Post.is_pinned.desc(), Post.created_at.desc()
        )
        posts = posts_query.all()
        posts.sort(key=lambda p: p.like_count, reverse=True)
    else:  # default: newest
        posts_query = base_query.order_by(
            Post.is_pinned.desc(), Post.created_at.desc()
        )

    if sort_option != 'top':
        posts = posts_query.all()

    # Get topic tags for the post-creation modal dropdown
    tags = Tag.query.filter_by(topic_id=topic.id).all()

    # Attach user_vote to each post for like/dislike button initial state
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
        'topic.html',
        topic        = topic,
        posts        = posts,
        tags         = tags,
        sort_option  = sort_option,
        current_tag  = tag_filter,
        is_subscribed= is_subscribed,
        is_moderator = is_moderator,
        is_banned    = is_banned
    )


# ──────────────────────────────────────────────────────────────
# CREATE TOPIC  (route: /t/new)
# ──────────────────────────────────────────────────────────────

@topics_bp.route('/t/<string:topic_name>/edit_images', methods=['POST'])
@login_required
def edit_topic_images(topic_name):
    """Handler for edit_topic_images."""
    topic = Topic.query.filter_by(name=topic_name).first_or_404()
    if not current_user.can_moderate(topic) and not current_user.is_super_admin:
        abort(403)
        
    photo_obj = request.files.get('photo')
    if photo_obj and photo_obj.filename:
        path = _save_upload(photo_obj, 'post_media')
        if path:
            topic.photo = path
            
    banner_obj = request.files.get('banner')
    if banner_obj and banner_obj.filename:
        path = _save_upload(banner_obj, 'post_media')
        if path:
            topic.banner = path
            
    db.session.commit()
    flash('Topic images updated!', 'success')
    # Smart redirect: go back to the page the user came from,
    # as long as it's a topic or profile page (not a random external URL).
    ref = request.referrer
    if ref and ('/t/' in ref or '/u/' in ref):
        return redirect(ref)
    # Fallback: go to the topic page.
    return redirect(url_for('topics.topic_page', topic_name=topic_name))


@topics_bp.route('/t/<string:topic_name>/edit_description', methods=['POST'])
@login_required
def edit_topic_description(topic_name):
    """Edit the topic description. Only creator, moderators, or super_admin."""
    topic = Topic.query.filter_by(name=topic_name).first_or_404()
    if not current_user.can_moderate(topic) and not current_user.is_super_admin:
        abort(403)
    desc = request.form.get('description', '').strip()
    if not desc:
        return jsonify({'status': 'error', 'message': 'Description cannot be empty.'}), 400
    topic.description = desc
    db.session.commit()
    return jsonify({'status': 'success'})


# ──────────────────────────────────────────────────────────────
# CREATE TOPIC  (route: /t/new)
# ──────────────────────────────────────────────────────────────

@topics_bp.route('/t/new', methods=['GET', 'POST'])
@login_required
def create_topic():
    """
    GET:  Show the create-topic form page.
    POST: Process the form and create a new topic in the database.
          The submitting user becomes the topic creator.
    """

    if request.method == 'GET':
        return render_template('create_topic.html')

    # ── Process POST ──────────────────────────────────────────

    name        = request.form.get('name', '').strip().lower()
    description = request.form.get('description', '').strip()

    # Validate name
    if not name:
        flash('Topic name is required.', 'danger')
        return render_template('create_topic.html')

    # Only letters, numbers, underscores, hyphens allowed in topic name
    import re
    if not re.match(r'^[a-z0-9_-]+$', name):
        flash('Topic name can only contain letters, numbers, underscores, and hyphens.', 'danger')
        return render_template('create_topic.html')

    if Topic.query.filter_by(name=name).first():
        flash(f'A topic named "{name}" already exists.', 'danger')
        return render_template('create_topic.html')

    # Handle optional photo and banner uploads; fall back to defaults
    photo_path  = _save_upload(request.files.get('photo'),  'post_media') or 'default_topic.png'
    banner_path = _save_upload(request.files.get('banner'), 'post_media') or 'default_banner.png'

    # Create the new topic – creator is the logged-in user
    new_topic = Topic(
        name       = name,
        description= description,
        photo      = photo_path,
        banner     = banner_path,
        creator_id = current_user.id
    )

    db.session.add(new_topic)
    db.session.commit()

    # Auto-subscribe the creator to their own topic
    sub = Subscription(user_id=current_user.id, topic_id=new_topic.id)
    db.session.add(sub)
    db.session.commit()

    flash(f'Topic ".{name}" created successfully!', 'success')
    return redirect(url_for('topics.topic_page', topic_name=name))


# ──────────────────────────────────────────────────────────────
# POST DETAIL PAGE  (route: /t/<name>/post/<id>)
# ──────────────────────────────────────────────────────────────

@topics_bp.route('/t/<string:topic_name>/post/<int:post_id>')
def post_detail(topic_name, post_id):
    """
    Display a single post with its full content and comment thread.
    Comments are server-side rendered (no AJAX loading needed).
    Max comment depth: 2 (comment → reply).
    """

    # Find the topic and post (404 if not found)
    topic = Topic.query.filter_by(name=topic_name).first_or_404()
    post  = Post.query.filter(
        Post.id == post_id,
        Post.topic_id == topic.id
    ).first_or_404()

    # ── Sort comments ─────────────────────────────────────────

    sort_option = request.args.get('sort', 'newest')

    # Fetch only TOP-LEVEL comments (parent_id is None)
    # Replies are accessed via comment.replies in the template
    if sort_option == 'oldest':
        top_comments = Comment.query.filter_by(
            post_id=post.id, parent_id=None
        ).order_by(Comment.is_pinned.desc(), Comment.created_at.asc()).all()

    elif sort_option == 'top':
        top_comments = Comment.query.filter_by(
            post_id=post.id, parent_id=None
        ).all()
        top_comments.sort(key=lambda c: c.like_count, reverse=True)
        # Keep pinned at top
        pinned   = [c for c in top_comments if c.is_pinned]
        unpinned = [c for c in top_comments if not c.is_pinned]
        top_comments = pinned + unpinned

    else:  # default: newest
        top_comments = Comment.query.filter_by(
            post_id=post.id, parent_id=None
        ).order_by(Comment.is_pinned.desc(), Comment.created_at.desc()).all()

    # ── Permissions for current user ──────────────────────────

    is_moderator  = False
    is_banned     = False
    user_like_val = 0  # 0 = no vote, 1 = liked, -1 = disliked

    if current_user.is_authenticated:
        is_moderator = current_user.can_moderate(topic)
        is_banned    = current_user.is_banned_from(topic)

        # Check if user has already liked/disliked this post
        if not is_banned:
            existing_like = LikeDislike.query.filter_by(
                user_id=current_user.id, post_id=post.id
            ).first()
            if existing_like:
                user_like_val = existing_like.value

    return render_template(
        'post_detail.html',
        topic        = topic,
        post         = post,
        top_comments = top_comments,
        sort_option  = sort_option,
        is_moderator = is_moderator,
        is_banned    = is_banned,
        user_like_val= user_like_val
    )


# ──────────────────────────────────────────────────────────────
# CREATE NEW POST  (route: POST /t/<name>/post/new)
# ──────────────────────────────────────────────────────────────

@topics_bp.route('/t/<string:topic_name>/post/new', methods=['POST'])
@login_required
def create_post(topic_name):
    """
    Handle new post submission from the Create Post modal.
    Option A: Regular form POST (simple, Chapter 17).
    Files are uploaded to static/uploads/post_media/.
    """

    topic = Topic.query.filter_by(name=topic_name).first_or_404()

    # Check if user is banned from this topic
    if current_user.is_banned_from(topic):
        flash('You are banned from posting in this topic.', 'danger')
        return redirect(url_for('topics.topic_page', topic_name=topic_name))


    # Must be subscribed to post (or be creator/moderator)
    if (not current_user.is_subscribed_to(topic)
            and not current_user.can_moderate(topic)
            and not current_user.is_super_admin):
        flash('You must subscribe to this topic before posting.', 'warning')
        return redirect(url_for('topics.topic_page', topic_name=topic_name))

    # ── Get form values ───────────────────────────────────────

    title   = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    # Extract other fields later inside try block
    # tag_ids is now a JSON string 'tags'

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or 'application/json' in request.headers.get('Accept', '')

    if not title:
        if is_ajax:
            return jsonify({'status': 'error', 'message': 'Post title is required.'}), 400
        flash('Post title is required.', 'danger')
        return redirect(url_for('topics.topic_page', topic_name=topic_name))

    try:
        # ── Create the post ───────────────────────────────────────

        new_post = Post(
            title    = title,
            content  = content,
            topic_id = topic.id,
            user_id  = current_user.id
        )
        db.session.add(new_post)
        db.session.flush()  # Get the post ID before committing

        # Attach selected tags
        import json
        tags_str = request.form.get('tags', '[]')
        try:
            tag_ids = json.loads(tags_str)
        except Exception:
            tag_ids = []
            
        for tag_id in tag_ids:
            tag = db.session.get(Tag, int(tag_id))
            if tag and tag.topic_id == topic.id:
                new_post.tags.append(tag)

        # ── Handle media uploads ──────────────────────────────────

        media_files = request.files.getlist('media')
        import uuid
        for file_obj in media_files:
            if not file_obj.filename:
                continue
            # Generate unique filename with UUID
            ext = file_obj.filename.rsplit('.', 1)[-1].lower()
            if ext not in {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'webm'}:
                continue
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            file_obj.filename = unique_filename
            
            file_path = _save_upload(file_obj, 'post_media')
            if file_path:
                file_type = 'video' if ext in {'mp4', 'webm', 'mov'} else 'image'
                alt_text  = "Post Media"
                media = PostMedia(
                    post_id  = new_post.id,
                    file_path= file_path,
                    alt_text = alt_text,
                    file_type= file_type
                )
                db.session.add(media)

        db.session.commit()

        if is_ajax:
            return jsonify({
                'status': 'success',
                'post_url': url_for('topics.post_detail', topic_name=topic_name, post_id=new_post.id)
            })

        flash('Post created!', 'success')
        return redirect(url_for('topics.post_detail', topic_name=topic_name, post_id=new_post.id))

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        if is_ajax:
            return jsonify({'status': 'error', 'message': str(e)}), 400
        flash(f'Error creating post: {str(e)}', 'danger')
        return redirect(url_for('topics.topic_page', topic_name=topic_name))


# ──────────────────────────────────────────────────────────────
# EDIT POST  (route: POST /t/<name>/post/<id>/edit)
# ──────────────────────────────────────────────────────────────

@topics_bp.route('/t/<string:topic_name>/post/<int:post_id>/edit', methods=['POST'])
@login_required
def edit_post(topic_name, post_id):
    """
    Handle post editing. Only the post author can edit their own post.
    Moderators can delete but not edit others' posts.
    """

    topic = Topic.query.filter_by(name=topic_name).first_or_404()
    post  = Post.query.filter(
        Post.id == post_id, Post.topic_id == topic.id
    ).first_or_404()

    # Only the post author can edit
    if post.user_id != current_user.id and not current_user.is_super_admin:
        abort(403)

    if current_user.is_banned_from(topic):
        abort(403)

    title   = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or 'application/json' in request.headers.get('Accept', '')

    if not title:
        if is_ajax:
            return jsonify({'status': 'error', 'message': 'Post title cannot be empty.'}), 400
        flash('Post title cannot be empty.', 'danger')
        return redirect(url_for('topics.post_detail', topic_name=topic_name, post_id=post_id))

    try:
        post.title   = title
        post.content = content

        # Update tags
        import json
        tags_str = request.form.get('tags', '[]')
        try:
            tag_ids = json.loads(tags_str)
        except Exception:
            tag_ids = []

        post.tags.clear()
        for tag_id in tag_ids:
            tag = db.session.get(Tag, int(tag_id))
            if tag and tag.topic_id == topic.id:
                post.tags.append(tag)

        # Handle existing media deletion
        import json
        import os
        from flask import current_app
        existing_media_ids_str = request.form.get('existing_media_ids', '[]')
        try:
            existing_media_ids = json.loads(existing_media_ids_str)
            existing_media_ids = [int(i) for i in existing_media_ids]
        except Exception:
            existing_media_ids = []

        # Find media not in existing_media_ids
        for media in list(post.media):
            if media.id not in existing_media_ids:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], media.file_path.replace('uploads/', ''))
                if os.path.exists(file_path):
                    os.remove(file_path)
                db.session.delete(media)

        # Handle new media uploads
        media_files = request.files.getlist('media')
        import uuid
        for file_obj in media_files:
            if not file_obj.filename:
                continue
            # Generate unique filename with UUID
            ext = file_obj.filename.rsplit('.', 1)[-1].lower()
            if ext not in {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'webm'}:
                continue
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            file_obj.filename = unique_filename
            
            file_path = _save_upload(file_obj, 'post_media')
            if file_path:
                file_type = 'video' if ext in {'mp4', 'webm'} else 'image'
                alt_text  = "Post Media"
                
                media = PostMedia(
                    post_id  = post.id,
                    file_path= file_path,
                    alt_text = alt_text,
                    file_type= file_type
                )
                db.session.add(media)

        db.session.commit()

        if is_ajax:
            return jsonify({
                'status': 'success',
                'post_url': url_for('topics.post_detail', topic_name=topic_name, post_id=post_id)
            })

        flash('Post updated!', 'success')
        return redirect(url_for('topics.post_detail', topic_name=topic_name, post_id=post_id))

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        if is_ajax:
            return jsonify({'status': 'error', 'message': str(e)}), 400
        flash(f'Error updating post: {str(e)}', 'danger')
        return redirect(url_for('topics.post_detail', topic_name=topic_name, post_id=post_id))


# ──────────────────────────────────────────────────────────────
# DELETE POST  (route: POST /t/<name>/post/<id>/delete)
# ──────────────────────────────────────────────────────────────

@topics_bp.route('/t/<string:topic_name>/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post_page(topic_name, post_id):
    """
    Server-side post deletion (used as fallback; AJAX delete is in api.py).
    """
    topic = Topic.query.filter_by(name=topic_name).first_or_404()
    post  = Post.query.filter(
        Post.id == post_id, Post.topic_id == topic.id
    ).first_or_404()

    # Allow: post author, topic creator/moderators, super_admin
    if post.user_id != current_user.id and not current_user.can_moderate(topic):
        abort(403)

    if current_user.is_banned_from(topic):
        abort(403)

    db.session.delete(post)
    db.session.commit()

    flash('Post deleted.', 'info')
    return redirect(url_for('topics.topic_page', topic_name=topic_name))


# ──────────────────────────────────────────────────────────────
# MANAGE TAGS  (route: POST /t/<name>/tags)
# ──────────────────────────────────────────────────────────────

@topics_bp.route('/t/<string:topic_name>/tags', methods=['POST'])
@login_required
def manage_tags(topic_name):
    """
    Add or delete tags for a topic.
    Only topic creator, moderators, or super_admin can do this.
    """
    topic = Topic.query.filter_by(name=topic_name).first_or_404()

    if not current_user.can_moderate(topic):
        abort(403)

    action   = request.form.get('action')   # 'add' or 'delete'
    tag_name = request.form.get('tag_name', '').strip()
    tag_id   = request.form.get('tag_id',   type=int)

    if action == 'add' and tag_name:
        new_tag = Tag(name=tag_name, topic_id=topic.id)
        db.session.add(new_tag)
        db.session.commit()
        flash(f'Tag "{tag_name}" added.', 'success')

    elif action == 'delete' and tag_id:
        tag = Tag.query.get(tag_id)
        if tag and tag.topic_id == topic.id:
            db.session.delete(tag)
            db.session.commit()
            flash('Tag deleted.', 'info')

    return redirect(url_for('topics.topic_page', topic_name=topic_name))


# ──────────────────────────────────────────────────────────────
# RESET TOPIC IMAGES (creator / moderator / super-admin)
# ──────────────────────────────────────────────────────────────

@topics_bp.route('/t/<string:topic_name>/reset_images', methods=['POST'])
@login_required
def reset_topic_images(topic_name):
    """Reset topic photo and banner back to their default images."""
    topic = Topic.query.filter_by(name=topic_name).first_or_404()

    if not (current_user.id == topic.creator_id
            or current_user.can_moderate(topic)
            or current_user.is_super_admin):
        abort(403)

    topic.photo  = 'default_topic.png'
    topic.banner = 'default_banner.png'
    db.session.commit()

    return jsonify({'status': 'success'})
