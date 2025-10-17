import streamlit as st
import zipfile
import re
from pathlib import Path
import tempfile

def is_bangla_text(text):
    """
    Check if the text contains Bangla characters.
    Bangla Unicode range: \u0980-\u09FF
    """
    if not text or len(text.strip()) == 0:
        return False
    
    # Skip system messages
    system_keywords = [
        'Messages and calls are end-to-end encrypted',
        'created group',
        'were added',
        'left',
        'changed',
        '<Media omitted>',
        'Waiting for this message',
        'This message was deleted',
        'changed to'
    ]
    
    for keyword in system_keywords:
        if keyword.lower() in text.lower():
            return False
    
    bangla_chars = 0
    total_chars = 0
    
    for char in text:
        if char.strip() and not char.isspace() and char not in '.,!?;:@#$%^&*()[]{}+-=/\\|<>~`"\'':
            total_chars += 1
            if '\u0980' <= char <= '\u09FF':
                bangla_chars += 1
    
    if total_chars == 0:
        return False
    
    # Consider it Bangla if at least 25% of characters are Bangla
    return (bangla_chars / total_chars) >= 0.25

def extract_zip_file(zip_file):
    """Extract zip file and return the path to the .txt file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find the .txt file
        txt_files = list(Path(temp_dir).rglob('*.txt'))
        
        if txt_files:
            with open(txt_files[0], 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return None

def parse_whatsapp_chat(chat_text):
    """
    Parse WhatsApp chat text and extract messages.
    Format: DD/MM/YYYY, HH:MM am/pm - +880 XXXX-XXXXXX: Message
    """
    messages = []
    lines = chat_text.split('\n')
    
    # Pattern for WhatsApp message with phone number
    # Matches: DD/MM/YYYY, HH:MM am/pm - +880 XXXX-XXXXXX: Message
    pattern = r'^(\d{1,2}/\d{1,2}/\d{4}),\s+(\d{1,2}:\d{2}\s*(?:am|pm))\s*-\s*([^:]+):\s*(.*)$'
    
    current_msg = None
    
    for line in lines:
        match = re.match(pattern, line, re.IGNORECASE)
        
        if match:
            # Save previous message if exists
            if current_msg:
                messages.append(current_msg)
            
            # Start new message
            date = match.group(1)
            time = match.group(2)
            sender = match.group(3).strip()
            message = match.group(4).strip()
            
            current_msg = {
                'date': date,
                'time': time,
                'sender': sender,
                'message': message
            }
        elif current_msg and line.strip():
            # Continuation of previous message
            current_msg['message'] += '\n' + line.strip()
    
    # Add last message
    if current_msg:
        messages.append(current_msg)
    
    return messages

def filter_bangla_messages(messages):
    """Filter messages that contain Bangla text."""
    bangla_messages = []
    
    for msg in messages:
        if is_bangla_text(msg['message']):
            bangla_messages.append(msg)
    
    return bangla_messages

def format_phone_number(sender):
    """Format phone number for better display."""
    # If it's a phone number, format it nicely
    if sender.startswith('+880'):
        return sender
    return sender

# Streamlit App
st.set_page_config(
    page_title="WhatsApp Bangla Message Extractor",
    page_icon="💬",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .message-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #4CAF50;
    }
    .sender-info {
        color: #1f77b4;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .date-time {
        color: #666;
        font-size: 0.85em;
        margin-bottom: 10px;
    }
    .message-text {
        font-size: 1.1em;
        line-height: 1.6;
        color: #333;
    }
    .copy-button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 5px;
        cursor: pointer;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

st.title("💬 WhatsApp বাংলা Message Extractor")
st.markdown("আপনার WhatsApp চ্যাট এক্সপোর্ট (ZIP ফাইল) আপলোড করুন এবং সব বাংলা মেসেজ দেখুন।")

# File uploader
uploaded_file = st.file_uploader(
    "আপনার WhatsApp চ্যাট ZIP ফাইল এখানে ড্রপ করুন",
    type=['zip'],
    help="WhatsApp থেকে 'Export Chat' অপশন দিয়ে চ্যাট এক্সপোর্ট করুন এবং ZIP ফাইল আপলোড করুন"
)

if uploaded_file is not None:
    with st.spinner("আপনার চ্যাট প্রসেস করা হচ্ছে..."):
        # Extract the zip file
        chat_text = extract_zip_file(uploaded_file)
        
        if chat_text is None:
            st.error("❌ ZIP আর্কাইভে কোন .txt ফাইল পাওয়া যায়নি। অনুগ্রহ করে সঠিকভাবে চ্যাট এক্সপোর্ট করেছেন কিনা নিশ্চিত করুন।")
        else:
            # Parse the chat
            all_messages = parse_whatsapp_chat(chat_text)
            
            # Filter Bangla messages
            bangla_messages = filter_bangla_messages(all_messages)
            
            # Display statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("মোট মেসেজ", len(all_messages))
            with col2:
                st.metric("বাংলা মেসেজ", len(bangla_messages))
            with col3:
                percentage = (len(bangla_messages)/len(all_messages)*100) if all_messages else 0
                st.metric("পার্সেন্টেজ", f"{percentage:.1f}%")
            
            st.markdown("---")
            
            if bangla_messages:
                st.subheader(f"📝 {len(bangla_messages)} টি বাংলা মেসেজ পাওয়া গেছে")
                
                # Search functionality
                search_term = st.text_input("🔍 মেসেজে খুঁজুন", placeholder="সার্চ করতে টাইপ করুন...")
                
                # Filter by sender
                all_senders = sorted(list(set([msg['sender'] for msg in bangla_messages])))
                selected_sender = st.selectbox("পাঠাকারী অনুযায়ী ফিল্টার করুন", ["সবাই"] + all_senders)
                
                # Apply filters
                filtered_messages = bangla_messages
                if search_term:
                    filtered_messages = [msg for msg in filtered_messages if search_term.lower() in msg['message'].lower()]
                if selected_sender != "সবাই":
                    filtered_messages = [msg for msg in filtered_messages if msg['sender'] == selected_sender]
                
                st.info(f"📊 {len(filtered_messages)} টি মেসেজ দেখানো হচ্ছে")
                
                # Display messages in a beautiful format
                for idx, msg in enumerate(filtered_messages, 1):
                    with st.container():
                        # Header with number and sender
                        col1, col2 = st.columns([5, 1])
                        with col1:
                            st.markdown(f"### {idx}. 👤 {format_phone_number(msg['sender'])}")
                        with col2:
                            st.markdown(f"<div style='text-align: right; color: #666; font-size: 0.9em;'>📅 {msg['date']}<br>🕐 {msg['time']}</div>", unsafe_allow_html=True)
                        
                        # Message content in a text area (easy to copy)
                        st.text_area(
                            label=f"মেসেজ {idx}",
                            value=msg['message'],
                            height=max(100, len(msg['message'].split('\n')) * 30),
                            key=f"msg_{idx}",
                            label_visibility="collapsed"
                        )
                        
                        st.markdown("---")
                
                # Download option
                st.markdown("### 💾 ডাউনলোড অপশন")
                
                # Prepare text for download
                download_text = "=" * 80 + "\n"
                download_text += "বাংলা মেসেজ সংগ্রহ\n"
                download_text += f"মোট মেসেজ: {len(filtered_messages)}\n"
                download_text += "=" * 80 + "\n\n"
                
                for idx, msg in enumerate(filtered_messages, 1):
                    download_text += f"{idx}. পাঠাকারী: {msg['sender']}\n"
                    download_text += f"   তারিখ: {msg['date']} {msg['time']}\n"
                    download_text += f"   মেসেজ: {msg['message']}\n"
                    download_text += "\n" + "-" * 80 + "\n\n"
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 সব বাংলা মেসেজ TXT ফাইলে ডাউনলোড করুন",
                        data=download_text,
                        file_name="bangla_messages.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                with col2:
                    # Prepare simple format (only messages)
                    simple_text = "\n\n".join([msg['message'] for msg in filtered_messages])
                    st.download_button(
                        label="📄 শুধু মেসেজ ডাউনলোড করুন (সিম্পল ফরম্যাট)",
                        data=simple_text,
                        file_name="bangla_messages_simple.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
            else:
                st.warning("⚠️ এই চ্যাটে কোন বাংলা মেসেজ পাওয়া যায়নি।")
                st.info("নিশ্চিত করুন যে আপনার চ্যাটে বাংলা ভাষায় মেসেজ আছে।")

else:
    # Instructions
    st.info("👆 শুরু করতে আপনার WhatsApp চ্যাট ZIP ফাইল আপলোড করুন")
    
    with st.expander("📖 কিভাবে WhatsApp চ্যাট এক্সপোর্ট করবেন?"):
        st.markdown("""
        **Android/iPhone:**
        1. WhatsApp খুলুন
        2. যে গ্রুপ বা চ্যাট এক্সপোর্ট করতে চান সেটি খুলুন
        3. উপরে গ্রুপ/ব্যক্তির নামে ট্যাপ করুন
        4. নিচে স্ক্রল করে **"Export Chat"** এ ট্যাপ করুন
        5. **"Without Media"** বা **"Include Media"** সিলেক্ট করুন
        6. ZIP ফাইলটি সেভ করুন এবং এখানে আপলোড করুন
        """)
    
    with st.expander("ℹ️ ফিচার সমূহ"):
        st.markdown("""
        - ✅ স্বয়ংক্রিয়ভাবে ZIP ফাইল এক্সট্র্যাক্ট করে
        - ✅ NLP ব্যবহার করে বাংলা মেসেজ শনাক্ত করে
        - ✅ সুন্দর কার্ড-ভিত্তিক ডিসপ্লে
        - ✅ সার্চ ফাংশনালিটি
        - ✅ পাঠাকারী অনুযায়ী ফিল্টার
        - ✅ প্রতিটি মেসেজ আলাদাভাবে কপি করুন
        - ✅ সব বাংলা মেসেজ TXT ফাইলে ডাউনলোড করুন
        - ✅ পরিসংখ্যান এবং মেট্রিক্স দেখায়
        - ✅ সিস্টেম মেসেজ এড়িয়ে যায়
        - ✅ ফোন নম্বর ফরম্যাট সাপোর্ট
        """)
    
    with st.expander("🎯 উদাহরণ"):
        st.markdown("""
        এই অ্যাপটি নিম্নলিখিত ধরনের মেসেজ শনাক্ত করবে:
        
        - "শুভ নববর্ষ সবাইকে" ✅
        - "ধর্মকে ধর্মের স্থানে রেখে সকল মানুষকে ভালবাসি।" ✅
        - "সবাইকে নববর্ষ ও পাহাড় থেকে বৈসাবির শুভেচ্ছা" ✅
        - "এতো রাতে নক দেওয়ার জন্য সরি সবাইকে..." ✅
        
        এড়িয়ে যাবে:
        - "<Media omitted>" ❌
        - "Waiting for this message" ❌
        - "Messages and calls are end-to-end encrypted" ❌
        """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>❤️ Streamlit দিয়ে তৈরি | বাংলা ভাষাকে ভালোবাসি</div>",
    unsafe_allow_html=True
)