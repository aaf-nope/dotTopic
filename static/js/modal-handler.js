/**
 * modal-handler.js – Open / Close Modal Popups
 * ===============================================
 * Chapters 10-14: DOM manipulation, event handling, classList.
 * Chapter 15: jQuery for DOM queries and event binding.
 *
 * This file controls:
 *   - Opening and closing all modals (login, register, post, account)
 *   - Switching between Login / Register tabs
 *   - Switching between Account Settings tabs
 *   - Pre-filling the post modal for editing
 *   - Closing modals when clicking the overlay or pressing ESC
 */


// ── Wait for the DOM to be fully loaded before attaching events ──

$(document).ready(function () {

    // ══════════════════════════════════════════════════════════
    // OPEN MODAL FUNCTION
    // ══════════════════════════════════════════════════════════

    /**
     * Open a modal by its ID.
     * Adds the 'open' class to show it (CSS handles the display).
     * @param {string} modalId - The HTML id of the .modal-overlay element
     */
    window.openModal = function (modalId) {
        $('#' + modalId).addClass('open');
        $('body').css('overflow', 'hidden');  // Prevent background scrolling
    };


    // ══════════════════════════════════════════════════════════
    // CLOSE MODAL FUNCTION
    // ══════════════════════════════════════════════════════════

    /**
     * Close a modal by its ID.
     * Removes the 'open' class to hide it.
     * @param {string} modalId - The HTML id of the .modal-overlay element
     */
    window.closeModal = function (modalId) {
        $('#' + modalId).removeClass('open');
        $('body').css('overflow', '');  // Restore scrolling
    };


    // ══════════════════════════════════════════════════════════
    // CLOSE WHEN CLICKING THE OVERLAY BACKGROUND
    // Chapter 11: Event handling – detecting click target
    // ══════════════════════════════════════════════════════════

    $('.modal-overlay').on('click', function (event) {
        // Only close if the user clicked the dark overlay itself,
        // NOT the white modal box inside it
        if ($(event.target).hasClass('modal-overlay')) {
            $(this).removeClass('open');
            $('body').css('overflow', '');
        }
    });


    // ══════════════════════════════════════════════════════════
    // CLOSE WITH ESC KEY
    // Chapter 11: Keyboard events
    // ══════════════════════════════════════════════════════════

    $(document).on('keydown', function (event) {
        if (event.key === 'Escape') {
            // Close any open modal
            $('.modal-overlay.open').removeClass('open');
            $('body').css('overflow', '');
        }
    });


    // ══════════════════════════════════════════════════════════
    // LOGIN / REGISTER TAB SWITCHER
    // Chapter 11: Click events, Chapter 12: classList manipulation
    // ══════════════════════════════════════════════════════════

    $('.auth-tab-btn').on('click', function () {
        const targetPanel = $(this).data('panel');  // e.g. 'login' or 'register'

        // Update active tab button
        $('.auth-tab-btn').removeClass('active');
        $(this).addClass('active');

        // Show the correct form panel, hide others
        $('.auth-form-panel').removeClass('active');
        $('#panel-' + targetPanel).addClass('active');
    });


    // ══════════════════════════════════════════════════════════
    // ACCOUNT SETTINGS TAB SWITCHER
    // ══════════════════════════════════════════════════════════

    $('.settings-tab-btn').on('click', function () {
        const targetPanel = $(this).data('panel');

        // Update active tab button
        $('.settings-tab-btn').removeClass('active');
        $(this).addClass('active');

        // Show the correct settings panel
        $('.settings-panel').removeClass('active');
        $('#settings-' + targetPanel).addClass('active');
    });


    // ══════════════════════════════════════════════════════════
    // PROFILE DROPDOWN TOGGLE
    // ══════════════════════════════════════════════════════════

    $('#profile-toggle').on('click', function (event) {
        event.stopPropagation();  // Prevent the document click from closing it
        $('#profile-dropdown').toggleClass('open');
    });

    // Close dropdown when clicking anywhere else on the page
    $(document).on('click', function () {
        $('#profile-dropdown').removeClass('open');
    });


    // ══════════════════════════════════════════════════════════
    // FLASH MESSAGE AUTO-DISMISS
    // Chapter 11: setTimeout, jQuery .fadeOut()
    // ══════════════════════════════════════════════════════════

    // Close button on flash messages
    $('.close-flash').on('click', function () {
        $(this).closest('.flash-message').slideUp(250);
    });

    // Auto-dismiss success/info messages after 4 seconds
    setTimeout(function () {
        $('.flash-success, .flash-info').slideUp(500);
    }, 4000);


    // ══════════════════════════════════════════════════════════
    // STRICT MEDIA PREVIEW & DELETION SYSTEM
    // ══════════════════════════════════════════════════════════
    
    // Global array to persist selected files while modal is open
    window.pendingFiles = [];

    // ══════════════════════════════════════════════════════════
    // TAG PILL SELECTION SYSTEM
    // ══════════════════════════════════════════════════════════
    // Global array for selected tag IDs
    window.selectedTagIds = [];

    // Reset when modal opens
    function resetTagSelection() {
        window.selectedTagIds = [];
        $('.tag-pill').removeClass('selected');
    }

    // Click handler – use event delegation so it always works
    $(document).on('click', '#post-modal .tag-pill', function(e) {
        e.preventDefault();
        const $pill = $(this);
        const tagId = parseInt($pill.attr('data-tag-id'));
        
        $pill.toggleClass('selected');
        
        if ($pill.hasClass('selected')) {
            if (!window.selectedTagIds.includes(tagId)) {
                window.selectedTagIds.push(tagId);
            }
        } else {
            window.selectedTagIds = window.selectedTagIds.filter(id => id !== tagId);
        }
    });

    function preselectTagPills(tagIds) {
        resetTagSelection();
        if (!tagIds || !Array.isArray(tagIds)) return;
        tagIds.forEach(id => {
            window.selectedTagIds.push(id);
            $(`.tag-pill[data-tag-id="${id}"]`).addClass('selected');
        });
    }

    function renderPendingPreviews() {
        const $preview = $('#new-media-preview');
        $preview.empty();
        
        window.pendingFiles.forEach((file, index) => {
            const fileUrl = URL.createObjectURL(file);
            let mediaEl = '';
            if (file.type.startsWith('video/')) {
                mediaEl = `<video src="${fileUrl}" style="width: 100px; height: 100px; object-fit: cover;"></video>`;
            } else {
                mediaEl = `<img src="${fileUrl}" style="width: 100px; height: 100px; object-fit: cover;">`;
            }
            
            const html = `
                <div class="media-preview-item new-upload" style="position: relative;">
                    ${mediaEl}
                    <button type="button" class="remove-pending btn-danger" data-index="${index}" style="position: absolute; top: 2px; right: 2px; padding: 0 4px; font-size: 10px;">✕</button>
                </div>
            `;
            $preview.append(html);
        });
    }

    $(document).on('change', '#media-input', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        window.pendingFiles.push(file);
        $(this).val('');   // clear input so same file can be re-selected
        renderPendingPreviews();
    });

    $(document).on('click', '.remove-pending', function() {
        const idx = parseInt($(this).data('index'));
        window.pendingFiles.splice(idx, 1);
        renderPendingPreviews();  // refresh indices
    });

    $(document).on('click', '.remove-existing', function() {
        const mediaId = $(this).data('media-id');
        const postId = $(this).data('post-id');
        const $btn = $(this);
        
        $.ajax({
            url: `/api/post/${postId}/media/${mediaId}`,
            method: 'DELETE',
            success: function(res) {
                if (res.status === 'success') {
                    $btn.closest('.existing-thumb').remove();
                }
            },
            error: function(xhr) {
                showAlert(xhr.responseJSON?.message || 'Error deleting media');
            }
        });
    });

    $('#post-form').on('submit', function(e) {
        e.preventDefault();
        
        const $form = $(this);
        const url = $form.attr('action');
        
        // Build FormData
        const formData = new FormData();
        formData.append('title', $('#post-title-input').val());
        formData.append('content', $('#post-content-input').val());
        
        // Append tags as JSON string from pill selector
        formData.append('tags', JSON.stringify(window.selectedTagIds));
        
        // Send list of remaining existing media IDs (for edit mode)
        const remainingMediaIds = [];
        $('#existing-media .existing-thumb').each(function() {
            const id = $(this).data('media-id');
            if (id) remainingMediaIds.push(parseInt(id));
        });
        formData.append('existing_media_ids', JSON.stringify(remainingMediaIds));
        
        // Append all pending files
        window.pendingFiles.forEach(file => formData.append('media', file));
        
        const $submitBtn = $form.find('button[type="submit"]');
        $submitBtn.prop('disabled', true).text('Saving...');
        
        $.ajax({
            url: url,
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(res) {
                if (res.status === 'success') {
                    closeModal('post-modal');
                    window.location.href = res.post_url || window.location.href;
                }
            },
            error: function(xhr) {
                $submitBtn.prop('disabled', false).text('Submit');
                console.error("Save post error:", xhr.responseText);
                const msg = xhr.responseJSON?.message || 'Error saving post.';
                showAlert(msg);
            }
        });
    });

    // ══════════════════════════════════════════════════════════
    // PRE-FILL POST MODAL FOR EDITING
    // ══════════════════════════════════════════════════════════

    /**
     * Open the post modal in EDIT mode, pre-filled with existing post data.
     * Data is stored as data-* attributes on the edit button.
     *
     * @param {Element} btn - The button element with data-* attributes
     */
    window.openEditModal = function (btn) {
        const $btn = $(btn);

        // Read the post data from the button's data attributes
        const postId   = $btn.data('post-id');
        const title    = $btn.data('post-title');
        const content  = $btn.data('post-content');
        const topicName = $btn.data('topic-name');
        const media    = $btn.data('media') || [];

        // Update modal title
        $('#post-modal-title').text('Edit Post');

        // Pre-fill the form fields
        $('#post-title-input').val(title);
        $('#post-content-input').val(content);

        // Update the form action to point to the edit endpoint
        $('#post-form').attr(
            'action',
            '/t/' + topicName + '/post/' + postId + '/edit'
        );

        // Pre-select tag pills for this post's existing tags
        const tagIds = $btn.data('tag-ids') || [];
        preselectTagPills(tagIds);

        // Reset pending files
        window.pendingFiles = [];
        $('#new-media-preview').empty();

        // Render existing media previews
        const $existingPreview = $('#existing-media');
        $existingPreview.empty();
        media.forEach(m => {
            let mediaEl = '';
            if (m.type === 'video') {
                mediaEl = `<video src="/static/${m.file_path}" style="width: 100px; height: 100px; object-fit: cover;"></video>`;
            } else {
                mediaEl = `<img src="/static/${m.file_path}" style="width: 100px; height: 100px; object-fit: cover;">`;
            }
            $existingPreview.append(`
                <div class="existing-thumb" data-media-id="${m.id}" style="position: relative;">
                    ${mediaEl}
                    <button type="button" class="remove-existing btn-danger" data-post-id="${postId}" data-media-id="${m.id}" style="position: absolute; top: 2px; right: 2px; padding: 0 4px; font-size: 10px;">✕</button>
                </div>
            `);
        });

        // Open the modal
        openModal('post-modal');
    };


    /**
     * Open the post modal in CREATE mode (empty form).
     * @param {string} topicName - The topic to post in
     */
    window.openCreatePostModal = function (topicName) {
        // Reset modal title and form
        $('#post-modal-title').text('Create Post');
        $('#post-form')[0].reset();

        // Clear media previews
        window.pendingFiles = [];
        $('#new-media-preview').empty();
        $('#existing-media').empty();

        // Set form action to create endpoint
        $('#post-form').attr('action', '/t/' + topicName + '/post/new');

        // Reset tag pills
        resetTagSelection();

        // Reset submit button text
        $('#post-form').find('button[type="submit"]').prop('disabled', false).text('Submit');

        openModal('post-modal');
    };


    // ══════════════════════════════════════════════════════════
    // CONFIRM DELETE MODAL
    // ══════════════════════════════════════════════════════════

    // Store the callback function for when confirm is clicked
    let _confirmCallback = null;

    /**
     * Show the confirmation modal with a custom message.
     * @param {string} message  - Text shown in the modal
     * @param {Function} onConfirm - Called when the user clicks "Delete"
     */
    window.showConfirm = function (message, onConfirm) {
        $('#confirm-modal-message').text(message);
        _confirmCallback = onConfirm;
        openModal('confirm-modal');
    };

    // Confirm button in the modal
    $('#confirm-modal-yes').on('click', function () {
        closeModal('confirm-modal');
        if (typeof _confirmCallback === 'function') {
            _confirmCallback();
        }
        _confirmCallback = null;
    });

    // Cancel button
    $('#confirm-modal-no').on('click', function () {
        closeModal('confirm-modal');
        _confirmCallback = null;
    });

    // ══════════════════════════════════════════════════════════
    // ALERT MODAL
    // ══════════════════════════════════════════════════════════

    /**
     * Show the alert modal with a custom message.
     * @param {string} message  - Text shown in the modal
     */
    window.showAlert = function (message) {
        $('#alert-modal-message').text(message);
        openModal('alert-modal');
    };

});  // end $(document).ready
