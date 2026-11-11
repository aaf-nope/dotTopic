/**
 * main.js – Core Page Interactivity
 * ====================================
 * The largest JS file. Handles most AJAX-powered interactions across the site.
 * Loaded on every page via base.html (after jQuery).
 *
 * Sections in this file:
 *   1.  Feed Toggle              – Random ↔ Subscribed home page toggle
 *   2.  Media Preview            – Show thumbnail before uploading a file
 *   3.  Comment Submission       – Post a new top-level comment via AJAX
 *   4.  Reply Form Toggle        – Show/hide the inline reply textbox
 *   5.  Reply Submission         – Post a reply to a comment via AJAX
 *   6.  Comment / Reply Delete   – Delete comments and replies via AJAX
 *   7.  Comment Edit             – Edit comment text inline via AJAX
 *   8.  Pin Post (delegated)     – Fallback delegated handler for pin buttons
 *   9.  Delete Post (delegated)  – Fallback delegated handler for delete buttons
 *  10.  Sort Buttons             – Highlight the active sort tab (newest/oldest/top)
 *  11.  Pin/Unpin on Post Detail – Pin button handler specific to post_detail page
 *  12.  Mod Panel: Ban/Unban     – Moderate users from the topic sidebar
 *  13.  Mod Panel: Promote/Demote – Grant/remove moderator status
 *  14.  Topic Description Edit   – Inline edit of topic description text
 *  15.  Reset Topic Images       – Modal + AJAX for resetting topic photo/banner
 *  16.  Tag Management           – Add/delete topic tags; filter posts by tag
 *  17.  Theme Toggle             – Switch light/dark mode, saved to localStorage
 *  18.  Post Edit Modal          – Pre-fill and open the edit post modal
 *
 * How AJAX calls work in this file:
 *   - jQuery's $.ajax() is used throughout.
 *   - All API calls go to /api/... routes (defined in routes/api.py).
 *   - Responses are JSON objects with a 'status' field ('success' or 'error').
 *   - The showAlert() and showConfirm() helpers (from modal-handler.js) are
 *     used instead of browser alert() / confirm().
 */


$(document).ready(function () {

    // ══════════════════════════════════════════════════════════
    // FEED TOGGLE: Random ↔ Subscribed
    // Chapter 11: Click events
    // ══════════════════════════════════════════════════════════

    $('.feed-toggle-btn').on('click', function () {
        // Remove active class from all toggle buttons and add to the clicked one
        $('.feed-toggle-btn').removeClass('active');
        $(this).addClass('active');

        const feedType = $(this).data('feed');  // 'random' or 'subscribed'

        // Add the ?feed= parameter to the current URL and reload
        window.location.href = '/?feed=' + feedType;
    });


    // ══════════════════════════════════════════════════════════
    // MEDIA FILE PREVIEW THUMBNAILS
    // Chapter 13: FileReader API – reading files before upload
    // ══════════════════════════════════════════════════════════

    $('#media-file-input').on('change', function () {
        const files   = this.files;      // All selected files
        const $preview = $('#media-preview');

        // Clear any existing previews
        $preview.empty();

        // Loop through each selected file
        for (let i = 0; i < files.length; i++) {
            const file = files[i];

            // Use FileReader to read the file as a data URL (base64)
            const reader = new FileReader();

            // Immediately-invoked function to capture the current 'file' in the loop
            (function (f) {
                reader.onload = function (event) {
                    const dataUrl = event.target.result;

                    // Create a preview element based on file type
                    let mediaHtml = '';

                    if (f.type.startsWith('video/')) {
                        mediaHtml = '<video src="' + dataUrl + '" controls></video>';
                    } else {
                        // Extract alt text from filename (without extension)
                        const altText = f.name.replace(/\.[^/.]+$/, '');
                        mediaHtml = '<img src="' + dataUrl + '" alt="' + altText + '">';
                    }

                    // Build the preview item with a remove button
                    const $item = $('<div class="media-preview-item">')
                        .append(mediaHtml)
                        .append('<button type="button" class="remove-media" title="Remove">✕</button>');

                    $preview.append($item);
                };
            })(file);

            // Trigger the FileReader
            reader.readAsDataURL(file);
        }
    });

    // Remove a single preview item when the ✕ button is clicked
    $(document).on('click', '.remove-media', function () {
        $(this).closest('.media-preview-item').remove();
    });


    // ══════════════════════════════════════════════════════════
    // SUBMIT COMMENT (via AJAX)
    // Chapter 15: jQuery $.ajax
    // ══════════════════════════════════════════════════════════

    $('#comment-submit-btn').on('click', function () {

        const postId  = $(this).data('post-id');
        const content = $('#comment-textarea').val().trim();

        if (!content) {
            showAlert('Comment cannot be empty.');
            return;
        }

        const $btn = $(this);
        $btn.prop('disabled', true).text('Posting...');

        $.ajax({
            url        : '/api/post/' + postId + '/comment',
            method     : 'POST',
            contentType: 'application/json',
            data       : JSON.stringify({ content: content }),

            success: function (response) {
                if (response.status === 'success') {

                    // Clear the textarea
                    $('#comment-textarea').val('');

                    // Build the new comment HTML and prepend it to the list
                    const $newComment = buildCommentHTML(
                        response.comment_id,
                        response.username,
                        response.profile_pic,
                        response.content,
                        response.created_at,
                        postId,
                        true   // isOwn = true (current user just posted it)
                    );

                    $('#comments-list').prepend($newComment);
                }

                $btn.prop('disabled', false).text('Comment');
            },

            error: function (xhr) {
                $btn.prop('disabled', false).text('Comment');
                if (xhr.status === 401) {
                    openModal('auth-modal');
                } else {
                    showAlert(xhr.responseJSON?.message || 'Could not post comment.');
                }
            }
        });
    });


    // ══════════════════════════════════════════════════════════
    // REPLY FORM: Toggle show/hide
    // Chapter 11: Click events, Chapter 12: classList
    // ══════════════════════════════════════════════════════════

    $(document).on('click', '.reply-toggle-btn', function () {
        const $replyForm = $(this).closest('.comment-item').find('.reply-form').first();
        $replyForm.toggleClass('open');

        // Focus the textarea when opened
        if ($replyForm.hasClass('open')) {
            $replyForm.find('textarea').focus();
        }
    });

    // Cancel button inside reply form
    $(document).on('click', '.reply-cancel-btn', function () {
        $(this).closest('.reply-form').removeClass('open');
    });


    // ══════════════════════════════════════════════════════════
    // SUBMIT REPLY (via AJAX)
    // ══════════════════════════════════════════════════════════

    $(document).on('click', '.reply-submit-btn', function () {

        const $btn      = $(this);
        const commentId = $btn.data('comment-id');
        const $form     = $btn.closest('.reply-form');
        const content   = $form.find('textarea').val().trim();
        const postId    = $btn.data('post-id');

        if (!content) {
            showAlert('Reply cannot be empty.');
            return;
        }

        $btn.prop('disabled', true).text('Posting...');

        $.ajax({
            url        : '/api/comment/' + commentId + '/reply',
            method     : 'POST',
            contentType: 'application/json',
            data       : JSON.stringify({ content: content }),

            success: function (response) {
                if (response.status === 'success') {
                    $form.find('textarea').val('');
                    $form.removeClass('open');

                    // Find or create the replies container under this comment
                    let $repliesContainer = $form.closest('.comment-item').find('.replies-container').first();

                    if ($repliesContainer.length === 0) {
                        $repliesContainer = $('<div class="replies-container">');
                        $form.closest('.comment-item').append($repliesContainer);
                    }

                    // Build the reply HTML (no reply button since max depth = 2)
                    const $newReply = buildCommentHTML(
                        response.comment_id,
                        response.username,
                        response.profile_pic,
                        response.content,
                        response.created_at,
                        postId,
                        true,   // isOwn
                        false   // showReplyBtn = false (max depth)
                    );

                    $repliesContainer.append($newReply);
                }

                $btn.prop('disabled', false).text('Reply');
            },

            error: function (xhr) {
                $btn.prop('disabled', false).text('Reply');
                showAlert(xhr.responseJSON?.message || 'Could not post reply.');
            }
        });
    });


    // ══════════════════════════════════════════════════════════
    // DELETE COMMENT (via AJAX)
    // ══════════════════════════════════════════════════════════

    /**
     * Confirm and delete a comment.
     * @param {number}  commentId - The ID of the comment to delete
     * @param {Element} btnEl     - The delete button element (to find the card)
     */
    window.confirmDeleteComment = function (commentId, btnEl) {
        showConfirm('Delete this comment?', function () {
            $.ajax({
                url   : '/api/comment/' + commentId,
                method: 'DELETE',

                success: function () {
                    // Fade out and remove the comment item
                    $(btnEl).closest('.comment-item').fadeOut(300, function () {
                        $(this).remove();
                    });
                },

                error: function (xhr) {
                    showAlert(xhr.responseJSON?.message || 'Could not delete comment.');
                }
            });
        });
    };


    // ══════════════════════════════════════════════════════════
    // HELPER: Build comment HTML dynamically
    // Chapter 13: Creating DOM elements with JavaScript
    // ══════════════════════════════════════════════════════════

    /**
     * Create a comment item element from data returned by the API.
     *
     * @param {number}  id           - Comment ID
     * @param {string}  username     - Author's username
     * @param {string}  profilePic   - Profile picture filename
     * @param {string}  content      - Comment text
     * @param {string}  date         - Formatted date string
     * @param {number}  postId       - The post this comment belongs to
     * @param {boolean} isOwn        - Whether the current user owns this comment
     * @param {boolean} showReplyBtn - Whether to show the Reply button (default true)
     * @returns {jQuery} - The built comment item jQuery element
     */
    function buildCommentHTML(id, username, profilePic, content, date, postId, isOwn, showReplyBtn = true) {

        const picSrc = profilePic
            ? '/static/' + profilePic
            : '/static/images/default_pfp.png';

        const deleteBtn = isOwn
            ? `<button class="comment-action-btn delete-comment-btn" data-comment-id="${id}" title="Delete">🗑 Delete</button>`
            : '';

        // Reply button (only shown if max depth not reached)
        const replyBtn = showReplyBtn
            ? `<button class="comment-action-btn reply-toggle-btn">↩ Reply</button>`
            : '';

        // Reply form (hidden by default)
        const replyForm = showReplyBtn
            ? `<div class="reply-form">
                   <textarea placeholder="Write a reply..." rows="2"></textarea>
                   <div class="reply-form-actions">
                       <button class="btn btn-primary btn-sm reply-submit-btn"
                               data-comment-id="${id}"
                               data-post-id="${postId}">Reply</button>
                       <button class="btn btn-secondary btn-sm reply-cancel-btn">Cancel</button>
                   </div>
               </div>`
            : '';

        const html = `
            <div class="comment-item" id="comment-${id}">
                <div class="comment-bubble">
                    <div class="comment-author">
                        <img src="${picSrc}" alt="${username}" class="comment-avatar">
                        <a href="/u/${username}" class="comment-username">${username}</a>
                        <span class="comment-date">${date}</span>
                    </div>
                    <div class="comment-body">${content}</div>
                    <div class="comment-actions">
                        <button class="comment-action-btn comment-vote-btn liked"
                                data-comment-id="${id}" data-value="1">
                            👍 <span class="comment-like-count">0</span>
                        </button>
                        <button class="comment-action-btn comment-vote-btn"
                                data-comment-id="${id}" data-value="-1">
                            👎 <span class="comment-dislike-count">0</span>
                        </button>
                        ${replyBtn}
                        ${deleteBtn}
                    </div>
                    ${replyForm}
                </div>
            </div>
        `;

        return $(html);
    }

    // ══════════════════════════════════════════════════════════
    // MODERATION ACTIONS (Promote, Demote, Ban)
    // ══════════════════════════════════════════════════════════

    $(document).on('click', '.mod-action-btn', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const action = $(this).data('action'); // 'promote', 'demote', 'ban', 'unban'
        const userId = $(this).data('user-id');
        const topicId = $(this).data('topic-id');
        const $btn = $(this);

        if (action === 'promote' || action === 'demote') {
            $btn.prop('disabled', true);
            $.ajax({
                url: '/api/topic/' + topicId + '/mod',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ user_id: userId, action: action }),
                success: function (res) {
                    $btn.prop('disabled', false);
                    if (res.status === 'promoted') {
                        // Update all buttons for this user
                        $('.mod-action-btn[data-user-id="' + userId + '"][data-action="promote"]')
                            .text('Demote').data('action', 'demote').attr('data-action', 'demote');
                        // Add mod badge
                        $('.user-badges[data-user-id="' + userId + '"]:not(:has(.badge.mod))').append('<span class="badge mod" style="margin-left:4px;">Mod</span>');
                    } else if (res.status === 'demoted') {
                        $('.mod-action-btn[data-user-id="' + userId + '"][data-action="demote"]')
                            .text('Promote to Mod').data('action', 'promote').attr('data-action', 'promote');
                        // Remove mod badge
                        $('.user-badges[data-user-id="' + userId + '"] .badge.mod').remove();
                    }
                },
                error: function (xhr) {
                    $btn.prop('disabled', false);
                    showAlert(xhr.responseJSON?.message || 'Error updating moderator status.');
                }
            });
        }
        else if (action === 'ban') {
            // Open reason modal
            $('#mod-reason-action').val(action);
            $('#mod-reason-user-id').val(userId);
            $('#mod-reason-topic-id').val(topicId);
            $('#mod-reason-input').val('');
            
            $('#mod-reason-modal .modal-title').text('Ban User');
            openModal('mod-reason-modal');
        }
        else if (action === 'unban') {
            $btn.prop('disabled', true);
            $.ajax({
                url: '/api/topic/' + topicId + '/ban',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ user_id: userId }),
                success: function (res) {
                    $btn.prop('disabled', false);
                    if (res.status === 'unbanned') {
                        $('.mod-action-btn[data-user-id="' + userId + '"][data-action="unban"]')
                            .text('Ban').data('action', 'ban').attr('data-action', 'ban').removeClass('btn-danger').addClass('btn-secondary');
                        $('.user-badges[data-user-id="' + userId + '"] .badge.banned').remove();
                    }
                },
                error: function (xhr) {
                    $btn.prop('disabled', false);
                    showAlert(xhr.responseJSON?.message || 'Error updating user status.');
                }
            });
        }
    });

    // Handle mod reason modal submit (ban only)
    $('#submit-mod-reason').on('click', function() {
        const action = $('#mod-reason-action').val(); // 'ban'
        const userId = parseInt($('#mod-reason-user-id').val());
        const topicId = parseInt($('#mod-reason-topic-id').val());
        const reason = $('#mod-reason-input').val().trim();
        
        const $btn = $(this);
        $btn.prop('disabled', true).text('Processing...');

        $.ajax({
            url: '/api/topic/' + topicId + '/ban',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ user_id: userId, reason: reason }),
            success: function (res) {
                $btn.prop('disabled', false).text('Confirm');
                closeModal('mod-reason-modal');
                
                if (res.status === 'banned') {
                    $('.mod-action-btn[data-user-id="' + userId + '"][data-action="ban"]')
                        .text('Unban').data('action', 'unban').attr('data-action', 'unban').removeClass('btn-secondary').addClass('btn-danger');
                    $('.user-badges[data-user-id="' + userId + '"]:not(:has(.badge.banned))').append('<span class="badge banned" style="margin-left:4px;">Banned</span>');
                }
            },
            error: function (xhr) {
                $btn.prop('disabled', false).text('Confirm');
                showAlert(xhr.responseJSON?.message || 'Error processing action.');
                closeModal('mod-reason-modal');
            }
        });
    });

    // ══════════════════════════════════════════════════════════
    // SIDEBAR ACTIONS (Unban, Tags)
    // ══════════════════════════════════════════════════════════
    
    window.unbanUser = function(userId, topicId) {
        $.ajax({
            url: '/api/topic/' + topicId + '/ban',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ user_id: userId }),
            success: function (res) {
                if (res.status === 'unbanned') {
                    $('#banned-user-' + userId).fadeOut(300, function() { $(this).remove(); });
                }
            },
            error: function (xhr) {
                showAlert(xhr.responseJSON?.message || 'Error unbanning user.');
            }
        });
    };

    // ── Create Post button (data-topic-name) ──
    $(document).on('click', '#create-post-btn', function() {
        openCreatePostModal($(this).data('topic-name'));
    });

    // ── Add Tag button (data-topic-id) ──
    $(document).on('click', '#add-tag-btn', function() {
        submitNewTag($(this).data('topic-id'));
    });

    // ── Delete Topic Forever button (data-topic-id) ──
    $(document).on('click', '#delete-topic-forever-btn', function() {
        confirmDeleteTopic($(this).data('topic-id'));
    });

    // ── Delete Tag (sidebar span.delete-tag-btn) ──
    $(document).on('click', '.delete-tag-btn', function() {
        deleteTag($(this).data('tag-id'), $(this).data('topic-id'));
    });

    // ── Edit Comment button (.edit-comment-btn) ──
    $(document).on('click', '.edit-comment-btn', function() {
        openEditCommentModal($(this).data('comment-id'));
    });

    // ── Delete Comment button (.delete-comment-btn) ──
    $(document).on('click', '.delete-comment-btn', function() {
        confirmDeleteComment($(this).data('comment-id'), this);
    });

    // ── Pin Comment button (.pin-comment-btn) ──
    $(document).on('click', '.pin-comment-btn', function() {
        pinComment($(this).data('comment-id'), this);
    });

    // ── Pin Post button on post_detail (#pin-post-btn) ──
    $(document).on('click', '#pin-post-btn', function() {
        togglePinPost($(this).data('post-id'), this);
    });

    // ── Pin Post button on post_card (.mod-btn.pin) ──
    $(document).on('click', '.mod-btn.pin', function(e) {
        e.stopPropagation();
        e.preventDefault();
        togglePinPost($(this).data('post-id'), this);
    });

    // ── Delete Post button on post_card (.mod-btn.delete) ──
    $(document).on('click', '.mod-btn.delete', function(e) {
        e.stopPropagation();
        e.preventDefault();
        confirmDeletePost($(this).data('post-id'), this);
    });
    
    window.submitNewTag = function(topicId) {
        const name = $('#new-tag-input').val().trim();
        if (!name) return showAlert('Tag name cannot be empty');
        
        $.ajax({
            url: '/api/topic/' + topicId + '/tags',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ name: name }),
            success: function (res) {
                if (res.status === 'success') {
                    const newHtml = `
                    <span class="tag-chip" id="tag-${res.tag_id}">
                        ${res.name} 
                        <span class="delete-tag-btn" style="cursor:pointer; margin-left:4px;" data-tag-id="${res.tag_id}" data-topic-id="${topicId}">✕</span>
                    </span>`;
                    $('#topic-tags-list').append(newHtml);
                    $('#no-tags-msg').remove();
                    $('#new-tag-input').val('');
                    closeModal('create-tag-modal');
                }
            },
            error: function (xhr) {
                showAlert(xhr.responseJSON?.message || 'Error creating tag.');
            }
        });
    };
    
    window.deleteTag = function(tagId, topicId) {
        if(!topicId) {
            showAlert('Cannot determine topic ID for deletion');
            return;
        }
        
        $.ajax({
            url: '/api/topic/' + topicId + '/tags/' + tagId,
            method: 'DELETE',
            success: function (res) {
                if (res.status === 'success') {
                    $('#tag-' + tagId).fadeOut(300, function() { $(this).remove(); });
                }
            },
            error: function (xhr) {
                showAlert(xhr.responseJSON?.message || 'Error deleting tag.');
            }
        });
    };
    
    // ══════════════════════════════════════════════════════════
    // EDIT COMMENT
    // ══════════════════════════════════════════════════════════
    
    window.openEditCommentModal = function(commentId) {
        const currentContent = $('#comment-content-' + commentId).text().trim();
        $('#edit-comment-id').val(commentId);
        $('#edit-comment-textarea').val(currentContent);
        openModal('edit-comment-modal');
    };
    
    $('#submit-edit-comment').on('click', function() {
        const commentId = $('#edit-comment-id').val();
        const content = $('#edit-comment-textarea').val().trim();
        const $btn = $(this);
        
        if (!content) return showAlert('Comment cannot be empty.');
        
        $btn.prop('disabled', true).text('Saving...');
        
        $.ajax({
            url: '/api/comment/' + commentId,
            method: 'PUT',
            contentType: 'application/json',
            data: JSON.stringify({ content: content }),
            success: function (res) {
                $btn.prop('disabled', false).text('Save Changes');
                if (res.status === 'success') {
                    $('#comment-content-' + commentId).text(res.content);
                    closeModal('edit-comment-modal');
                }
            },
            error: function (xhr) {
                $btn.prop('disabled', false).text('Save Changes');
                showAlert(xhr.responseJSON?.message || 'Error updating comment.');
            }
        });
    });


    // ══════════════════════════════════════════════════════════
    // PIN COMMENT (via AJAX)
    // ══════════════════════════════════════════════════════════

    window.pinComment = function(commentId, btnEl) {
        $.ajax({
            url: '/api/comment/' + commentId + '/pin',
            method: 'POST',
            success: function (res) {
                if (res.status === 'success') {
                    var $btn = $(btnEl);
                    var $commentItem = $btn.closest('.comment-item');
                    var $bubble = $commentItem.find('.comment-bubble').first();

                    if (res.is_pinned) {
                        $btn.html('📌 Unpin').attr('title', 'Unpin');
                        $bubble.addClass('pinned-comment');
                        // Add pinned indicator if not present
                        if (!$bubble.find('.pinned-indicator').length) {
                            $bubble.prepend('<span class="pinned-indicator" style="font-size:0.72rem; color:var(--accent); font-weight:700; display:block; margin-bottom:0.35rem;">📌 Pinned Comment</span>');
                        }
                        // Move to top of comments list
                        var $commentsList = $('#comments-list');
                        $commentItem.prependTo($commentsList);
                    } else {
                        $btn.html('📌 Pin').attr('title', 'Pin');
                        $bubble.removeClass('pinned-comment');
                        $bubble.find('.pinned-indicator').remove();
                    }
                }
            },
            error: function (xhr) {
                showAlert(xhr.responseJSON?.message || 'Error pinning comment.');
            }
        });
    };


    // ══════════════════════════════════════════════════════════
    // DELETE TOPIC (Double confirmation, via AJAX)
    // ══════════════════════════════════════════════════════════

    window.confirmDeleteTopic = function(topicId) {
        var confirmValue = $('#delete-topic-confirm-input').val();
        if (confirmValue !== 'DELETE') {
            showAlert('You must type DELETE (case-sensitive) to confirm.');
            return;
        }

        var $btn = $('#delete-topic-forever-btn');
        $btn.prop('disabled', true).text('Deleting...');

        $.ajax({
            url: '/api/topic/' + topicId + '/delete',
            method: 'DELETE',
            success: function (res) {
                if (res.status === 'success') {
                    window.location.href = res.redirect || '/';
                }
            },
            error: function (xhr) {
                $btn.prop('disabled', false).text('Delete Forever');
                showAlert(xhr.responseJSON?.message || 'Error deleting topic.');
            }
        });
    };

    // ══════════════════════════════════════════════════════════
    // MEDIA PREVIEW & DELETION (Items 1 & 6)
    // ══════════════════════════════════════════════════════════

    // Preview new selected files
    $('#media-file-input').on('change', function(e) {
        const files = Array.from(e.target.files);
        // Do not empty the existing preview! We append to it.
        const $preview = $('#media-preview');
        
        files.forEach((file, index) => {
            const fileUrl = URL.createObjectURL(file);
            let mediaEl = '';
            if (file.type.startsWith('video/')) {
                mediaEl = `<video src="${fileUrl}"></video>`;
            } else {
                mediaEl = `<img src="${fileUrl}">`;
            }
            
            // For new files, we don't have a DB ID yet. Just an X button to remove it from DOM (and maybe input, but FileList is immutable, so usually it requires complex DataTransfer logic to remove from input. For simplicity, we just preview it here. In a real app we'd manage a separate file list.)
            const html = `
                <div class="media-preview-item new-upload" data-index="${index}">
                    ${mediaEl}
                </div>
            `;
            $preview.append(html);
        });
    });

    // Delete existing media via AJAX
    window.deletePostMedia = function(postId, mediaId) {
        showConfirm('Remove this media from the post?', function() {
            $.ajax({
                url: `/api/post/${postId}/media/${mediaId}`,
                method: 'DELETE',
                success: function(res) {
                    if (res.status === 'success') {
                        $(`#media-item-${mediaId}`).remove();
                    }
                },
                error: function(xhr) {
                    showAlert(xhr.responseJSON?.message || 'Error deleting media');
                }
            });
        });
    };

    // ══════════════════════════════════════════════════════════
    // DELETE ACCOUNT (Double confirmation)
    // ══════════════════════════════════════════════════════════

    window.confirmDeleteAccount = function() {
        var confirmValue = $('#delete-account-confirm-input').val();
        if (confirmValue !== 'DELETE') {
            showAlert('You must type DELETE (case-sensitive) to confirm.');
            return;
        }

        var $btn = $('#delete-account-forever-btn');
        $btn.prop('disabled', true).text('Deleting...');

        $.ajax({
            url: '/auth/delete_account',
            method: 'POST',
            success: function(res) {
                if (res.status === 'success') {
                    window.location.href = res.redirect || '/';
                }
            },
            error: function(xhr) {
                $btn.prop('disabled', false).text('Delete Forever');
                showAlert(xhr.responseJSON?.message || 'Error deleting account.');
            }
        });
    };

    // ══════════════════════════════════════════════════════════
    // REMOVE PROFILE PICTURE (via AJAX)
    // ══════════════════════════════════════════════════════════

    $('#remove-pic-btn').on('click', function() {
        showConfirm('Remove your profile picture?', function() {
            $.ajax({
                url: '/auth/clear_profile_pic',
                method: 'POST',
                // We need CSRF token. Assuming global CSRF token is available or we can get it from another form.
                // Let's get it from the nearest form in the modal.
                data: { csrf_token: $('input[name="csrf_token"]').val() || '' },
                success: function() {
                    location.reload();
                }
            });
        });
    });

});  // end $(document).ready


// ══════════════════════════════════════════════════════════
// LIGHT / DARK MODE TOGGLE
// ══════════════════════════════════════════════════════════

(function() {
    var themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;

    var body = document.body;

    // Apply saved theme on load
    if (localStorage.getItem('theme') === 'light') {
        body.classList.add('light');
        themeToggle.textContent = '☀️';
    } else {
        themeToggle.textContent = '🌙';
    }

    themeToggle.addEventListener('click', function() {
        body.classList.toggle('light');
        var isLight = body.classList.contains('light');
        themeToggle.textContent = isLight ? '☀️' : '🌙';
        localStorage.setItem('theme', isLight ? 'light' : 'dark');
    });
})();
