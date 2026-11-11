/**
 * subscribe.js – Topic Subscription Toggle
 * ==========================================
 * Chapter 15: jQuery AJAX ($.ajax)
 * Chapter 20: REST API, JSON
 *
 * When a user clicks the Subscribe button:
 *   1. AJAX POST sent to /api/topic/<id>/subscribe
 *   2. Server toggles the subscription in the DB
 *   3. Button text/style updates without page reload
 */


$(document).ready(function () {

    // ══════════════════════════════════════════════════════════
    // SUBSCRIBE / UNSUBSCRIBE BUTTON
    // ══════════════════════════════════════════════════════════

    $('#subscribe-btn').on('click', function () {

        const $btn    = $(this);
        const topicId = $btn.data('topic-id');  // Set as data-topic-id on the button

        // Disable the button while the request is in progress
        $btn.prop('disabled', true);

        // ── Send AJAX POST to the subscribe API endpoint ──────

        $.ajax({
            url   : '/api/topic/' + topicId + '/subscribe',
            method: 'POST',

            // ── On success: update the button ─────────────────
            success: function (response) {
                $btn.prop('disabled', false);

                if (response.status === 'subscribed') {
                    // User just subscribed
                    $btn.text('✓ Subscribed');
                    $btn.addClass('subscribed');
                    $btn.addClass('pulse-once');

                } else if (response.status === 'unsubscribed') {
                    // User just unsubscribed
                    $btn.text('+ Subscribe');
                    $btn.removeClass('subscribed');
                }

                // Update subscriber count if displayed on page
                if (response.subscriber_count !== undefined) {
                    $('#subscriber-count').text(response.subscriber_count + ' members');
                }
                // Auto-refresh page after a short delay to show updated subscribe state
                setTimeout(() => location.reload(), 500);

                // Remove pulse animation class after it plays
                setTimeout(function () {
                    $btn.removeClass('pulse-once');
                }, 350);
            },

            // ── On error: check if user is logged in ──────────
            error: function (xhr) {
                $btn.prop('disabled', false);

                if (xhr.status === 401) {
                    // Not logged in → open the auth modal
                    openModal('auth-modal');
                } else {
                    console.error('Subscribe failed:', xhr.responseJSON?.message);
                }
            }
        });

    });

});  // end $(document).ready
