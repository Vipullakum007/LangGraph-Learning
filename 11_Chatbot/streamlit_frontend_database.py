import streamlit as st
from langgraph_database_backend import chatbot, retrieve_all_threads, delete_thread_from_db  # updated import
from langchain_core.messages import HumanMessage, AIMessage
import uuid

# ---------------- Utility Functions ----------------

def generate_thread_id():
    return str(uuid.uuid4())

def generate_title(first_message: str):
    return first_message[:25] + ("..." if len(first_message) > 25 else "")

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['chat_titles'][thread_id] = "New Chat"
    add_thread(thread_id)
    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def delete_thread(thread_id):
    delete_thread_from_db(thread_id)  # permanently delete from DB

    if thread_id in st.session_state['chat_threads']:
        st.session_state['chat_threads'].remove(thread_id)
        st.session_state['chat_titles'].pop(thread_id, None)

        if st.session_state['thread_id'] == thread_id:
            if st.session_state['chat_threads']:
                new_active = st.session_state['chat_threads'][-1]
                st.session_state['thread_id'] = new_active
                st.session_state['message_history'] = [
                    {'role': 'user' if isinstance(m, HumanMessage) else 'assistant', 'content': m.content}
                    for m in load_conversation(new_active)
                ]
            else:
                reset_chat()

def load_conversation(thread_id):
    try:
        state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
        return state.values.get('messages', [])
    except Exception:
        return []


# ---------------- Page Config & Styling ----------------
st.set_page_config(page_title="LangGraph Chatbot", page_icon="💬", layout="wide")

st.markdown("""
<style>
.chat-container { max-width: 900px; margin: auto; }
.stChatMessage { border-radius: 10px; padding: 12px; }
.sidebar-title { font-size: 18px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ---------------- Session State Setup ----------------
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'chat_threads' not in st.session_state:
    db_threads = retrieve_all_threads()
    st.session_state['chat_threads'] = db_threads if db_threads else []

if 'chat_titles' not in st.session_state:
    st.session_state['chat_titles'] = {}

if 'thread_id' not in st.session_state:
    if st.session_state['chat_threads']:
        st.session_state['thread_id'] = st.session_state['chat_threads'][-1]
    else:
        st.session_state['thread_id'] = generate_thread_id()

add_thread(st.session_state['thread_id'])
st.session_state['chat_titles'].setdefault(st.session_state['thread_id'], "New Chat")


# ---------------- Sidebar UI ----------------
with st.sidebar:
    st.markdown("<div class='sidebar-title'>💬 My Conversations</div>", unsafe_allow_html=True)

    if st.button("➕ New Chat", use_container_width=True):
        reset_chat()
        st.rerun()

    st.divider()

    for thread_id in st.session_state['chat_threads'][::-1]:
        col1, col2 = st.columns([0.8, 0.2])

        if thread_id not in st.session_state['chat_titles']:
            msgs = load_conversation(thread_id)
            title_set = False
            for m in msgs:
                if isinstance(m, HumanMessage):
                    st.session_state['chat_titles'][thread_id] = generate_title(m.content)
                    title_set = True
                    break
            if not title_set:
                st.session_state['chat_titles'][thread_id] = f"Chat {str(thread_id)[:8]}..."

        title = st.session_state['chat_titles'].get(thread_id, "New Chat")

        if col1.button(title, key=f"select_{thread_id}", use_container_width=True):
            st.session_state['thread_id'] = thread_id
            messages = load_conversation(thread_id)
            st.session_state['message_history'] = [
                {'role': 'user' if isinstance(m, HumanMessage) else 'assistant', 'content': m.content}
                for m in messages
            ]
            st.rerun()

        if col2.button("🗑️", key=f"delete_{thread_id}"):
            delete_thread(thread_id)
            st.rerun()


# ---------------- Main Chat UI ----------------
st.markdown(f"**Thread:** `{st.session_state['thread_id'][:8]}...`")

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

user_input = st.chat_input('Type here...')

if user_input:
    if st.session_state['chat_titles'].get(st.session_state['thread_id']) == "New Chat":
        st.session_state['chat_titles'][st.session_state['thread_id']] = generate_title(user_input)

    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

    with st.chat_message('assistant'):
        def stream_response():
            for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            ):
                if hasattr(message_chunk, 'content'):
                    content = message_chunk.content
                    if isinstance(content, str) and content:
                        yield content
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                yield block.get('text', '')

        ai_message = st.write_stream(stream_response())

    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})