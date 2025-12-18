# ========================================================
# UNEB Primary 7/6 Exam Preparation Platform
# Multi-AI System: Gemini (Primary) → Cohere → HF (Fallback)
# ========================================================

import os
import json
from datetime import datetime
import gradio as gr
import time
from io import BytesIO
from PIL import Image
import csv
from pathlib import Path
import re

# ---------- 1. Configure AI Systems ----------
# Primary: Gemini (with vision support)
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
    print("✓ Gemini AI initialized (PRIMARY with Vision)")
except Exception as e:
    print(f"✗ Gemini Error: {e}")
    gemini_model = None

# Secondary: Cohere
try:
    import cohere
    cohere_client = cohere.Client(os.getenv("COHERE_API_KEY"))
    print("✓ Cohere initialized (SECONDARY)")
except Exception as e:
    print(f"✗ Cohere Error: {e}")
    cohere_client = None

# Tertiary: Hugging Face Inference
try:
    from huggingface_hub import InferenceClient
    hf_client = InferenceClient(api_key=os.environ.get("HF_TOKEN"))
    print("✓ Hugging Face initialized (FALLBACK)")
except Exception as e:
    print(f"✗ HF Error: {e}")
    hf_client = None

# ---------- 2. Unified AI Function ----------
def ask_ai(prompt, temperature=0.7, max_retries=2, image=None):
    """Try models: Gemini → Cohere → HF
    If image provided, only Gemini can process it"""
    
    # Try Gemini first (Primary) - handles both text and images
    if gemini_model:
        for attempt in range(max_retries):
            try:
                if image:
                    response = gemini_model.generate_content(
                        [prompt, image],
                        generation_config=genai.types.GenerationConfig(
                            temperature=temperature,
                        )
                    )
                else:
                    response = gemini_model.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=temperature,
                        )
                    )
                return response.text, "gemini"
            except Exception as e:
                print(f"✗ Gemini attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
    
    if image:
        return " Image analysis requires Gemini AI. Please check API configuration.", "error"
    
    # Try Cohere (Secondary) - text only
    if cohere_client:
        for attempt in range(max_retries):
            try:
                response = cohere_client.chat(
                    model="command-r-plus-08-2024",
                    message=prompt,
                    temperature=temperature
                )
                return response.text, "cohere"
            except Exception as e:
                print(f"✗ Cohere attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
    
    # Try Hugging Face (Fallback) - text only
    if hf_client:
        try:
            completion = hf_client.chat.completions.create(
                model="Qwen/Qwen2.5-72B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=2000
            )
            return completion.choices[0].message.content, "hf"
        except Exception as e:
            print(f"✗ HF failed: {e}")
    
    return " All AI services failed. Please try again later.", "error"

# ---------- 3. Uganda Primary Curriculum Syllabus (P6 & P7 Only, by Subject) ----------
# Topics below are expanded and aligned to typical NCDC/UNEB primary curriculum themes
# (see https://ncdc.go.ug/ and Ministry of Education resources for official documents).
syllabus_topics = {
    "Primary 6": {
        "Mathematics": [
            "Whole Numbers - Addition & Subtraction",
            "Whole Numbers - Multiplication & Division",
            "Factors, Multiples and Prime Numbers",
            "Fractions & Decimals",
            "Money & Making Change",
            "Measurement - Length, Mass & Capacity",
            "Time - Hours, Minutes & Conversion",
            "Geometry - Shapes, Symmetry & Angles (basic)",
            "Data Handling - Tables, Bar Graphs & Pictograms",
            "Ratio & Proportion",
            "Introduction to Algebra - Simple Equations",
            "Basic Percentages and Problem Solving"
        ],
        "English": [
            "Reading Comprehension - Short Passages",
            "Grammar - Tenses, Parts of Speech, Sentence Structure",
            "Vocabulary Building & Spelling",
            "Composition - Story and Letter Writing",
            "Punctuation & Capitalization",
            "Clarity in Expression - Cohesion and Coherence",
            "Cloze Tests & Short Answer Questions",
            "Listening and Speaking Basics"
        ],
        "Social Studies": [
            "Local Community - Roles, Services & Leaders",
            "Local History & Traditions",
            "Civics - Rights, Responsibilities & Good Citizenship",
            "Map Skills - Directions, Symbols, Scale (basic)",
            "Resources and Local Economy - Farming, Trade, Markets",
            "Culture, Customs and Heritage",
            "Environment & Conservation - Local Examples",
            "Health, Sanitation and Community Wellbeing",
            "Basic Local Government Structures and Participation",
            "Road Safety and Community Rules"
        ],
        "Science": [
            "Living & Non-Living Things - Characteristics",
            "Plants - Parts and Functions",
            "Animals - Habitats and Adaptations",
            "Human Body - Health, Nutrition & Hygiene",
            "Materials & Their Properties",
            "Forces and Motion - Simple Examples",
            "Light, Heat and Sound (basic concepts)",
            "Environment and Natural Resources",
            "Simple Experiments and Observations"
        ]
    },
    "Primary 7": {
        "Mathematics": [
            "Integers & Operations",
            "Fractions - Addition, Subtraction, Multiplication & Division",
            "Decimals & Percentages",
            "Ratio, Rate & Proportion",
            "Algebraic Expressions & Simple Equations",
            "Geometry - Angles, Triangles and Quadrilaterals",
            "Mensuration - Area, Perimeter and Volume (basic)",
            "Statistics & Probability - Averages and Data Interpretation",
            "Coordinate Geometry - Introduction",
            "Number Theory - Factors, HCF & LCM",
            "Problem Solving Strategies"
        ],
        "English": [
            "Comprehension - Longer Passages & Questioning",
            "Grammar - Sentence Transformation, Tenses, Agreement",
            "Composition - Stories, Letters, Reports and Dialogues",
            "Cloze & Summary Writing",
            "Vocabulary - Synonyms, Antonyms & Contextual Use",
            "Listening Skills and Oral Expression",
            "Directed Writing and Examination Techniques"
        ],
        "Social Studies": [
            "History - Key Events in Uganda and East Africa (pre-colonial, colonial, independence)",
            "Civics and Governance - Structure of Government, Roles and Rights",
            "Geography - Maps, Physical Features, Weather, Climate and Resources",
            "Economy - Agriculture, Trade, Markets, Production and Consumption",
            "Community Development - Projects, Participation and Leadership",
            "Citizenship Education - Rights, Responsibilities and Human Rights",
            "Culture, National Symbols and Heritage",
            "Local and National Government - Functions and Services",
            "Environmental Issues - Conservation, Deforestation, Pollution",
            "Global Connections - Trade, Aid and Regional Cooperation"
        ],
        "Science": [
            "Living Things - Classification, Life Cycles and Ecosystems",
            "Plants and Animals - Structure and Function",
            "Human Body Systems - Digestive, Respiratory, Circulatory (basic)",
            "Health and Disease Prevention",
            "Forces, Magnets and Motion",
            "Energy - Sources and Uses",
            "Materials and Their Uses (including mixtures and separation)",
            "Environment - Habitats, Conservation and Sustainable Use",
            "Simple Scientific Investigation and Reporting"
        ]
    }
}

# ---------- 4. Generate Practice Questions (Customizable) ----------
def generate_sample_questions(grade_level, subject, topic, num_questions=10):
    """Fallback: Generate sample questions locally when AI is unavailable.
    This function is subject-aware and supplies simple sample questions for common topics."""
    # Basic sample banks keyed by subject/topic
    samples = {
        "Mathematics": {
            "Integers & Operations": [
                "Q1. Calculate the sum of -20 and -15.",
                "Q2. A farmer bought 40 oranges and then sold 25 of them. What is the difference between the number of oranges bought and sold?",
                "Q3. Simplify: 36 - (-10) + 5.",
                "Q4. Find the value of -2(8) + 15.",
                "Q5. A car is parked at -10 meters. If it moves up 15 meters, what is its final position?",
                "Q6. Calculate the product of -4 and 5.",
                "Q7. A boat descends 12 meters, then rises 8 meters. What is its final position relative to sea level?",
                "Q8. Simplify: 2(-3) + 5(-2).",
                "Q9. A rabbit hops 7 meters forward and then 4 meters backward. What is the net distance covered?",
                "Q10. A plane descends 300 meters and then ascends 200 meters. What is the plane's final position?",
            ],
            "Fractions - Addition & Subtraction": [
                "Q1. Add 1/4 and 1/3.",
                "Q2. Subtract 2/5 from 3/5.",
                "Q3. What is 1/2 + 1/4 + 1/8?",
                "Q4. Calculate 7/8 - 1/4.",
                "Q5. Find the sum of 2/3 and 1/6.",
                "Q6. Subtract 3/10 from 9/10.",
                "Q7. Add 1/5, 2/5, and 1/5.",
                "Q8. What is 5/6 - 1/3?",
                "Q9. Calculate 3/4 + 2/8.",
                "Q10. Find 11/12 - 1/4.",
            ],
        },
        "English": {
            "Comprehension - Passages & Questions": [
                "Q1. Read the passage and answer: What is the main idea of paragraph 2?",
                "Q2. From the passage, extract two reasons the author gives for saving water.",
                "Q3. What does the word 'frugal' mean in the passage?",
                "Q4. Give a title for the passage in not more than five words.",
                "Q5. Why did the character decide to leave home?",
            ],
            "Grammar - Sentence Transformation & Tenses": [
                "Q1. Change to passive voice: 'The teacher marked the tests.'",
                "Q2. Fill in the blank with the correct tense: 'She ___ (go) to school yesterday.'",
                "Q3. Correct the sentence: 'He don't like vegetables.'",
                "Q4. Combine the sentences: 'He ran fast. He missed the bus.'",
                "Q5. Rewrite in reported speech: 'She said, \"I will come.\"'",
            ]
        },
        "Science": {
            "Living Things - Classification": [
                "Q1. State two differences between plants and animals.",
                "Q2. Name three groups of living organisms.",
                "Q3. How do leaves help plants to survive?",
                "Q4. What is photosynthesis? Give a simple definition.",
                "Q5. Explain why animals need oxygen.",
            ],
            "Forces, Magnets and Motion": [
                "Q1. Define force with an example.",
                "Q2. What does a magnet attract?",
                "Q3. Give one example of a push and one example of a pull.",
            ]
        },
        "Social Studies": {
            "History - Uganda & East Africa": [
                "Q1. Name one important event in Uganda's history and explain why it is important.",
                "Q2. Who was the first person to unite (example) ...?",
            ],
            "Geography - Maps, Weather & Resources": [
                "Q1. Give two uses of a map.",
                "Q2. What are the main types of weather in Uganda?",
            ]
        }
    }
    
    subject_bank = samples.get(subject, {})
    # Try to match topic within subject bank
    topic_key = None
    for key in subject_bank:
        if key.lower() in topic.lower() or topic.lower() in key.lower():
            topic_key = key
            break
    
    if topic_key:
        qs = subject_bank[topic_key][:num_questions]
    else:
        # Generic fallback per subject
        qs = [f"Q{i+1}. Sample {subject} question {i+1} on {topic}." for i in range(num_questions)]
    
    return "\n\n".join(qs)

def generate_practice_questions(grade_level, subject, topic, num_questions=10):
    """Generate multiple questions with robust text parsing (not JSON). Subject-aware prompt."""
    
    if not topic:
        return None, "⚠️ Please select a topic first!"
    
    prompt = f"""Generate exactly {num_questions} UNEB-style {subject} questions for {grade_level} students on: "{topic}"

Format your response EXACTLY like this:
Q1. [Question text here]
Q2. [Question text here]
Q3. [Question text here]
... and so on up to Q{num_questions}

Each question should be:
- Clear and exam-like
- Appropriate difficulty for {grade_level}
- Self-contained (includes all necessary information)
- Solvable in 2-5 minutes for short-answer questions

Start immediately with Q1. Do not include any introduction or explanation.
"""
    
    response, source = ask_ai(prompt, temperature=0.6)
    
    # Fallback: if AI fails or returns empty, use local generator (now subject-aware)
    if "All AI services failed" in response or not response or response.strip() == "":
        response = generate_sample_questions(grade_level, subject, topic, num_questions)

    # Parse questions robustly using regex to support multi-digit numbers (Q1..Q10..)
    questions = []
    current_question = None
    q_re = re.compile(r'^Q(\d+)\.?\s*(.*)', re.IGNORECASE)

    for raw_line in response.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = q_re.match(line)
        if m:
            # Start of a new question
            if current_question:
                questions.append(current_question.strip())
            # Include the rest of the line after the Qn. prefix
            rest = m.group(2) or ''
            current_question = f"Q{m.group(1)}. {rest.strip()}"
        else:
            # Continuation of previous question (append with space)
            if current_question:
                current_question += ' ' + line

    if current_question:
        questions.append(current_question.strip())
    
    # Ensure we got questions
    if not questions:
        return None, " Failed to generate questions. Please try again."
    
    questions = questions[:num_questions]
    
    # Format for display
    formatted = "\n\n".join(questions)
    return questions, formatted

# ---------- 5. Grade/Mark Student Answers ----------
def grade_student_answers(questions, student_answers, grade_level, topic, subject=None):
    """Grade all student answers and provide feedback"""
    
    if not questions or not student_answers:
        return " No questions or answers to grade."
    
    feedback_list = []
    
    for i, question_text in enumerate(questions):
        student_answer = student_answers.get(i, "") or ""
        
        if not student_answer.strip():
            feedback_list.append(f"Q{i+1}: [NOT ANSWERED]")
            continue
        
        # Create grading prompt
        grading_prompt = f"""You are an experienced UNEB examiner for {grade_level} students. Subject: {subject or 'General'}
        
Question: {question_text}

Student's Answer: {student_answer}

Provide:
1. Is this answer correct? (Yes/Partially/No)
2. Score: X/10
3. Explanation: Brief feedback on what's correct and what needs improvement
4. If wrong, provide the correct approach

Keep feedback concise but clear. Be encouraging."""
        
        grade_response, _ = ask_ai(grading_prompt, temperature=0.3)
        feedback_list.append(f"Q{i+1}:\n{grade_response}\n")
    
    full_feedback = "\n" + "="*60 + "\n".join(feedback_list)
    return full_feedback

# ---------- 6. Session Tracking ----------
class StudentSession:
    def __init__(self, student_name="Student"):
        self.student_name = student_name
        self.current_questions = []
        self.current_answers = {}
        self.current_topic = None
        self.current_grade = None
        self.last_feedback = None
        
    def clear_session(self):
        self.current_questions = []
        self.current_answers = {}
        self.current_topic = None
        self.current_grade = None
        self.last_feedback = None

session = StudentSession()

# ---------- 7. Download Functions ----------
def download_questions_file(questions_list, topic, grade_level, subject=None):
    """Download questions as text file"""
    if not questions_list:
        return None
    
    def sanitize_filename(name: str) -> str:
        # Replace unsafe characters with underscore
        return re.sub(r"[^A-Za-z0-9_.()-]", "_", str(name))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_grade = sanitize_filename(grade_level)
    safe_topic = sanitize_filename(topic)
    safe_subject = sanitize_filename(subject) if subject else ""
    subject_tag = f"_{safe_subject}" if safe_subject else ""
    filename = f"questions_{safe_grade}{subject_tag}_{safe_topic}_{timestamp}.txt"
    
    content = f"""UNEB EXAM PRACTICE QUESTIONS
{'='*50}
Grade Level: {grade_level}
Subject: {subject or 'N/A'}
Topic: {topic}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Total Questions: {len(questions_list)}
{'='*50}

"""
    
    for question in questions_list:
        content += question + "\n\n"
    
    content += f"""
{'='*50}
INSTRUCTIONS:
1. Write your working clearly for each question
2. Show all steps in your solution
3. Once complete, submit to AI for correction
4. Review the feedback to improve

Good luck! 
"""
    
    filepath = os.path.join("downloads", filename)
    os.makedirs("downloads", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return os.path.abspath(filepath)


def download_questions_pdf(questions_list, topic, grade_level, subject=None):
    """Generate a simple PDF with the questions, return filepath."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import mm
    except Exception:
        return None

    def sanitize_filename(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.()-]", "_", str(name))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_grade = sanitize_filename(grade_level)
    safe_topic = sanitize_filename(topic)
    safe_subject = sanitize_filename(subject) if subject else ""
    subject_tag = f"_{safe_subject}" if safe_subject else ""
    filename = f"questions_{safe_grade}{subject_tag}_{safe_topic}_{timestamp}.pdf"
    filepath = os.path.join("downloads", filename)
    os.makedirs("downloads", exist_ok=True)

    doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    heading = ParagraphStyle('Heading', parent=styles['Heading1'], alignment=0)
    elems = []

    elems.append(Paragraph("UNEB EXAM PRACTICE QUESTIONS", styles['Title']))
    elems.append(Spacer(1, 4*mm))
    meta = f"Grade Level: {grade_level}  &nbsp;&nbsp; Subject: {subject or 'N/A'}  &nbsp;&nbsp; Topic: {topic}  &nbsp;&nbsp; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    elems.append(Paragraph(meta, normal))
    elems.append(Spacer(1, 6*mm))

    for i, q in enumerate(questions_list):
        # Remove any leading Qn. if present
        q_text = re.sub(r'^Q\d+\.?\s*', '', q)
        elems.append(Paragraph(f"<b>Q{i+1}.</b> {q_text}", normal))
        elems.append(Spacer(1, 3*mm))

    try:
        doc.build(elems)
        return os.path.abspath(filepath)
    except Exception:
        return None

def download_feedback_file(feedback_text, topic, grade_level, subject=None):
    """Download AI feedback/corrections"""
    if not feedback_text:
        return None
    
    def sanitize_filename(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.()-]", "_", str(name))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_grade = sanitize_filename(grade_level)
    safe_topic = sanitize_filename(topic)
    safe_subject = sanitize_filename(subject) if subject else ""
    subject_tag = f"_{safe_subject}" if safe_subject else ""
    filename = f"feedback_{safe_grade}{subject_tag}_{safe_topic}_{timestamp}.txt"
    
    content = f"""AI CORRECTION & FEEDBACK
{'='*50}
Student: {session.student_name}
Grade Level: {grade_level}
Subject: {subject or 'N/A'}
Topic: {topic}
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
{'='*50}

{feedback_text}

{'='*50}
Review this feedback carefully to understand where you went wrong.
Practice similar questions to strengthen this topic.
"""
    
    filepath = os.path.join("downloads", filename)
    os.makedirs("downloads", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return os.path.abspath(filepath)

# ---------- 8. Gradio UI ----------
css_styles = """
    .header-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        color: white;
        margin-bottom: 20px;
    }
    
    .tab-content {
        padding: 20px;
    }
    
    .question-display {
        background: #f9fafb;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #667eea;
        margin: 15px 0;
        color: #111827;
        font-size: 16px;
        line-height: 1.5;
        overflow-wrap: break-word;
    }
    
    .feedback-box {
        background: #f0fdf4;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #10b981;
        color: #064e3b;
        font-size: 16px;
        line-height: 1.5;
        overflow-wrap: break-word;
    }
    
    .answer-section {
        background: #fef9e7;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
    }
    /* Slightly larger base text for smaller screens */
    @media (max-width: 900px) {
        .question-display, .feedback-box { font-size: 18px; }
    }
"""

with gr.Blocks(title="UNEB Exam Prep - Primary 6 & 7", theme=gr.themes.Soft(), css=css_styles) as app:
    
    gr.Markdown("""
    #  UNEB Exam Practice
    ## Primary 6 & 7 — Multiple Subjects
    """)
    
    # Global state for questions
    questions_state = gr.State(value=[])
    
    # Student name input
    with gr.Group():
        student_name_input = gr.Textbox(
            label="Your Name",
            placeholder="Enter your name",
            value="Student"
        )
    
    def update_student_name(name):
        session.student_name = name if name else "Student"
        return f"Welcome, {session.student_name}!"
    
    student_name_input.change(update_student_name, student_name_input, None)
    
    with gr.Tabs():
        # ===== TAB 1: GENERATE QUESTIONS =====
        with gr.Tab("1️⃣ Generate Questions"):
            gr.Markdown("### Step 1: Generate Practice Questions\n\nChoose the Grade, Subject and Topic, then set the Number of Questions (1–100).")
            
            with gr.Row():
                grade_input = gr.Dropdown(
                    choices=["Primary 6", "Primary 7"],
                    label="Grade Level",
                    value="Primary 7"
                )
                subject_input = gr.Dropdown(
                    choices=["Mathematics", "English", "Social Studies", "Science"],
                    label="Subject",
                    value="Mathematics"
                )
                topic_input = gr.Dropdown(
                    label="Topic",
                    choices=syllabus_topics["Primary 7"]["Mathematics"],
                    value=syllabus_topics["Primary 7"]["Mathematics"][0]
                )
            
            # Update topics when grade or subject changes
            def update_topics(grade, subject):
                topics = syllabus_topics.get(grade, {}).get(subject, [])
                if not topics:
                    topics = ["General - " + subject]
                return gr.Dropdown(choices=topics, value=topics[0])
            
            grade_input.change(update_topics, [grade_input, subject_input], topic_input)
            subject_input.change(update_topics, [grade_input, subject_input], topic_input)
            
            with gr.Row():
                num_questions_input = gr.Slider(minimum=1, maximum=100, step=1, value=20, label="Number of Questions")
                generate_btn = gr.Button(" Generate Questions", variant="primary", size="lg")
            
            questions_output = gr.HTML(
                value="",
                elem_classes="question-display"
            )

            status_output = gr.Textbox(
                label="Status",
                interactive=False,
                lines=1
            )

            with gr.Row():
                download_questions_btn = gr.DownloadButton(" Download Questions (PDF)")
                copy_btn = gr.Button(" Copy Questions")
            
            # Generate questions handler
            def generate_and_display(grade, subject, topic, num_questions):
                questions_list, formatted_text = generate_practice_questions(grade, subject, topic, num_questions=num_questions)

                if questions_list is None:
                    return "", questions_state.value, " Generation failed"

                session.current_questions = questions_list
                session.current_grade = grade
                session.current_topic = topic
                # Also store subject
                session.current_subject = subject

                # Build accessible HTML list for better rendering on iPad/Safari
                items_html = "".join([f"<li>{q.split('.',1)[1].strip() if '.' in q else q}</li>" for q in questions_list])
                html = f"<div><ol style='margin:0 0 0 1.2rem;padding:0'>{items_html}</ol></div>"
                return html, questions_list, f" Generated {len(questions_list)} {subject} questions on {topic}"
            
            generate_btn.click(
                fn=generate_and_display,
                inputs=[grade_input, subject_input, topic_input, num_questions_input],
                outputs=[questions_output, questions_state, status_output]
            )            
            # Download handler - returns file path for gr.DownloadButton
            def download_qns():
                if not session.current_questions:
                    return None
                try:
                    # Prefer PDF export; fall back to plain text if PDF library missing
                    subject = getattr(session, 'current_subject', None)
                    pdf_path = download_questions_pdf(session.current_questions, session.current_topic, session.current_grade, subject=subject)
                    if pdf_path:
                        return pdf_path
                    # Fallback to text
                    filepath = download_questions_file(session.current_questions, session.current_topic, session.current_grade, subject=subject)
                    return filepath
                except Exception as e:
                    return None
            
            download_questions_btn.click(
                fn=download_qns,
                inputs=[],
                outputs=download_questions_btn
            )
        
        # ===== TAB 2: SUBMIT ANSWERS =====
        with gr.Tab("2️⃣ Answer Questions"):
            gr.Markdown("### Step 2: Answer the Questions")
            gr.Markdown("Write out your working and answers. You can use any of the three methods below.")
            
            with gr.Row():
                method_info = gr.Textbox(
                    label="How to Submit Answers",
                    value="Method 1: Draw/Write in canvas\nMethod 2: Upload photo of your written work\nMethod 3: Type your answers directly",
                    interactive=False,
                    lines=3
                )
            
            with gr.Tabs():
                # Method 1: Draw
                with gr.Tab("✏️ Draw Answers"):
                    canvas = gr.Sketchpad(
                        label="Draw or write your answers here",
                        type="pil",
                        height=500,
                        brush=gr.Brush(
                            colors=["#000000", "#0000FF", "#FF0000"],
                            default_size=4
                        )
                    )
                    canvas_status = gr.Textbox(
                        label="Canvas Status",
                        interactive=False,
                        value="Ready to draw"
                    )
                
                # Method 2: Upload
                with gr.Tab("📸 Upload Photo"):
                    upload_image = gr.Image(
                        label="Upload photo of your written work",
                        type="pil",
                        height=500
                    )
                    upload_status = gr.Textbox(
                        label="Upload Status",
                        interactive=False,
                        value="Ready to upload"
                    )
                
                # Method 3: Type
                with gr.Tab(" Type Answers"):
                    gr.Markdown("Type your answers here, numbered Q1, Q2, etc.")
                    typed_answers = gr.Textbox(
                        label="Type your answers",
                        lines=15,
                        placeholder="Q1. [Your answer]\nQ2. [Your answer]\n..."
                    )
            
            # Combined submit button
            with gr.Row():
                submit_btn = gr.Button(" Submit for Correction", variant="primary", size="lg")
            
            submit_status = gr.Textbox(
                label="Submission Status",
                interactive=False,
                lines=2
            )
            
            # Submission handler
            def submit_answers(canvas_input, upload_input, typed_input):
                if not session.current_questions:
                    return " Generate questions first in Step 1!"
                
                # Check which method was used
                if canvas_input is not None:
                    # Convert canvas to text representation
                    session.current_answers = {0: "[Canvas drawing - sent to AI for analysis]"}
                    return f" Canvas submission received with {len(session.current_questions)} questions. Processing..."
                elif upload_input is not None:
                    session.current_answers = {0: "[Uploaded image - sent to AI for analysis]"}
                    return f" Photo submission received with {len(session.current_questions)} questions. Processing..."
                elif typed_input and typed_input.strip():
                    # Parse typed answers
                    session.current_answers = {}
                    lines = typed_input.split('\n')
                    for line in lines:
                        if line.strip().startswith('Q') and '.' in line:
                            try:
                                parts = line.split('.', 1)
                                q_num = int(parts[0].strip('Q').strip()) - 1
                                answer_text = parts[1].strip() if len(parts) > 1 else ""
                                session.current_answers[q_num] = answer_text
                            except:
                                pass
                    
                    if session.current_answers:
                        return f"✅ Received {len(session.current_answers)} typed answers. Processing for correction..."
                    else:
                        return "⚠️ Could not parse your answers. Use format: Q1. [answer], Q2. [answer], etc."
                else:
                    return "⚠️ Please provide answers using one of the three methods."
            
            submit_btn.click(
                fn=submit_answers,
                inputs=[canvas, upload_image, typed_answers],
                outputs=submit_status
            )
        
        # ===== TAB 3: AI CORRECTION =====
        with gr.Tab("3️⃣ AI Correction"):
            gr.Markdown("### Step 3: Get AI Feedback & Corrections")
            
            correction_btn = gr.Button(" Get AI Correction", variant="primary", size="lg")
            
            feedback_output = gr.Textbox(
                label="AI Feedback & Corrections",
                lines=20,
                elem_classes="feedback-box"
            )
            
            with gr.Row():
                download_feedback_btn = gr.DownloadButton(" Download Feedback (TXT)")
                save_status = gr.Textbox(
                    label="Download Status",
                    interactive=False
                )
            
            # Correction handler
            def get_correction():
                if not session.current_questions:
                    return " Generate questions in Step 1 first!"
                
                if not session.current_answers:
                    return " Submit answers in Step 2 first!"
                
                feedback = grade_student_answers(
                    session.current_questions,
                    session.current_answers,
                    session.current_grade,
                    session.current_topic,
                    getattr(session, 'current_subject', None)
                )
                
                session.last_feedback = feedback
                return feedback
            
            correction_btn.click(
                fn=get_correction,
                inputs=[],
                outputs=feedback_output
            )
            
            # Download feedback handler - returns file path for gr.DownloadButton
            def download_feedback_handler():
                if not session.last_feedback:
                    return None
                try:
                    subject = getattr(session, 'current_subject', None)
                    filepath = download_feedback_file(session.last_feedback, session.current_topic, session.current_grade, subject=subject)
                    return filepath
                except Exception as e:
                    return None
            
            download_feedback_btn.click(
                fn=download_feedback_handler,
                inputs=[],
                outputs=download_feedback_btn
            )
        
        # ===== TAB 4: START NEW SESSION =====
        with gr.Tab(" New Session"):
            gr.Markdown("### Start a Fresh Practice Session")
            gr.Markdown("Click below to clear your current answers and start practicing a new topic.")
            
            new_session_btn = gr.Button(" Clear & Start New", variant="primary", size="lg")
            new_session_status = gr.Textbox(
                label="Status",
                interactive=False
            )
            
            def start_new_session():
                session.clear_session()
                return " Session cleared. Go to 'Step 1' to generate new questions."
            
            new_session_btn.click(
                fn=start_new_session,
                inputs=[],
                outputs=new_session_status
            )

# Launch
if __name__ == "__main__":
    is_hf_spaces = os.getenv("SPACE_ID") is not None
    
    app.launch(
        share=False if is_hf_spaces else True,
        server_name="0.0.0.0",
        show_error=True
    )
