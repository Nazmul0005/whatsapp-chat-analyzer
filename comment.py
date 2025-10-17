import streamlit as st
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="YouTube Comments Viewer",
    page_icon="💬",
    layout="wide"
)

# Custom CSS for beautiful styling
st.markdown("""
    <style>
    .comment-card {
        background-color: #f8f9fa;
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
    .stButton>button {
        background-color: #ff0000;
        color: white;
        border-radius: 5px;
        padding: 10px 24px;
        font-weight: bold;
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

def get_video_comments(api_key, video_id, max_results=100):
    """Fetch comments from YouTube video"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        comments_data = []
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=min(max_results, 100),
            order='relevance',
            textFormat='plainText'
        )
        
        while request and len(comments_data) < max_results:
            response = request.execute()
            
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comments_data.append({
                    'author': comment['authorDisplayName'],
                    'text': comment['textDisplay'],
                    'likes': comment['likeCount'],
                    'published_at': comment['publishedAt'],
                    'reply_count': item['snippet']['totalReplyCount']
                })
            
            # Check if there are more comments
            if 'nextPageToken' in response and len(comments_data) < max_results:
                request = youtube.commentThreads().list(
                    part='snippet',
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
        st.error(f"An error occurred: {e}")
        return None

def format_date(date_string):
    """Format ISO date string to readable format"""
    dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    return dt.strftime('%B %d, %Y at %I:%M %p')

# Main app
st.title("💬 YouTube Comments Viewer")
st.markdown("### Fetch and view YouTube comments beautifully")

# Sidebar for API key and settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("YouTube API Key", type="password", help="Enter your YouTube Data API v3 key")
    st.markdown("---")
    st.markdown("**How to get API Key:**")
    st.markdown("1. Go to [Google Cloud Console](https://console.cloud.google.com/)")
    st.markdown("2. Create a project")
    st.markdown("3. Enable YouTube Data API v3")
    st.markdown("4. Create credentials (API Key)")
    
    max_comments = st.slider("Max comments to fetch", 10, 500, 100)

# Main content
col1, col2 = st.columns([3, 1])

with col1:
    video_url = st.text_input("🔗 Paste YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

with col2:
    st.write("")
    st.write("")
    fetch_button = st.button("🚀 Fetch Comments")

if fetch_button:
    if not api_key:
        st.error("⚠️ Please enter your YouTube API Key in the sidebar!")
    elif not video_url:
        st.error("⚠️ Please enter a YouTube video URL!")
    else:
        video_id = extract_video_id(video_url)
        
        if not video_id:
            st.error("❌ Invalid YouTube URL. Please check and try again.")
        else:
            with st.spinner("🔄 Fetching comments..."):
                comments = get_video_comments(api_key, video_id, max_comments)
                
                if comments:
                    st.success(f"✅ Successfully fetched {len(comments)} comments!")
                    
                    # Display statistics
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
                    
                    st.markdown("---")
                    
                    # Filter options
                    st.subheader("🔍 Filter Comments")
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
                    
                    st.markdown(f"### Showing {len(filtered_comments)} comments")
                    
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
                    
                    # Download option
                    st.markdown("---")
                    df = pd.DataFrame(filtered_comments)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Comments as CSV",
                        data=csv,
                        file_name=f"youtube_comments_{video_id}.csv",
                        mime="text/csv"
                    )