import base64
import io
from dotenv import load_dotenv
import os
from PIL import Image
import pdf2image
import google.generativeai as genai
import streamlit as st
import sqlite3  # For database operations
import streamlit.components.v1 as components
import bcrypt






#Password Hashing

def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed_password):
    """Verify a password against its hashed version."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def register_user(username, password):
    """Register a new user in the database."""
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    try:
        hashed_password = hash_password(password)
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("Username already exists. Please choose a different username.")
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    """Authenticate a user by checking the database."""
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and verify_password(password, user[0]):
        return True
    return False



#2. Session Expiry
import time
# Add this to your session state initialization
if "last_activity" not in st.session_state:
    st.session_state.last_activity = time.time()

# Check for inactivity (e.g., 30 minutes)
def check_session_expiry():
    if time.time() - st.session_state.last_activity > 1800:  # 30 minutes
        st.session_state.logged_in = False
        st.session_state.current_page = "auth_page"
        st.warning("Session expired. Please log in again.")
        st.experimental_rerun()

# Update last activity time on user interaction
st.session_state.last_activity = time.time()


# 3. Error Handling for Gemini API
def get_gemini_response(input_text, pdf_content, prompt):
    """Get AI response from Google Gemini."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([input_text, pdf_content[0], prompt])
        return response.text
    except Exception as e:
        st.error(f"Error generating response: {str(e)}")
        return None

# 4. Improve PDF Processing
def input_pdf_setup(uploaded_file):
    """Convert uploaded PDF to images and encode them for Gemini API."""
    try:
        if not uploaded_file:
            raise FileNotFoundError("No file uploaded")

        # Convert PDF to images
        images = pdf2image.convert_from_bytes(uploaded_file.read())

        if not images:
            raise ValueError("Could not convert PDF to image")

        pdf_parts = []
        for idx, image in enumerate(images):
            # Convert each page to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()

            # Encode image to base64 for API
            pdf_parts.append({
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()
            })

        return pdf_parts
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

# Load API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("Google API Key not found! Please check your .env file.")
genai.configure(api_key=api_key)

# Database setup
def init_db():
    """Initialize the SQLite database and create a users table if it doesn't exist."""
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    

# Function to register a new user
def register_user(username, password):
    """Register a new user in the database."""
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("Username already exists. Please choose a different username.")
        return False
    finally:
        conn.close()

# Function to authenticate a user
def authenticate_user(username, password):
    """Authenticate a user by checking the database."""
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user is not None





# Function to process PDF
def input_pdf_setup(uploaded_file):
    """Convert uploaded PDF to an image and encode it for Gemini API."""
    try:
        if not uploaded_file:
            raise FileNotFoundError("No file uploaded")

        # Convert PDF to images
        images = pdf2image.convert_from_bytes(uploaded_file.read())

        if not images:
            raise ValueError("Could not convert PDF to image")

        first_page = images[0]

        # Convert first page to bytes
        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        # Encode image to base64 for API
        pdf_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()
            }
        ]
        return pdf_parts
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

# Function to display uploaded resume
def show_uploaded_resume(uploaded_file):
    """Display the uploaded resume in the app."""
    if uploaded_file is not None:
        # Save the uploaded file temporarily
        with open("temp_resume.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Display the PDF in the app
        with open("temp_resume.pdf", "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.write("No resume uploaded yet.")

# Function to get Gemini response
def get_gemini_response(input_text, pdf_content, prompt):
    """Get AI response from Google Gemini."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([input_text, pdf_content[0], prompt])
    return response.text

# Login and Registration Page
def auth_page():
    """Display login and registration forms."""
    st.title("Welcome to ATS Resume Expert")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.header("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        login_button = st.button("Login")

        if login_button:
            if authenticate_user(login_username, login_password):
                st.session_state.logged_in = True
                st.session_state.username = login_username
                st.session_state.current_page = "main_app"  # Set the current page to main app
                st.success("Login successful!")
            else:
                st.error("Invalid username or password.")

    with tab2:
        st.header("Register")
        reg_username = st.text_input("Choose a Username", key="reg_username")
        reg_password = st.text_input("Choose a Password", type="password", key="reg_password")
        reg_button = st.button("Register")

        if reg_button:
            if reg_username and reg_password:
                if register_user(reg_username, reg_password):
                    st.success("Registration successful! Please login.")
            else:
                st.error("Please fill in all fields.")



# Add this function to calculate the ATS score
def get_ats_score(pdf_content, job_description):
    """Calculate the ATS score for the uploaded resume."""
    input_prompt_ats = """
    You are a skilled ATS (Applicant Tracking System) scanner with expertise in evaluating resumes. 
    Your task is to analyze the provided resume and calculate an ATS score based on the following criteria:
    1. Keyword match with the job description.
    2. Formatting and structure of the resume.
    3. Relevance of skills and experience to the job.
    4. Clarity and professionalism of the content.

    Provide the ATS score as a percentage (0-100%) and a brief explanation of the score.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([input_prompt_ats, pdf_content[0], job_description])
    return response.text

# Add this button and functionality to the main_app function


# Main App


def main_app():
    """Main application after login."""
    st.set_page_config(page_title="ATS Resume Expert")
    st.header(f"Welcome, {st.session_state.username}!")
    st.write("ATS Tracking System")
    

    # Back button to return to the login page
    if st.button("⬅ Back to Login"):
        st.session_state.logged_in = False
        st.session_state.current_page = "auth_page"
        st.experimental_rerun()  # Return the app to reflect changes

    input_text = st.text_area("Job Description:", key="input")
    uploaded_file = st.file_uploader("Upload Your resume (PDF)...", type=["pdf"])
    uploaded_video = st.file_uploader("Upload a Video (optional)", type=["mp4", "avi", "mov"])


    

    # Display the uploaded resume
    if uploaded_file is not None:
        st.subheader("Uploaded Resume")
        show_uploaded_resume(uploaded_file)


    # Create columns for buttons
    col1, col2, col3, col4 = st.columns(4)  # Create 4 columns for 4 buttons

    with col1:
        submit_ats_score = st.button("Show My ATS Score")
    with col2:
        submit1 = st.button("Tell me About the Resume")
    with col3:
        submit2 = st.button("How Can I Improve my Skills")
    with col4:
        submit3 = st.button("Percentage Match")

    input_prompt1 = """
    You are an experienced Technical Human Resource Manager. Your task is to review the provided resume against the job description. 
    Please share your professional evaluation on whether the candidate's profile aligns with the role. 
    Highlight the strengths and weaknesses of the applicant in relation to the specified job requirements.
    """ 

    input_prompt3 = """
    You are a skilled ATS (Applicant Tracking System) scanner with a deep understanding of data science and ATS functionality. 
    Your task is to evaluate the resume against the provided job description. Provide the percentage match if the resume aligns
    with the job description. First, output the percentage, then highlight the missing keywords, and finally provide your overall thoughts.
    """

    if submit_ats_score:
        if uploaded_file is not None:
            pdf_content = input_pdf_setup(uploaded_file)
            if pdf_content:
                st.subheader("ATS Score")
                with st.spinner("Calculating ATS Score..."):  # Show a spinner while processing
                    ats_score = get_ats_score(pdf_content, input_text)
                    st.write(ats_score)
        else:
            st.write("⚠ Please upload the resume.")

    if submit1:
        if uploaded_file is not None:
            pdf_content = input_pdf_setup(uploaded_file)
            if pdf_content:
                response = get_gemini_response(input_prompt1, pdf_content, input_text)
                st.subheader("The Response is:")
                st.write(response)
        else:
            st.write("⚠ Please upload the resume.")

    

    # Video URLs and titles
    youtube_videos = [
        {"url": "https://www.youtube.com/watch?v=Tt08KmFfIYQ", "title": "Video 1: Understanding ATS Systems"},
        {"url": "https://www.youtube.com/watch?v=HG68Ymazo18", "title": "Video 2: Improving Your Skills"},
        {"url": "https://www.youtube.com/watch?v=9RkxevxGIoU", "title": "Video 3: Building Your Resume"}
    ]

    if submit2:
        if youtube_videos:
            st.write("### Suggested Videos to Improve Your Skills:")

            # Loop through videos and display each with title and styled video frame
            for video in youtube_videos:
                st.markdown(f"""
                <div style="border: 2px solid #e74c3c; border-radius: 10px; padding: 15px; margin-bottom: 20px; background-color: #ffffff; box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); width: 80%; margin-left: auto; margin-right: auto;">
                    <h4 style="color: #e74c3c; font-size: 22px; font-weight: bold; text-align: center; margin-bottom: 15px;">{video['title']}</h4>
                    <div style="position: relative; padding-top: 56.25%; border-radius: 10px; overflow: hidden; background-color: #f1f1f1;">
                        <iframe width="100%" height="100%" src="{video['url'].replace('watch?v=', 'embed/')}?autoplay=1" frameborder="0" allowfullscreen style="position: absolute; top: 0; left: 0;"></iframe>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("---")  # Add a divider for better separation between videos
        else:
            st.write("⚠ Please provide valid YouTube URLs.")

    elif submit3:
        if uploaded_file is not None:
            pdf_content = input_pdf_setup(uploaded_file)
            if pdf_content:
                response = get_gemini_response(input_prompt3, pdf_content, input_text)
                st.subheader("The Response is:")
                st.write(response)
        else:
            st.write("⚠ Please upload the resume.")

# Initialize the database
init_db()

# Session Management and App Flow
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "auth_page"

# Page routing
if st.session_state.current_page == "auth_page":
    auth_page()
elif st.session_state.current_page == "main_app":
    main_app() 
