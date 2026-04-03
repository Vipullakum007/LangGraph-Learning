import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage, AIMessage
import uuid

# ---------------- Utility Functions ----------------

def generate_thread_id():
    return str(uuid.uuid4())


def generate_title(first_message: str):
    return first_message[:25] + ("..." if len(first_message) > 25 else "")


def reset_chat():
    thread_id = generate_thread_id()
    st.session_state.thread_id = thread_id
    st.session_state.chat_titles[thread_id] = "New Chat"
    add_thread(thread_id)
    st.session_state.message_history = []


def add_thread(thread_id):
    if thread_id not in st.session_state.chat_threads:
        st.session_state.chat_threads.append(thread_id)


def delete_thread(thread_id):
    if thread_id in st.session_state.chat_threads:
        st.session_state.chat_threads.remove(thread_id)
        st.session_state.chat_titles.pop(thread_id, None)

        if st.session_state.thread_id == thread_id:
            reset_chat()


def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    return state.values.get('messages', [])


# ---------------- Page Config ----------------
st.set_page_config(page_title="ChatBot UI", page_icon="💬", layout="wide")

# ---------------- Styling ----------------
st.markdown("""
<style>
.chat-container {
    max-width: 900px;
    margin: auto;
}
.stChatMessage {
    border-radius: 10px;
    padding: 12px;
}
.user-msg {
    background-color: #343541;
    color: white;
}
.assistant-msg {
    background-color: #444654;
    color: white;
}
.sidebar-title {
    font-size: 18px;
    font-weight: 600;
}
.thread-btn {
    text-align: left;
}
</style>
""", unsafe_allow_html=True)


# ---------------- Session State ----------------
if 'message_history' not in st.session_state:
    st.session_state.message_history = []

if 'thread_id' not in st.session_state:
    st.session_state.thread_id = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state.chat_threads = []

if 'chat_titles' not in st.session_state:
    st.session_state.chat_titles = {}

add_thread(st.session_state.thread_id)
st.session_state.chat_titles.setdefault(st.session_state.thread_id, "New Chat")


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("<div class='sidebar-title'>💬 Chats</div>", unsafe_allow_html=True)

    if st.button("➕ New Chat", use_container_width=True):
        reset_chat()

    st.divider()

    for thread_id in st.session_state.chat_threads[::-1]:
        col1, col2 = st.columns([0.8, 0.2])

        title = st.session_state.chat_titles.get(thread_id, "New Chat")

        if col1.button(title, key=f"select_{thread_id}"):
            st.session_state.thread_id = thread_id
            messages = load_conversation(thread_id)

            temp_messages = []
            for msg in messages:
                role = 'user' if isinstance(msg, HumanMessage) else 'assistant'
                temp_messages.append({'role': role, 'content': msg.content})

            st.session_state.message_history = temp_messages

        if col2.button("🗑️", key=f"delete_{thread_id}"):
            
            delete_thread(thread_id)
            st.rerun()


# ---------------- Main Chat UI ----------------

chat_container = st.container()

with chat_container:
    for message in st.session_state.message_history:
        with st.chat_message(message['role']):
            st.markdown(message['content'])


# ---------------- Input ----------------
user_input = st.chat_input("Send a message...")

if user_input:
    # Set title if first message
    if st.session_state.chat_titles[st.session_state.thread_id] == "New Chat":
        st.session_state.chat_titles[st.session_state.thread_id] = generate_title(user_input)

    # User message
    st.session_state.message_history.append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    CONFIG = {'configurable': {'thread_id': st.session_state.thread_id}}

    # Assistant response
    with st.chat_message("assistant"):
        def stream_response():
            for chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages"
            ):
                if isinstance(chunk, AIMessage):
                    yield chunk.content

        ai_response = st.write_stream(stream_response())

    st.session_state.message_history.append({'role': 'assistant', 'content': ai_response})
