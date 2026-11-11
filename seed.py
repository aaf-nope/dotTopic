"""
seed.py
Purpose: Handles logic for seed.py
"""
import random
from datetime import datetime, timedelta
from app import app, db
from models import User, Topic, Post, Comment, Tag, LikeDislike, Subscription, Moderator, BannedUser, PostMedia
from werkzeug.security import generate_password_hash

def seed():
    """Handler for seed."""
    with app.app_context():
        print("Clearing database...")
        db.drop_all()
        db.create_all()
        
        print("Creating users...")
        
        # 1. USERS
        users_data = [
            {"username": "admin", "email": "admin@dottopic.com", "password": "admin123", "is_super_admin": True},
            {"username": "tech_guru", "email": "tech@email.com", "password": "password123", "is_super_admin": False},
            {"username": "game_master", "email": "game@email.com", "password": "password123", "is_super_admin": False},
            {"username": "movie_buff", "email": "movie@email.com", "password": "password123", "is_super_admin": False},
            {"username": "book_worm", "email": "book@email.com", "password": "password123", "is_super_admin": False},
            {"username": "music_lover", "email": "music@email.com", "password": "password123", "is_super_admin": False},
            {"username": "art_enthusiast", "email": "art@email.com", "password": "password123", "is_super_admin": False},
            {"username": "science_nerd", "email": "science@email.com", "password": "password123", "is_super_admin": False},
        ]
        
        user_objects = {}
        for u_data in users_data:
            user = User(
                username=u_data["username"],
                email=u_data["email"],
                is_super_admin=u_data["is_super_admin"],
                profile_pic='default_pfp.png'
            )
            user.set_password(u_data["password"])
            db.session.add(user)
            user_objects[user.username] = user
        
        db.session.commit()
        
        print("Creating topics...")
        
        # 2. TOPICS
        topics_data = [
            {
                "name": "gaming",
                "creator": "game_master",
                "description": "The hub for all things gaming. From retro classics to modern masterpieces, PC to console, indie gems to AAA blockbusters. Share your gameplay, reviews, and gaming news.",
                "banner": "gaming_banner.png",
                "moderators": ["tech_guru"],
                "tags": ["Review", "News", "Discussion", "Help", "Screenshot", "Video", "Retro", "Indie"],
                "subscribers": ["tech_guru", "game_master", "movie_buff", "book_worm", "music_lover", "art_enthusiast", "science_nerd"]
            },
            {
                "name": "movies",
                "creator": "movie_buff",
                "description": "Lights, camera, discussion! Talk about the latest blockbusters, hidden gems, classic films, directors, actors, and everything cinema.",
                "banner": "movies_banner.png",
                "moderators": [],
                "tags": ["Review", "News", "Discussion", "Recommendation", "Spoiler", "Classic", "Trailer"],
                "subscribers": ["tech_guru", "movie_buff", "book_worm", "music_lover", "art_enthusiast"]
            },
            {
                "name": "books",
                "creator": "book_worm",
                "description": "A cozy corner for book lovers. Discuss your favorite novels, share reading recommendations, and join book discussions. Fiction, non-fiction, and everything in between.",
                "banner": "books_banner.png",
                "moderators": [],
                "tags": ["Review", "Discussion", "Recommendation", "Spoiler", "Fiction", "Non-Fiction", "Currently Reading"],
                "subscribers": ["tech_guru", "book_worm", "movie_buff", "science_nerd"]
            },
            {
                "name": "music",
                "creator": "music_lover",
                "description": "Share your favorite tracks, discover new artists, discuss albums, and talk about concerts. All genres welcome - from classical to hip-hop.",
                "banner": "music_banner.png",
                "moderators": ["art_enthusiast"],
                "tags": ["Review", "Discussion", "Recommendation", "New Release", "Concert", "Playlist", "Genre Discussion"],
                "subscribers": ["tech_guru", "game_master", "movie_buff", "book_worm", "music_lover", "art_enthusiast", "science_nerd"]
            },
            {
                "name": "art",
                "creator": "art_enthusiast",
                "description": "A creative space for artists and art lovers. Share your artwork, discuss techniques, get feedback, and explore different art styles and mediums.",
                "banner": "art_banner.png",
                "moderators": [],
                "tags": ["Showcase", "Feedback", "Digital Art", "Traditional", "Photography", "Tutorial", "Discussion"],
                "subscribers": ["tech_guru", "art_enthusiast", "music_lover", "book_worm"]
            },
            {
                "name": "science",
                "creator": "science_nerd",
                "description": "Explore the wonders of science! From physics to biology, astronomy to chemistry. Share interesting articles, ask questions, and discuss the latest discoveries.",
                "banner": "science_banner.png",
                "moderators": ["tech_guru"],
                "tags": ["Discussion", "News", "Question", "Article", "Physics", "Biology", "Space", "Technology"],
                "subscribers": ["tech_guru", "science_nerd", "book_worm", "game_master"]
            }
        ]
        
        topic_objects = {}
        tag_objects_by_topic = {}
        
        for t_data in topics_data:
            topic = Topic(
                name=t_data["name"],
                description=t_data["description"],
                photo="default_topic.png",
                banner="default_banner.png",
                creator_id=user_objects[t_data["creator"]].id
            )
            db.session.add(topic)
            db.session.commit()
            topic_objects[t_data["name"]] = topic
            
            # Tags
            tag_objects_by_topic[topic.id] = []
            for tag_name in t_data["tags"]:
                tag = Tag(name=tag_name, topic_id=topic.id)
                db.session.add(tag)
                tag_objects_by_topic[topic.id].append(tag)
            
            # Subscribers
            print(f"Subscribing users to .{topic.name}...")
            for sub_username in t_data["subscribers"]:
                sub = Subscription(user_id=user_objects[sub_username].id, topic_id=topic.id)
                db.session.add(sub)
                
            # Moderators
            print(f"Assigning moderators for .{topic.name}...")
            for mod_username in t_data["moderators"]:
                mod = Moderator(user_id=user_objects[mod_username].id, topic_id=topic.id)
                db.session.add(mod)
        
        db.session.commit()
        
        print("Creating posts...")
        
        # 3. POSTS
        now = datetime.utcnow()
        posts_data = [
            {
                "topic": "gaming",
                "title": "Welcome to .gaming! Read this first",
                "content": "Welcome everyone to the gaming community! Here's what you need to know: Feel free to share your gaming experiences, post reviews, ask for help, or just discuss your favorite games. Please keep things civil and use appropriate tags when posting. Game on!\n- Your mod team",
                "author": "game_master",
                "tags": ["Discussion"],
                "days_ago": 14,
                "is_pinned": True
            },
            {
                "topic": "gaming",
                "title": "Just finished Elden Ring - My thoughts",
                "content": "After 120 hours, I finally finished Elden Ring and wow, what a journey. The open world design is incredible, every corner hides something new. The boss fights are challenging but fair (except Malenia, we don't talk about her). The lore is deep and mysterious as expected from FromSoftware.\n\nWhat did you all think? Any tips for NG+?",
                "author": "tech_guru",
                "tags": ["Review", "Discussion"],
                "days_ago": 5,
                "is_pinned": False
            },
            {
                "topic": "gaming",
                "title": "Best indie games of 2026 so far?",
                "content": "I've been exploring some amazing indie games lately and wanted to share my favorites: Hades 2 has been incredible, the combat feels even better than the original. Another gem I found is Animal Well - the pixel art and puzzles are mind-blowing.\n\nWhat indie games are you playing? Always looking for recommendations!",
                "author": "music_lover",
                "tags": ["Discussion", "Indie", "Recommendation"],
                "days_ago": 2,
                "is_pinned": False
            },
            {
                "topic": "movies",
                "title": "Dune Part 3 announced - Release date revealed",
                "content": "Denis Villeneuve just confirmed Dune Part 3 is in production! Based on Dune Messiah, it'll be fascinating to see how they handle the time jump and Paul's arc. The cast is returning with some new additions.\n\nExpected release: late 2027. What are your expectations?",
                "author": "movie_buff",
                "tags": ["News", "Discussion"],
                "days_ago": 7,
                "is_pinned": True
            },
            {
                "topic": "movies",
                "title": "Underrated movies that deserve more love",
                "content": "I recently watched 'The Fall' (2006) and I can't believe it's not more popular. The visuals are absolutely stunning, filmed in over 20 countries with no CGI. The storytelling is unique and emotional.\n\nWhat's your favorite underrated movie? Let's build a watchlist together.",
                "author": "book_worm",
                "tags": ["Recommendation", "Discussion"],
                "days_ago": 3,
                "is_pinned": False
            },
            {
                "topic": "movies",
                "title": "Thoughts on the new Matrix reboot?",
                "content": "So they are rebooting the Matrix again. I'm honestly not sure how I feel about it. The original trilogy was groundbreaking, and Resurrections was divisive. Do we really need another one? Let's discuss.",
                "author": "tech_guru",
                "tags": ["Discussion", "News"],
                "days_ago": 1,
                "is_pinned": False
            },
            {
                "topic": "books",
                "title": "Welcome to .books! Community Guidelines",
                "content": "Welcome to .books! We are a community of readers. Please be respectful of others' opinions. Use spoiler tags when discussing plot points. Share your favorite books and let's read together!",
                "author": "book_worm",
                "tags": ["Discussion"],
                "days_ago": 10,
                "is_pinned": True
            },
            {
                "topic": "books",
                "title": "Project Hail Mary - A must read for sci-fi fans",
                "content": "I just finished Project Hail Mary by Andy Weir. It's fantastic! If you loved The Martian, you'll love this. The science is fascinating, and the relationship between Grace and Rocky is so well written. Highly recommend!",
                "author": "science_nerd",
                "tags": ["Review", "Recommendation", "Fiction"],
                "days_ago": 4,
                "is_pinned": False
            },
            {
                "topic": "books",
                "title": "What are you currently reading?",
                "content": "I'm looking for some inspiration. What is everyone reading right now? I'm currently diving into some historical non-fiction about the Roman Empire. Let me know your current reads in the comments!",
                "author": "movie_buff",
                "tags": ["Currently Reading", "Discussion"],
                "days_ago": 1,
                "is_pinned": False
            },
            {
                "topic": "music",
                "title": "Welcome to .music! Introduce yourselves",
                "content": "Welcome to the music hub! Introduce yourselves, what are your favorite genres? Favorite bands? We are open to all types of music here. Let's share some great tracks!",
                "author": "music_lover",
                "tags": ["Discussion"],
                "days_ago": 12,
                "is_pinned": True
            },
            {
                "topic": "music",
                "title": "The new Kendrick album is a masterpiece",
                "content": "I've had the new Kendrick Lamar album on repeat for the past week. The production is insane, and the lyricism is unmatched as always. What are your favorite tracks so far?",
                "author": "game_master",
                "tags": ["Review", "New Release", "Discussion"],
                "days_ago": 6,
                "is_pinned": False
            },
            {
                "topic": "music",
                "title": "Need recommendations for focus music",
                "content": "I'm working on a big project and need some good background music to help me focus. I usually listen to lo-fi hip hop or ambient electronic. Any specific playlists or artists you recommend?",
                "author": "tech_guru",
                "tags": ["Recommendation", "Playlist"],
                "days_ago": 2,
                "is_pinned": False
            },
            {
                "topic": "art",
                "title": "Welcome to .art! Share your creations",
                "content": "Welcome to the art community! This is a place to share your artwork, whether it's digital, traditional, photography, or anything else. Don't be afraid to ask for feedback, and always be supportive of your fellow artists.",
                "author": "art_enthusiast",
                "tags": ["Discussion"],
                "days_ago": 13,
                "is_pinned": True
            },
            {
                "topic": "art",
                "title": "My first attempt at digital painting",
                "content": "I recently got a drawing tablet and tried my hand at digital painting for the first time. It's a steep learning curve! I followed a few tutorials online. Any tips for a beginner?",
                "author": "book_worm",
                "tags": ["Showcase", "Digital Art", "Feedback"],
                "days_ago": 5,
                "is_pinned": False,
                "media": [
                    {"file_path": "images/avatars/avatar3.png", "file_type": "image"},
                    {"file_path": "images/avatars/avatar4.png", "file_type": "image"},
                    {"file_path": "images/avatars/avatar5.png", "file_type": "image"},
                    {"file_path": "images/avatars/avatar6.png", "file_type": "image"}
                ]
            },
            {
                "topic": "art",
                "title": "The beauty of film photography",
                "content": "I've been getting back into shooting on film recently. There's something so magical about the process, and the colors you get straight out of the camera are unmatched. Anyone else here shoot film?",
                "author": "music_lover",
                "tags": ["Photography", "Discussion"],
                "days_ago": 3,
                "is_pinned": False
            },
            {
                "topic": "science",
                "title": "Welcome to .science! Rules and Guidelines",
                "content": "Welcome to the science forum! We encourage critical thinking and evidence-based discussions. Please provide sources for your claims when possible. Keep it educational and fascinating!",
                "author": "science_nerd",
                "tags": ["Discussion"],
                "days_ago": 14,
                "is_pinned": True
            },
            {
                "topic": "science",
                "title": "JWST discovers new exoplanet with water vapor",
                "content": "The James Webb Space Telescope just made another incredible discovery! It detected water vapor in the atmosphere of a rocky exoplanet in the habitable zone of its star. This is a huge step in the search for extraterrestrial life.",
                "author": "tech_guru",
                "tags": ["News", "Space", "Discussion"],
                "days_ago": 4,
                "is_pinned": False
            },
            {
                "topic": "science",
                "title": "How does quantum entanglement actually work?",
                "content": "I've read a few articles about quantum entanglement, but I still struggle to wrap my head around it. Can someone explain it in simple terms? How can two particles affect each other instantly across vast distances?",
                "author": "game_master",
                "tags": ["Question", "Physics"],
                "days_ago": 2,
                "is_pinned": False
            }
        ]
        
        post_objects = []
        for p_data in posts_data:
            topic = topic_objects[p_data["topic"]]
            author = user_objects[p_data["author"]]
            post = Post(
                title=p_data["title"],
                content=p_data["content"],
                topic_id=topic.id,
                user_id=author.id,
                is_pinned=p_data["is_pinned"],
                created_at=now - timedelta(days=p_data["days_ago"])
            )
            db.session.add(post)
            db.session.commit()
            
            # Associate tags
            topic_tags = tag_objects_by_topic[topic.id]
            for t_name in p_data["tags"]:
                for t_obj in topic_tags:
                    if t_obj.name == t_name:
                        post.tags.append(t_obj)
                        break
                        
            # Handle media
            for m_data in p_data.get("media", []):
                media = PostMedia(
                    post_id=post.id,
                    file_path=m_data["file_path"],
                    file_type=m_data["file_type"]
                )
                db.session.add(media)
                
            post_objects.append(post)
            
        db.session.commit()
        
        print("Creating comments...")
        
        # 4. COMMENTS
        # Example comment thread on "Just finished Elden Ring"
        elden_ring_post = next((p for p in post_objects if "Elden Ring" in p.title), None)
        if elden_ring_post:
            # Comment 1
            c1 = Comment(
                content="Great review! Malenia took me 50+ tries, no joke. For NG+, try a different build - I went from strength to faith/dex and it feels like a new game.",
                post_id=elden_ring_post.id,
                user_id=user_objects["game_master"].id,
                created_at=now - timedelta(days=4)
            )
            db.session.add(c1)
            db.session.commit()
            
            # Reply 1 to Comment 1
            c1_r1 = Comment(
                content="50 tries? I'm at 80 and counting... send help",
                post_id=elden_ring_post.id,
                user_id=user_objects["science_nerd"].id,
                parent_id=c1.id,
                created_at=now - timedelta(days=3)
            )
            db.session.add(c1_r1)
            db.session.commit()
            
            # Reply 2 to Reply 1
            c1_r2 = Comment(
                content="Try using Bloodhound's Step ash of war, makes dodging waterfowl dance way easier!",
                post_id=elden_ring_post.id,
                user_id=user_objects["tech_guru"].id,
                parent_id=c1_r1.id,
                created_at=now - timedelta(days=3)
            )
            db.session.add(c1_r2)
            db.session.commit()
            
            # Comment 2
            c2 = Comment(
                content="The soundtrack alone deserves 10/10. The final boss theme gives me chills every time.",
                post_id=elden_ring_post.id,
                user_id=user_objects["music_lover"].id,
                created_at=now - timedelta(days=3)
            )
            db.session.add(c2)
            db.session.commit()
            
            # Comment 3
            c3 = Comment(
                content="The art direction is unmatched. Every area feels like a painting.",
                post_id=elden_ring_post.id,
                user_id=user_objects["art_enthusiast"].id,
                created_at=now - timedelta(days=2)
            )
            db.session.add(c3)
            db.session.commit()
            
        # Add random comments to other posts to make it realistic
        all_users = list(user_objects.values())
        comment_objects = Comment.query.all()
        for post in post_objects:
            if "Elden Ring" in post.title:
                continue # Already handled
            
            num_comments = random.randint(3, 6)
            for _ in range(num_comments):
                # Pick a random subscriber from the topic
                topic = Topic.query.get(post.topic_id)
                subs = [s.user_id for s in topic.subscriptions]
                if not subs:
                    continue
                author_id = random.choice(subs)
                
                c = Comment(
                    content=random.choice([
                        "I completely agree with this!",
                        "Thanks for sharing this, very insightful.",
                        "I have a different opinion, but I see your point.",
                        "This is awesome!",
                        "Can't wait to see more.",
                        "Interesting perspective.",
                        "I've been thinking about this a lot lately.",
                        "Great write-up."
                    ]),
                    post_id=post.id,
                    user_id=author_id,
                    created_at=post.created_at + timedelta(hours=random.randint(1, 48))
                )
                db.session.add(c)
                db.session.commit()
                comment_objects.append(c)
                
                # Add a chance for a reply
                if random.random() > 0.5:
                    reply_author_id = random.choice(subs)
                    reply = Comment(
                        content=random.choice([
                            "Yeah, absolutely.",
                            "Good point!",
                            "I totally missed that.",
                            "Exactly what I was thinking.",
                            "Haha, right?"
                        ]),
                        post_id=post.id,
                        user_id=reply_author_id,
                        parent_id=c.id,
                        created_at=c.created_at + timedelta(hours=random.randint(1, 12))
                    )
                    db.session.add(reply)
                    db.session.commit()
                    comment_objects.append(reply)
            
        print("Adding likes/dislikes...")
        
        # 5. LIKES/DISLIKES
        # For posts
        for post in post_objects:
            topic = Topic.query.get(post.topic_id)
            subs = [s.user_id for s in topic.subscriptions]
            
            max_likes = min(25, len(subs) if len(subs) > 0 else 0)
            num_likes = random.randint(min(5, max_likes), max_likes) if max_likes > 0 else 0
            if num_likes > 0:
                likers = random.sample(subs, num_likes)
                for u_id in likers:
                    ld = LikeDislike(user_id=u_id, post_id=post.id, value=1)
                    db.session.add(ld)
            
            # Dislikes
            remaining_subs = list(set(subs) - set(likers if num_likes > 0 else []))
            num_dislikes = random.randint(0, min(5, len(remaining_subs)))
            if num_dislikes > 0:
                dislikers = random.sample(remaining_subs, num_dislikes)
                for u_id in dislikers:
                    ld = LikeDislike(user_id=u_id, post_id=post.id, value=-1)
                    db.session.add(ld)
                    
        # For comments
        for comment in comment_objects:
            post = Post.query.get(comment.post_id)
            topic = Topic.query.get(post.topic_id)
            subs = [s.user_id for s in topic.subscriptions]
            
            # Add specific likes to Elden Ring comments as requested
            if "50+ tries" in comment.content:
                num_likes = 12
                num_dislikes = 1
            elif "80 and counting" in comment.content:
                num_likes = 8
                num_dislikes = 0
            elif "Bloodhound's Step" in comment.content:
                num_likes = 5
                num_dislikes = 0
            elif "soundtrack alone" in comment.content:
                num_likes = 7
                num_dislikes = 0
            elif "art direction" in comment.content:
                num_likes = 4
                num_dislikes = 0
            else:
                num_likes = random.randint(2, min(12, len(subs) if len(subs) > 0 else 0))
                remaining_for_dislike = max(0, len(subs) - num_likes)
                num_dislikes = random.randint(0, min(2, remaining_for_dislike))
                
            if num_likes > 0 and len(subs) >= num_likes:
                likers = random.sample(subs, num_likes)
                for u_id in likers:
                    ld = LikeDislike(user_id=u_id, comment_id=comment.id, value=1)
                    db.session.add(ld)
                    
                remaining_subs = list(set(subs) - set(likers))
                if num_dislikes > 0 and len(remaining_subs) >= num_dislikes:
                    dislikers = random.sample(remaining_subs, num_dislikes)
                    for u_id in dislikers:
                        ld = LikeDislike(user_id=u_id, comment_id=comment.id, value=-1)
                        db.session.add(ld)

        db.session.commit()
        
        print("Adding moderation records...")
        
        # 6. BANNED USERS
        # Ban game_master in .science (NOT .gaming where he is creator)
        science_topic = topic_objects["science"]
        banned = BannedUser(
            user_id=user_objects["game_master"].id,
            topic_id=science_topic.id,
            banned_by=user_objects["tech_guru"].id # tech_guru is mod of .science
        )
        db.session.add(banned)
        
        db.session.commit()
        
        print("\n[OK] Database seeded successfully!")
        print(f"   - {User.query.count()} users")
        print(f"   - {Topic.query.count()} topics")
        print(f"   - {Post.query.count()} posts")
        print(f"   - {Comment.query.count()} comments")

if __name__ == "__main__":
    seed()
