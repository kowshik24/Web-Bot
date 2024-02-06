import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import sqlite3
import hashlib
import os

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'last_page' not in st.session_state:
    st.session_state.last_page = 'Home 🏠'

# Function to hash passwords
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Function to check hashes
def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Database connection
conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()

# Create the table
def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT, openai_key TEXT)')

# Add user data
def add_userdata(username, password, openai_key):
    c.execute('INSERT INTO userstable(username, password, openai_key) VALUES (?,?,?)', (username, password, openai_key))
    conn.commit()

# Login user
def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    if data:
        openai_key = data[0][2]
        print(openai_key)
        return data, openai_key
    return None , None

# Update user data
def update_userdata(username, new_password, new_openai_key):
    c.execute('UPDATE userstable SET password = ?, openai_key = ? WHERE username = ?', (new_password, new_openai_key, username))
    conn.commit()

def get_vectorstore_from_url(url):
    # get the text in document form
    loader = WebBaseLoader(url)
    document = loader.load()
    
    # split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter()
    document_chunks = text_splitter.split_documents(document)
    
    # create a vectorstore from the chunks
    vector_store = Chroma.from_documents(document_chunks, OpenAIEmbeddings(api_key=st.session_state.openai_api_key))

    return vector_store

def get_context_retriever_chain(vector_store):
    llm = ChatOpenAI(api_key=st.session_state.openai_api_key)
    
    retriever = vector_store.as_retriever()
    
    prompt = ChatPromptTemplate.from_messages([
      MessagesPlaceholder(variable_name="chat_history"),
      ("user", "{input}"),
      ("user", "Given the above conversation, generate a search query to look up in order to get information relevant to the conversation")
    ])
    
    retriever_chain = create_history_aware_retriever(llm, retriever, prompt)
    
    return retriever_chain
    
def get_conversational_rag_chain(retriever_chain): 
    
    llm = ChatOpenAI(api_key=st.session_state.openai_api_key)
    
    prompt = ChatPromptTemplate.from_messages([
      ("system", "Answer the user's questions based on the below context:\n\n{context}"),
      MessagesPlaceholder(variable_name="chat_history"),
      ("user", "{input}"),
    ])
    
    stuff_documents_chain = create_stuff_documents_chain(llm,prompt)
    
    return create_retrieval_chain(retriever_chain, stuff_documents_chain)

def get_response(user_input):
    retriever_chain = get_context_retriever_chain(st.session_state.vector_store)
    conversation_rag_chain = get_conversational_rag_chain(retriever_chain)
    
    response = conversation_rag_chain.invoke({
        "chat_history": st.session_state.chat_history,
        "input": user_input
    })
    
    return response['answer']

# Streamlit UI
def main():
    st.markdown("<h1 style='text-align: center; color: blue;'>Web Bot 🤖</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Chat with your web url</h3>", unsafe_allow_html=True)

    


    menu = ["Home 🏠", "Login 🔑", "SignUp 📝", "Web Bot 🤖", "Settings ⚙️"]
    
    # Function to update the last page and rerun the app
    def update_page_and_rerun(new_page):
        st.session_state.last_page = new_page
        st.experimental_rerun()

    if st.session_state.logged_in:
        if st.session_state.last_page not in menu:
            st.session_state.last_page = 'Home 🏠'
        choice = st.sidebar.selectbox("Menu 📜", menu, index=menu.index(st.session_state.last_page))
        # Update and rerun if the page choice has changed
        if choice != st.session_state.last_page:
            update_page_and_rerun(choice)
    else:
        choice = st.sidebar.selectbox("Menu 📜", ["Home 🏠", "Login 🔑", "SignUp 📝"])
        if choice != st.session_state.last_page:
            update_page_and_rerun(choice)

    if choice == "Home 🏠":
        st.subheader("Welcome to Web Bot 🤖")
        st.info("The chatbot that can chat with your web url. Just enter the URL and start chatting. 🌐🤖")
        st.info("""
        ## About Web Bot 🤖
        
        **Web Bot** is a chatbot that can chat with your web url. Just enter the URL and start chatting. 🌐🤖

        ### Features:
        - **Chat with your web url**
        - **Login and Signup**
        - **Update your API Keys and Password**

        ### Get in Touch:
        - **Email**: [kowshikcseruet1998@gmail.com](mailto:kowshikcseruet1998@gmail.com) 📧
        - **LinkedIn**: [https://www.linkedin.com/in/kowshik24/](https://www.linkedin.com/in/kowshik24/) 💼
        - **GitHub**: [https://github.com/kowshik24](https://github.com/kowshik24) 🌐

        ### Stay Connected 🌍
        """)
        st.session_state.last_page = choice

    elif choice == "Login 🔑":
        if st.session_state.logged_in:
            st.success(f"Already logged in as {st.session_state.username} 👋")
        else:
            st.subheader("Login Section 🔐")
            username = st.sidebar.text_input("User Name 👤")
            password = st.sidebar.text_input("Password 🔒", type='password')
            if st.sidebar.button("Login 🚪"):
                create_usertable()
                hashed_password = make_hashes(password)
                result , openai_key = login_user(username, check_hashes(password, hashed_password))
                if result:
                    # now add openai_api_key to session state
                    st.session_state.openai_api_key = openai_key
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.last_page = "Web Bot 🤖"
                    st.experimental_rerun()

    elif choice == "SignUp 📝":
        st.subheader("Create New Account 🌱")
        st.info("Don't have OPENAI API KEY? Get one here: https://platform.openai.com/api-keys")
        new_user = st.text_input("Username 👤")
        new_password = st.text_input("Password 🔑", type='password')
        new_openai_key = st.text_input("OpenAI API Key 🌐")
        if st.button("Signup 🌟"):
            create_usertable()
            add_userdata(new_user, make_hashes(new_password), new_openai_key)
            st.success("You have successfully created an account ✅")
            st.info("Go to Login Menu to login 🔑")
    
    elif choice == "Web Bot 🤖":
        with st.sidebar:
            st.header("URL")
            website_url = st.text_input("Enter the URL of the website")
        
        if website_url:
            # Initialize session state for chat history and vector store
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = [AIMessage(content="Hello, I am a bot. How can I help you?")]
            if "vector_store" not in st.session_state or st.session_state.website_url != website_url:
                st.session_state.vector_store = get_vectorstore_from_url(website_url)
                st.session_state.website_url = website_url

            # User input for chat
            user_query = st.chat_input("Type your message here...")
            if user_query:
                response = get_response(user_query)
                st.session_state.chat_history.append(HumanMessage(content=user_query))
                st.session_state.chat_history.append(AIMessage(content=response))

            # Display conversation
            for message in st.session_state.chat_history:
                if isinstance(message, AIMessage):
                    with st.chat_message("AI"):
                        st.write(message.content)
                elif isinstance(message, HumanMessage):
                    with st.chat_message("Human"):
                        st.write(message.content)
        else:
            st.info("Please enter a URL")

    elif choice == "Settings ⚙️":
        if st.session_state.logged_in:
            st.subheader("Update Your API Keys and Password 🔧")
            new_password = st.text_input("New Password 🔑", type='password')
            new_openai_key = st.text_input("New OpenAI API Key 🌐",type='password')
            if st.button("Update 🔄"):
                update_userdata(st.session_state.username, make_hashes(new_password), new_openai_key)
                st.success("Settings Updated Successfully ✅")
            st.session_state.last_page = choice
        else:
            st.warning("Please login to access this feature 🔐")
    # Contact Form
    with st.expander("Contact us"):
        with st.form(key='contact', clear_on_submit=True):
            email = st.text_input('Contact Email')
            st.text_area("Query",placeholder="Please fill in all the information or we may not be able to process your request")  
            submit_button = st.form_submit_button(label='Send Information')

if __name__ == '__main__':
    st.set_page_config(page_title="WebBot 🤖",
                       page_icon="✨", layout="centered", initial_sidebar_state="auto")
    main()