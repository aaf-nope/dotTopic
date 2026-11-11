# dotTopic – Project Documentation

dotTopic is a Reddit-style community forum built with Flask (Python).
Users can create topics, post content, comment, vote, and moderate communities.

---

## Technology Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Backend    | Python 3, Flask, Flask-Login, Flask-WTF (CSRF)  |
| Database   | SQLite via SQLAlchemy ORM                        |
| Templating | Jinja2 (server-side HTML rendering)              |
| Frontend   | Vanilla HTML/CSS + jQuery AJAX                  |
| Auth       | Flask-Login (session cookies, password hashing) |

---

## Project File Structure

```
dottopic/
+-- app.py              – Creates and configures the Flask app
+-- config.py           – All configuration settings (DB, uploads, secrets)
+-- models.py           – SQLAlchemy database models (tables)
+-- seed.py             – Populates the database with sample data
+-- requirements.txt    – Python package dependencies
+-- DOCS.md             – This file
|
+-- routes/
|   +-- __init__.py     – Makes routes/ a Python package
|   +-- main.py         – Home page and search
|   +-- auth.py         – Login, register, logout, account deletion
|   +-- topics.py       – Topic pages, posts, moderation
|   +-- users.py        – User profile and account settings
|   +-- api.py          – REST API endpoints (AJAX-driven features)
|
+-- templates/
|   +-- base.html       – Master layout (header, nav, modals)
|   +-- home.html       – Home feed page
|   +-- topic.html      – Individual topic page with posts
|   +-- post_detail.html – Single post with comment thread
|   +-- user.html       – User profile page
|   +-- create_topic.html – Create a new topic form
|   +-- search.html     – Search results page
|   +-- partials/
|       +-- post_card.html      – Reusable post preview card
|       +-- comment_thread.html – Recursive comment + replies
|       +-- modals/
|           +-- login_modal.html    – Login / Register modal
|           +-- account_modal.html  – Account settings modal
|           +-- post_modal.html     – Create / Edit post modal
|           +-- alert_modal.html    – Styled alert dialog
|           +-- confirm_modal.html  – Styled confirmation dialog
|
+-- static/
    +-- default_pfp.png     – Default user avatar
    +-- default_topic.png   – Default topic icon
    +-- default_banner.png  – Default topic banner
    +-- css/
    |   +-- style.css       – All main application styles
    |   +-- modals.css      – Modal-specific styles
    +-- js/
    |   +-- main.js         – Core AJAX interactions (posts, comments, tags, moderation)
    |   +-- modal-handler.js – Opens/closes all modals, handles forms inside them
    |   +-- like-system.js  – Like/dislike voting for posts and comments
    |   +-- subscribe.js    – Topic subscription toggle
    +-- uploads/            – User-uploaded images and videos
```

---

## Request → Response Cycle

1. User opens a URL in their browser (e.g. /t/gaming).
2. Flask receives the request and matches it to a route in one of the routes/ files.
3. The route function queries the database using SQLAlchemy models.
4. The function calls render_template(), passing data to a Jinja2 .html template.
5. Jinja2 fills in the template with the data and sends the final HTML back to the browser.
6. The browser loads static assets (CSS, JS) from /static/.
7. JavaScript (jQuery) attaches event listeners for dynamic features (likes, comments, moderation).
8. When the user clicks a button (e.g. Like), jQuery sends a background AJAX request to /api/...
9. The API route returns JSON, and jQuery updates the page without a full reload.

---

## Database Models & Relationships

    User  --< Post --< Comment
              |  `--< PostMedia
              |
              `--< LikeDislike (on Post)

    Comment --< LikeDislike (on Comment)
            `--< Comment (replies, depth 2 max)

    Topic --< Post
          --< Subscription (User to Topic)
          --< Moderator (User to Topic)
          --< BannedUser (User to Topic)
          --< Tag
              `-- Post --< post_tags (many-to-many junction)

### Key Relationships
- A User can create many Posts and Comments.
- A Topic has one creator (User) and can have many Moderators (Users).
- A Post belongs to one Topic and one User (author).
- Subscriptions track which users follow which topics.
- LikeDislike records store one vote per user per post/comment (+1 like, -1 dislike).
- Tags belong to a Topic; Posts can have multiple Tags (many-to-many via post_tags).

---

## Role Hierarchy

    Super Admin  (is_super_admin=True)
        |  Can do everything anywhere on the site
        |
    Topic Creator  (topic.creator_id == user.id)
        |  Full control of their own topic
        |
    Topic Moderator  (Moderator table entry)
        |  Can pin/delete posts, ban users, add tags within a topic
        |
    Subscriber  (Subscription table entry)
        |  Can post, comment, vote
        |
    Visitor (not logged in)
           Can only read public content

The helper method user.can_moderate(topic) returns True if the user is the
creator, a moderator, or the super admin — used throughout routes and API.

---

## Key Feature Flows

### Creating a Post
1. User clicks "New Post" on a topic page → the create post modal opens.
2. User fills in title, content, tags, optional media → clicks Submit.
3. main.js sends a POST to /api/topic/<id>/post via jQuery AJAX.
4. The API validates, creates a Post record, and returns JSON.
5. jQuery injects the new post card at the top of the feed without a page reload.

### Pinning / Deleting a Post
1. Moderator clicks Pin or Delete on a post card.
2. post_card.html inline onclick calls togglePinPost() or confirmDeletePost().
3. confirmDeletePost() shows a styled confirmation modal first.
4. On confirm, jQuery sends POST /api/post/<id>/pin or DELETE /api/post/<id>.
5. The API checks permissions and updates the database.
6. jQuery updates the card appearance or removes it from the DOM.

### Banning a User
1. Moderator clicks Ban on a user in the topic mod panel.
2. A ban reason modal appears.
3. On confirm, jQuery sends POST /api/topic/<id>/ban with {user_id, reason}.
4. API creates a BannedUser record, preventing that user from posting/commenting.

### Voting (Like / Dislike)
1. User clicks like or dislike button on a post or comment.
2. like-system.js sends POST /api/post/<id>/like with {value: 1 or -1}.
3. API toggles the vote and returns updated counts as JSON.
4. jQuery updates the counter in the DOM immediately.

### Subscribing to a Topic
1. User clicks Subscribe/Unsubscribe button on a topic page.
2. subscribe.js sends POST /api/topic/<id>/subscribe.
3. Button text and subscriber count update instantly via jQuery.

---

## Image Defaults

All user and topic images always have a valid filename stored in the database.
Default files live directly in static/ (not in a subfolder):
- default_pfp.png    – shown when a user has no custom avatar
- default_topic.png  – shown when a topic has no custom icon
- default_banner.png – shown when a topic has no custom banner

---

## Running the App

    # Install dependencies
    pip install -r requirements.txt

    # (Re)seed the database with sample data
    python seed.py

    # Start the development server
    python app.py
    # Visit http://127.0.0.1:5000

Default seed accounts (all passwords: password123):
- admin / admin123 — super admin
- game_master, movie_buff, book_worm, music_lover, tech_guru, etc.
