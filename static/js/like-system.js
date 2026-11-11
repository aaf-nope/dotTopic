/**
 * like-system.js – Like / Dislike Posts and Comments
 * =====================================================
 * Chapter 15: jQuery AJAX calls ($.ajax)
 * Chapter 20: REST API, JSON request/response
 *
 * How it works:
 *   1. User clicks a like or dislike button
 *   2. jQuery sends a POST request to the REST API
 *   3. Server returns JSON with updated counts
 *   4. JavaScript updates the DOM without refreshing the page
 */


$(document).ready(function () {


    // ══════════════════════════════════════════════════════════
    // POST-CARD CLICK → NAVIGATE (replaces inline onclick)
    // The card div now uses data-href instead of onclick so that
    // jQuery can intercept and skip navigation for vote buttons,
    // mod buttons, links, and other interactive elements.
    // ══════════════════════════════════════════════════════════

    $(document).on('click', '.post-card', function (e) {
        // Skip navigation if the click was on (or inside) an interactive element
        const $target = $(e.target);
        if (
            $target.closest('.post-vote-btn').length   ||  // vote buttons
            $target.closest('.mod-btn').length         ||  // pin/delete/edit
            $target.closest('.mod-action-btn').length  ||  // promote/ban
            $target.closest('a').length                ||  // topic/user links
            $target.closest('button').length               // any other button
        ) {
            return;  // Let the element handle its own click
        }

        const href = $(this).data('href');
        if (href) {
            window.location.href = href;
        }
    });

    // ══════════════════════════════════════════════════════════
    // LIKE / DISLIKE A POST
    // ══════════════════════════════════════════════════════════

    /**
     * Click handler for post like/dislike buttons.
     * Uses event delegation so it works on dynamically added buttons too.
     * Chapter 15: jQuery .on() with event delegation
     */
    $(document).on('click', '.post-vote-btn', function (e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();

        const $btn    = $(this);
        const postId  = $btn.data('post-id');    // e.g. 3
        const value   = $btn.data('value');       // +1 for like, -1 for dislike

        // Find the container for the like/dislike counts
        const $voteGroup = $btn.closest('.vote-group');

        // ── Send AJAX request to the REST API ─────────────────

        $.ajax({
            url        : '/api/post/' + postId + '/like',
            method     : 'POST',
            contentType: 'application/json',
            data       : JSON.stringify({ value: value }),  // Send as JSON

            // ── On success: update the count in the DOM ───────
            success: function (response) {
                if (response.status === 'success') {

                    // Update the displayed counts
                    $voteGroup.find('.like-count').text(response.likes_count);
                    $voteGroup.find('.dislike-count').text(response.dislikes_count);

                    // Toggle button active styles
                    $voteGroup.find('.post-vote-btn').removeClass('liked disliked');

                    if (response.user_vote === 1) {
                        $voteGroup.find('[data-value="1"]').addClass('liked');
                    } else if (response.user_vote === -1) {
                        $voteGroup.find('[data-value="-1"]').addClass('disliked');
                    }

                    // Small animation on the button
                    $btn.addClass('pulse-once');
                    setTimeout(function () {
                        $btn.removeClass('pulse-once');
                    }, 350);
                }
            },

            // ── On error: show a simple alert ─────────────────
            error: function (xhr) {
                if (xhr.status === 401) {
                    // User is not logged in – open the auth modal
                    openModal('auth-modal');
                } else {
                    console.error('Like failed:', xhr.responseJSON);
                }
            }
        });
    });


    // ══════════════════════════════════════════════════════════
    // LIKE / DISLIKE A COMMENT
    // ══════════════════════════════════════════════════════════

    /**
     * Click handler for comment like/dislike buttons.
     * Same logic as post likes, but calls a different API endpoint.
     */
    $(document).on('click', '.comment-vote-btn', function (e) {
        e.preventDefault();
        e.stopPropagation();

        const $btn      = $(this);
        const commentId = $btn.data('comment-id');
        const value     = $btn.data('value');         // +1 or -1

        const $commentBubble = $btn.closest('.comment-bubble');

        $.ajax({
            url        : '/api/comment/' + commentId + '/like',
            method     : 'POST',
            contentType: 'application/json',
            data       : JSON.stringify({ value: value }),

            success: function (response) {
                if (response.status === 'success') {

                    // Update displayed counts
                    $commentBubble.find('.comment-like-count').text(response.likes_count);
                    $commentBubble.find('.comment-dislike-count').text(response.dislikes_count);

                    // Toggle active class on the buttons
                    $commentBubble.find('.comment-vote-btn').removeClass('liked disliked');

                    if (response.user_vote === 1) {
                        $commentBubble.find('[data-value="1"]').addClass('liked');
                    } else if (response.user_vote === -1) {
                        $commentBubble.find('[data-value="-1"]').addClass('disliked');
                    }
                }
            },

            error: function (xhr) {
                if (xhr.status === 401) {
                    openModal('auth-modal');
                }
            }
        });
    });


    // ══════════════════════════════════════════════════════════
    // DELETE POST (via AJAX)
    // Chapter 15: jQuery $.ajax with method DELETE
    // ══════════════════════════════════════════════════════════

    /**
     * Called when the user clicks "Delete" on a post card.
     * Shows a confirmation modal, then sends DELETE to the API.
     * On success, the post card fades out and is removed from the DOM.
     *
     * @param {number} postId   - The ID of the post to delete
     * @param {Element} cardEl  - The .post-card DOM element to remove
     */
    window.confirmDeletePost = function (postId, cardEl) {
        showConfirm('Are you sure you want to delete this post? This cannot be undone.', function () {

            $.ajax({
                url   : '/api/post/' + postId,
                method: 'DELETE',

                success: function (response) {
                    if (response.status === 'success') {
                        // Fade out and remove the card from the page
                        $(cardEl).closest('.post-card').fadeOut(350, function () {
                            $(this).remove();
                        });
                    }
                },

                error: function (xhr) {
                    showAlert('Could not delete post: ' + (xhr.responseJSON?.message || 'Server error'));
                }
            });
        });
    };


    // ══════════════════════════════════════════════════════════
    // PIN / UNPIN POST (via AJAX)
    // ══════════════════════════════════════════════════════════

    /**
     * Toggle the pinned state of a post.
     * Updates the pin badge and button text in the DOM.
     * @param {number} postId  - The post ID
     * @param {Element} btnEl  - The pin button element
     */
    window.togglePinPost = function (postId, btnEl) {
        $.ajax({
            url   : '/api/post/' + postId + '/pin',
            method: 'POST',

            success: function (response) {
                if (response.status === 'success') {
                    const $card = $(btnEl).closest('.post-card');
                    const $btn  = $(btnEl);

                    if (response.is_pinned) {
                        $card.addClass('pinned');
                        $card.find('.pin-badge').show();
                        $btn.text('Unpin');
                    } else {
                        $card.removeClass('pinned');
                        $card.find('.pin-badge').hide();
                        $btn.text('Pin');
                    }
                }
            },

            error: function (xhr) {
                console.error('Pin failed:', xhr.responseJSON);
            }
        });
    };

});  // end $(document).ready
