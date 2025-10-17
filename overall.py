import streamlit as st
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="YouTube Video Analyzer",
    page_icon="🎥",
    layout="wide"
)

# Custom CSS for beautiful styling
st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #ff0000 0%, #cc0000 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-number {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
    }
    .stat-label {
        font-size: 14px;
        opacity: 0.9;
    }
    .info-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .comment-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #ff0000;
    }
    .author-name {
        font-weight: bold;
        color: #1a73e8;
        font-size: 16px;
    }
    .comment-text {
        margin: 10px 0;
        color: #333;
        line-height: 1.6;
    }
    .comment-meta {
        color: #666;
        font-size: 12px;
    }
    .tag {
        background: #e3f2fd;
        padding: 5px 10px;
        border-radius: 15px;
        display: inline-block;
        margin: 5px;
        font-size: 12px;
        color: #1976d2;
    }
    .thumbnail-container {
        text-align: center;
        margin: 20px 0;
    }
    .channel-info {
        display: flex;
        align-items: center;
        padding: 15px;
        background: #f8f9fa;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^?]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^?]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_number(num):
    """Format large numbers with K, M, B suffixes"""
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

def format_duration(duration):
    """Convert ISO 8601 duration to readable format"""
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return duration
    
    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def format_date(date_string):
    """Format ISO date string to readable format"""
    dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    return dt.strftime('%B %d, %Y at %I:%M %p')

def get_video_details(api_key, video_id):
    """Fetch complete video details"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        request = youtube.videos().list(
            part='snippet,contentDetails,statistics,status,topicDetails,recordingDetails,liveStreamingDetails',
            id=video_id
        )
        response = request.execute()
        
        if not response['items']:
            return None
        
        return response['items'][0]
    
    except HttpError as e:
        st.error(f"An error occurred: {e}")
        return None

def get_channel_details(api_key, channel_id):
    """Fetch channel details"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        request = youtube.channels().list(
            part='snippet,statistics,brandingSettings',
            id=channel_id
        )
        response = request.execute()
        
        if not response['items']:
            return None
        
        return response['items'][0]
    
    except HttpError as e:
        return None

def get_video_comments(api_key, video_id, max_results=100):
    """Fetch comments from YouTube video"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        comments_data = []
        request = youtube.commentThreads().list(
            part='snippet,replies',
            videoId=video_id,
            maxResults=min(max_results, 100),
            order='relevance',
            textFormat='plainText'
        )
        
        while request and len(comments_data) < max_results:
            response = request.execute()
            
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                replies = []
                
                if 'replies' in item:
                    for reply in item['replies']['comments']:
                        reply_snippet = reply['snippet']
                        replies.append({
                            'author': reply_snippet['authorDisplayName'],
                            'text': reply_snippet['textDisplay'],
                            'likes': reply_snippet['likeCount'],
                            'published_at': reply_snippet['publishedAt']
                        })
                
                comments_data.append({
                    'author': comment['authorDisplayName'],
                    'text': comment['textDisplay'],
                    'likes': comment['likeCount'],
                    'published_at': comment['publishedAt'],
                    'reply_count': item['snippet']['totalReplyCount'],
                    'replies': replies
                })
            
            if 'nextPageToken' in response and len(comments_data) < max_results:
                request = youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    pageToken=response['nextPageToken'],
                    maxResults=min(max_results - len(comments_data), 100),
                    order='relevance',
                    textFormat='plainText'
                )
            else:
                break
        
        return comments_data
    
    except HttpError as e:
        if 'commentsDisabled' in str(e):
            return "disabled"
        st.error(f"An error occurred while fetching comments: {e}")
        return None

# Main app
st.markdown('<div class="main-header"><h1>🎥 Complete YouTube Video Analyzer</h1><p>Discover everything about any YouTube video</p></div>', unsafe_allow_html=True)

# Sidebar for API key and settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("YouTube API Key", type="password", help="Enter your YouTube Data API v3 key")
    st.markdown("---")
    max_comments = st.slider("Max comments to fetch", 10, 500, 100)
    st.markdown("---")
    st.markdown("**📚 How to get API Key:**")
    st.markdown("1. Go to [Google Cloud Console](https://console.cloud.google.com/)")
    st.markdown("2. Create a project")
    st.markdown("3. Enable YouTube Data API v3")
    st.markdown("4. Create credentials (API Key)")

# Main content
video_url = st.text_input("🔗 Paste YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns([1, 5])
with col1:
    analyze_button = st.button("🚀 Analyze Video", use_container_width=True)

if analyze_button:
    if not api_key:
        st.error("⚠️ Please enter your YouTube API Key in the sidebar!")
    elif not video_url:
        st.error("⚠️ Please enter a YouTube video URL!")
    else:
        video_id = extract_video_id(video_url)
        
        if not video_id:
            st.error("❌ Invalid YouTube URL. Please check and try again.")
        else:
            with st.spinner("🔄 Fetching video data..."):
                video_data = get_video_details(api_key, video_id)
                
                if video_data:
                    snippet = video_data['snippet']
                    statistics = video_data.get('statistics', {})
                    content_details = video_data.get('contentDetails', {})
                    status = video_data.get('status', {})
                    
                    # Video Title and Thumbnail
                    st.markdown(f"## {snippet['title']}")
                    
                    col1, col2 = st.columns([2, 3])
                    
                    with col1:
                        st.markdown('<div class="thumbnail-container">', unsafe_allow_html=True)
                        thumbnail_url = snippet['thumbnails'].get('maxres', snippet['thumbnails'].get('high', snippet['thumbnails']['default']))['url']
                        st.image(thumbnail_url, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("### 📊 Video Statistics")
                        
                        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                        
                        with stat_col1:
                            views = int(statistics.get('viewCount', 0))
                            st.markdown(f'<div class="stat-card"><div class="stat-label">👁️ Views</div><div class="stat-number">{format_number(views)}</div></div>', unsafe_allow_html=True)
                        
                        with stat_col2:
                            likes = int(statistics.get('likeCount', 0))
                            st.markdown(f'<div class="stat-card"><div class="stat-label">👍 Likes</div><div class="stat-number">{format_number(likes)}</div></div>', unsafe_allow_html=True)
                        
                        with stat_col3:
                            comments_count = int(statistics.get('commentCount', 0))
                            st.markdown(f'<div class="stat-card"><div class="stat-label">💬 Comments</div><div class="stat-number">{format_number(comments_count)}</div></div>', unsafe_allow_html=True)
                        
                        with stat_col4:
                            favorites = int(statistics.get('favoriteCount', 0))
                            st.markdown(f'<div class="stat-card"><div class="stat-label">⭐ Favorites</div><div class="stat-number">{format_number(favorites)}</div></div>', unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        # Additional metrics
                        if likes > 0 and views > 0:
                            engagement_rate = (likes / views) * 100
                            st.metric("📈 Engagement Rate", f"{engagement_rate:.2f}%")
                    
                    # Video Information
                    st.markdown("---")
                    st.markdown("### 📝 Video Information")
                    
                    info_col1, info_col2, info_col3 = st.columns(3)
                    
                    with info_col1:
                        st.markdown('<div class="info-card">', unsafe_allow_html=True)
                        st.markdown(f"**📅 Published:** {format_date(snippet['publishedAt'])}")
                        st.markdown(f"**⏱️ Duration:** {format_duration(content_details.get('duration', 'N/A'))}")
                        st.markdown(f"**🔒 Privacy:** {status.get('privacyStatus', 'N/A').upper()}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with info_col2:
                        st.markdown('<div class="info-card">', unsafe_allow_html=True)
                        st.markdown(f"**📺 Definition:** {content_details.get('definition', 'N/A').upper()}")
                        st.markdown(f"**🎬 License:** {content_details.get('license', 'N/A')}")
                        st.markdown(f"**👶 Made for Kids:** {'Yes' if status.get('madeForKids', False) else 'No'}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with info_col3:
                        st.markdown('<div class="info-card">', unsafe_allow_html=True)
                        st.markdown(f"**🎵 Caption:** {content_details.get('caption', 'false').upper()}")
                        st.markdown(f"**🌍 Default Language:** {snippet.get('defaultLanguage', 'N/A').upper()}")
                        st.markdown(f"**📱 Live Content:** {'Yes' if status.get('selfDeclaredMadeForKids', False) else 'No'}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Description
                    st.markdown("---")
                    st.markdown("### 📄 Description")
                    with st.expander("Click to read full description", expanded=False):
                        st.write(snippet.get('description', 'No description available'))
                    
                    # Tags
                    if 'tags' in snippet and snippet['tags']:
                        st.markdown("### 🏷️ Tags")
                        tags_html = ''.join([f'<span class="tag">{tag}</span>' for tag in snippet['tags'][:20]])
                        st.markdown(tags_html, unsafe_allow_html=True)
                    
                    # Category
                    st.markdown("---")
                    categories = {
                        '1': 'Film & Animation', '2': 'Autos & Vehicles', '10': 'Music',
                        '15': 'Pets & Animals', '17': 'Sports', '19': 'Travel & Events',
                        '20': 'Gaming', '22': 'People & Blogs', '23': 'Comedy',
                        '24': 'Entertainment', '25': 'News & Politics', '26': 'Howto & Style',
                        '27': 'Education', '28': 'Science & Technology', '29': 'Nonprofits & Activism'
                    }
                    category_id = snippet.get('categoryId', 'Unknown')
                    category_name = categories.get(category_id, 'Unknown')
                    st.markdown(f"**📂 Category:** {category_name}")
                    
                    # Channel Information
                    st.markdown("---")
                    st.markdown("### 📺 Channel Information")
                    
                    channel_id = snippet['channelId']
                    channel_data = get_channel_details(api_key, channel_id)
                    
                    if channel_data:
                        channel_snippet = channel_data['snippet']
                        channel_stats = channel_data.get('statistics', {})
                        
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            if 'thumbnails' in channel_snippet:
                                channel_thumbnail = channel_snippet['thumbnails']['high']['url']
                                st.image(channel_thumbnail, width=150)
                        
                        with col2:
                            st.markdown(f"**Channel Name:** {channel_snippet['title']}")
                            st.markdown(f"**Subscribers:** {format_number(int(channel_stats.get('subscriberCount', 0)))}")
                            st.markdown(f"**Total Videos:** {format_number(int(channel_stats.get('videoCount', 0)))}")
                            st.markdown(f"**Total Views:** {format_number(int(channel_stats.get('viewCount', 0)))}")
                            st.markdown(f"**Created:** {format_date(channel_snippet['publishedAt'])}")
                        
                        if channel_snippet.get('description'):
                            with st.expander("Channel Description"):
                                st.write(channel_snippet['description'])
                    
                    # Comments Section
                    st.markdown("---")
                    st.markdown("### 💬 Comments Analysis")
                    
                    with st.spinner("🔄 Fetching comments..."):
                        comments = get_video_comments(api_key, video_id, max_comments)
                        
                        if comments == "disabled":
                            st.warning("💬 Comments are disabled for this video.")
                        elif comments:
                            st.success(f"✅ Successfully fetched {len(comments)} comments!")
                            
                            # Comments Statistics
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Total Comments", len(comments))
                            with col2:
                                total_likes = sum(c['likes'] for c in comments)
                                st.metric("Total Likes", total_likes)
                            with col3:
                                avg_likes = total_likes / len(comments) if comments else 0
                                st.metric("Avg Likes", f"{avg_likes:.1f}")
                            with col4:
                                total_replies = sum(c['reply_count'] for c in comments)
                                st.metric("Total Replies", total_replies)
                            
                            # Filter options
                            st.markdown("#### 🔍 Filter Comments")
                            col1, col2 = st.columns(2)
                            with col1:
                                sort_by = st.selectbox("Sort by", ["Likes (High to Low)", "Likes (Low to High)", "Date (Newest)", "Date (Oldest)"])
                            with col2:
                                search_term = st.text_input("🔎 Search in comments", placeholder="Enter keyword...")
                            
                            # Apply filters
                            filtered_comments = comments.copy()
                            
                            if search_term:
                                filtered_comments = [c for c in filtered_comments if search_term.lower() in c['text'].lower()]
                            
                            # Sort comments
                            if sort_by == "Likes (High to Low)":
                                filtered_comments.sort(key=lambda x: x['likes'], reverse=True)
                            elif sort_by == "Likes (Low to High)":
                                filtered_comments.sort(key=lambda x: x['likes'])
                            elif sort_by == "Date (Newest)":
                                filtered_comments.sort(key=lambda x: x['published_at'], reverse=True)
                            elif sort_by == "Date (Oldest)":
                                filtered_comments.sort(key=lambda x: x['published_at'])
                            
                            st.markdown(f"**Showing {len(filtered_comments)} comments**")
                            
                            # Display comments
                            for idx, comment in enumerate(filtered_comments, 1):
                                with st.container():
                                    st.markdown(f"""
                                        <div class="comment-card">
                                            <div class="author-name">👤 {comment['author']}</div>
                                            <div class="comment-text">{comment['text']}</div>
                                            <div class="comment-meta">
                                                👍 {comment['likes']} likes • 
                                                💬 {comment['reply_count']} replies • 
                                                📅 {format_date(comment['published_at'])}
                                            </div>
                                        </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Show replies if available
                                    if comment['replies'] and len(comment['replies']) > 0:
                                        with st.expander(f"View {len(comment['replies'])} replies"):
                                            for reply in comment['replies']:
                                                st.markdown(f"**{reply['author']}:** {reply['text']}")
                                                st.caption(f"👍 {reply['likes']} • {format_date(reply['published_at'])}")
                                                st.markdown("---")
                            
                            # Download options
                            st.markdown("---")
                            st.markdown("### 📥 Export Data")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                # Export comments
                                df_comments = pd.DataFrame([{
                                    'Author': c['author'],
                                    'Comment': c['text'],
                                    'Likes': c['likes'],
                                    'Replies': c['reply_count'],
                                    'Published': c['published_at']
                                } for c in filtered_comments])
                                csv_comments = df_comments.to_csv(index=False)
                                st.download_button(
                                    label="📄 Download Comments CSV",
                                    data=csv_comments,
                                    file_name=f"youtube_comments_{video_id}.csv",
                                    mime="text/csv"
                                )
                            
                            with col2:
                                # Export video info
                                video_info = {
                                    'Title': snippet['title'],
                                    'Views': statistics.get('viewCount', 0),
                                    'Likes': statistics.get('likeCount', 0),
                                    'Comments': statistics.get('commentCount', 0),
                                    'Published': snippet['publishedAt'],
                                    'Duration': content_details.get('duration', 'N/A'),
                                    'Channel': snippet['channelTitle']
                                }
                                json_data = json.dumps(video_info, indent=2)
                                st.download_button(
                                    label="📊 Download Video Info JSON",
                                    data=json_data,
                                    file_name=f"youtube_video_info_{video_id}.json",
                                    mime="application/json"
                                )
                            
                            with col3:
                                # Export full data
                                full_data = {
                                    'video': video_data,
                                    'channel': channel_data,
                                    'comments': comments
                                }
                                full_json = json.dumps(full_data, indent=2, default=str)
                                st.download_button(
                                    label="📦 Download Complete Data",
                                    data=full_json,
                                    file_name=f"youtube_complete_data_{video_id}.json",
                                    mime="application/json"
                                )
                        else:
                            st.info("No comments available or an error occurred.")