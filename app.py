import streamlit as st
import google.generativeai as genai
import os

# --- SMART API KEY LOADER ---
# Try to get the key from Streamlit Cloud Secrets first (Production)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    # If it fails, we are running locally, so use the .env file (Development)
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

# Configure the LLM
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("API Key not found. Please check your .env file or Streamlit Secrets.")
    st.stop()

# --- LLM ENGINE FUNCTIONS ---
def generate_questions(process_description):
    prompt = f"""
    You are an expert business analyst. A user wants to create a Standard Operating Procedure (SOP) for the following process:
    '{process_description}'
    Generate exactly 5 clarifying questions to ask the user to gather the necessary details (e.g., tools used, roles involved, edge cases). 
    Return ONLY the 5 questions separated by newlines, with no extra text or numbering.
    """
    response = model.generate_content(prompt)
    # Split the response by newlines and clean up empty strings
    questions = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
    # Ensure we only return 5, even if the model gets chatty
    return questions[:5]

def generate_final_sop(process, qa_pairs):
    qa_text = "\n".join([f"Q: {pair['Q']}\nA: {pair['A']}" for pair in qa_pairs])
    prompt = f"""
    Write a highly professional, structured Standard Operating Procedure (SOP) for the following process: '{process}'.
    Use the following details gathered from the user to build it:
    {qa_text}
    
    Structure it with:
    1. Objective
    2. Roles & Responsibilities
    3. Step-by-Step Procedure
    4. Exceptions/Edge Cases
    """
    response = model.generate_content(prompt)
    return response.text

# --- STATE MANAGEMENT ---
if 'stage' not in st.session_state:
    st.session_state.stage = 'intake'
if 'process_desc' not in st.session_state:
    st.session_state.process_desc = ""
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'answers' not in st.session_state:
    st.session_state.answers = []
if 'current_q_index' not in st.session_state:
    st.session_state.current_q_index = 0

# --- UI LAYOUT ---
st.title("⚙️ Enterprise Workflow & SOP Generator")

# PHASE 1: INTAKE
if st.session_state.stage == 'intake':
    st.write("### Step 1: Define the Workflow")
    desc = st.text_area("Describe the business process briefly (2-3 sentences):", placeholder="e.g., Onboarding a new remote software engineer...")
    
    if st.button("Analyze Workflow"):
        if desc:
            st.session_state.process_desc = desc
            with st.spinner("Analyzing process and generating targeted questions..."):
                st.session_state.questions = generate_questions(desc)
            st.session_state.stage = 'interview'
            st.rerun()

# PHASE 2: INTERVIEW
elif st.session_state.stage == 'interview':
    total_q = len(st.session_state.questions)
    
    # Safety check in case the LLM failed to generate questions
    if total_q == 0:
        st.error("Failed to generate questions. Please start over.")
        if st.button("Restart"):
            st.session_state.clear()
            st.rerun()
            
    q_index = st.session_state.current_q_index
    st.write(f"### Clarifying Question {q_index + 1} of {total_q}")
    st.progress((q_index) / total_q)
    
    current_question = st.session_state.questions[q_index]
    st.info(current_question)
    
    # Form to handle "Enter" key submissions smoothly
    with st.form(key=f'q_form_{q_index}'):
        answer = st.text_input("Your Answer:")
        submit_button = st.form_submit_button(label='Next')
        
        if submit_button and answer:
            st.session_state.answers.append({"Q": current_question, "A": answer})
            if q_index < total_q - 1:
                st.session_state.current_q_index += 1
            else:
                st.session_state.stage = 'generation'
            st.rerun()

# PHASE 3: ASSEMBLY & OUTPUT
elif st.session_state.stage == 'generation':
    st.write("### Assembling your SOP...")
    with st.spinner("Compiling structural data, roles, and edge cases..."):
        sop = generate_final_sop(st.session_state.process_desc, st.session_state.answers)
        st.session_state.final_sop = sop
        st.session_state.stage = 'complete'
        st.rerun()

# PHASE 4: COMPLETE
elif st.session_state.stage == 'complete':
    st.success("SOP Generated Successfully!")
    
    # Display the final document
    with st.container(border=True):
        st.markdown(st.session_state.final_sop)
    
    if st.button("Start a New Process"):
        st.session_state.clear()
        st.rerun()