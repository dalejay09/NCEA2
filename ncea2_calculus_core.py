import streamlit as st
import random
import io
import json
import re
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- THE ULTIMATE MONKEY PATCH (For native canvas rendering) ---
import streamlit_drawable_canvas
def b64_image_to_url(image, *args, **kwargs):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

streamlit_drawable_canvas.image_to_url = b64_image_to_url
from streamlit_drawable_canvas import st_canvas

# --- Force Matplotlib to use classic LaTeX styling ---
plt.rcParams['mathtext.fontset'] = 'cm'
plt.rcParams['font.family'] = 'serif'

from PIL import Image
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages
from pydantic import BaseModel, Field
from google import genai
import ai_marking_component

st.set_page_config(page_title="NCEA 2 - CALCULUS (Core Mechanics)", page_icon="📈", layout="centered")

st.markdown("""
    <style>
    button[kind="primary"] { background-color: #007AFF !important; border-color: #007AFF !important; color: white !important; }
    button[kind="primary"]:hover { background-color: #0056b3 !important; border-color: #0056b3 !important; }
    div[data-testid="stElementContainer"]:has(#next-problem-btn) + div[data-testid="stElementContainer"] button {
        background-color: #28a745 !important; border-color: #28a745 !important; color: white !important;
    }
    div[data-testid="stElementContainer"]:has(#next-problem-btn) + div[data-testid="stElementContainer"] button:hover {
        background-color: #218838 !important; border-color: #218838 !important;
    }
    .stRadio > div { gap: 0rem; }
    [data-testid="stHorizontalBlock"] { gap: 0.5rem; align-items: center; }
    div[data-testid="stToolbar"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- AI Output Schemas for PDF ---
class SolutionRow(BaseModel):
    q_num: int = Field(description="The question number (1 to 20)")
    steps: str = Field(description="Step-by-step solving method using valid LaTeX formatting")

class AIWorksheetSolutions(BaseModel):
    solutions: list[SolutionRow]

# --- Math Engine: LEVEL 2 CALCULUS GENERATOR ---
def format_frac(num, den):
    """Simplifies clean divisions to integers, otherwise returns a LaTeX fraction."""
    if num % den == 0:
        return str(num // den)
    return f"\\frac{{{num}}}{{{den}}}"

def generate_calculus_problem(topic="Mixed", level="Basic Polynomials"):
    if topic == "Mixed":
        operation = random.choice(["Differentiate", "Integrate"])
    else:
        operation = topic

    var = 'x'
    q_latex = ""
    a_latex = ""
    dist1 = ""
    dist2 = ""
    
    if level == "Basic Polynomials":
        a = random.randint(2, 6) * 3
        b = random.randint(2, 6) * 2
        c = random.randint(2, 9)
        
        if operation == "Differentiate":
            instruction = "Find the gradient function, $f'(x)$, for:"
            q_latex = f"f(x) = {a}{var}^3 - {b}{var}^2 + {c}{var}"
            a_latex = f"f'(x) = {3*a}{var}^2 - {2*b}{var} + {c}"
            dist1 = f"f'(x) = {3*a}{var}^4 - {2*b}{var}^3 + {c}{var}^2" 
            dist2 = f"f'(x) = {a}{var}^2 - {b}{var} + {c}" 
        else:
            instruction = "Find the indefinite integral:"
            q_latex = f"\\int ({a}{var}^2 - {b}{var} + {c}) \\, d{var}"
            a_latex = f"{a//3}{var}^3 - {b//2}{var}^2 + {c}{var} + c"
            dist1 = f"{a//3}{var}^3 - {b//2}{var}^2 + {c}{var}" 
            dist2 = f"{2*a}{var} - {b} + c" 

    else: 
        variant = random.choice(["negative", "fractional"])
        
        if variant == "negative":
            a = random.randint(2, 6) * 2 
            b = random.randint(2, 8)
            
            if operation == "Differentiate":
                instruction = "Differentiate with respect to $x$:"
                q_latex = f"y = \\frac{{{a}}}{{{var}^3}} + {b}{var}"
                a_latex = f"\\frac{{dy}}{{dx}} = -\\frac{{{3*a}}}{{{var}^4}} + {b}"
                dist1 = f"\\frac{{dy}}{{dx}} = \\frac{{{3*a}}}{{{var}^2}} + {b}" 
                dist2 = f"\\frac{{dy}}{{dx}} = -\\frac{{{a}}}{{{var}^4}} + {b}" 
            else:
                instruction = "Find the indefinite integral:"
                q_latex = f"\\int \\left( \\frac{{{a}}}{{{var}^3}} + {b} \\right) \\, d{var}"
                a_latex = f"-\\frac{{{a//2}}}{{{var}^2}} + {b}{var} + c"
                dist1 = f"-\\frac{{{a//2}}}{{{var}^2}} + {b}{var}" 
                dist2 = f"-\\frac{{{3*a}}}{{{var}^4}} + {b}x + c" 

        elif variant == "fractional":
            a = random.randint(2, 5) * 2
            
            if operation == "Differentiate":
                instruction = "Find $f'(x)$ for:"
                q_latex = f"f(x) = {a}\\sqrt{{{var}}} - 3{var}^2"
                a_latex = f"f'(x) = \\frac{{{a//2}}}{{\\sqrt{{{var}}}}} - 6{var}"
                dist1 = f"f'(x) = {a//2}\\sqrt{{{var}}} - 6{var}" 
                dist2 = f"f'(x) = \\frac{{{a}}}{{\\sqrt{{{var}}}}} - 6{var}" 
            else:
                instruction = "Integrate with respect to $x$:"
                q_latex = f"\\int {a}\\sqrt{{{var}}} \\, d{var}"
                a_latex = f"{format_frac(a * 2, 3)}{var}^{{3/2}} + c"
                dist1 = f"{format_frac(a * 2, 3)}{var}^{{3/2}}" 
                dist2 = f"\\frac{{{a//2}}}{{\\sqrt{{{var}}}}} + c" 

    a_latex = a_latex.replace("1x", "x").replace("+ -", "- ").replace(".0", "")
    
    return {
        "operation": operation,
        "instruction": instruction,
        "q_latex": q_latex,
        "a_latex": a_latex,
        "dist1": dist1,
        "dist2": dist2,
        "variable": var
    }

# --- Visual Engine: CANVAS RENDERER ---
def draw_calculus_image(problem_data, mode="Solve", level="Basic Polynomials"):
    width_px = 380
    
    if mode == "Solve":
        height_px = 450
    elif level == "Negative & Fractional Indices":
        height_px = 350
    else:
        height_px = 180
        
    fig, ax = plt.subplots(figsize=(width_px/100, height_px/100), dpi=100)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    is_tall = "\\int" in problem_data['q_latex'] or "\\frac" in problem_data['q_latex']
    fs = 20 if is_tall else 18
    
    if mode == "Solve" or level == "Negative & Fractional Indices":
        text_y = 0.95
        eq_y = 0.85 if is_tall else 0.88
    else:
        text_y = 0.90
        eq_y = 0.55 if is_tall else 0.65
        
    ax.text(0.05, text_y, problem_data['instruction'], fontsize=11, fontweight='normal', fontfamily='sans-serif', va='top', ha='left')
    ax.text(0.05, eq_y, f"${problem_data['q_latex']}$", fontsize=fs, va='top', ha='left', color='black')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor='white', transparent=False)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert('RGBA').copy()

# --- Worksheet PDF Generator ---
def create_pdf_bytes(topic, level):
    buffer = io.BytesIO()
    try:
        with PdfPages(buffer) as pdf:
            problems = [generate_calculus_problem(topic, level) for _ in range(20)]
            ai_steps = {}
            try:
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                payload = "".join([f"Q{i+1}: {p['instruction']} {p['q_latex']} | Final Ans: {p['a_latex']}\n" for i, p in enumerate(problems)])
                prompt = (
                    "Write concise step-by-step calculus solutions using valid LaTeX math expressions enclosed in single dollar signs. "
                    "Use \\n to separate steps so they break into new lines cleanly. "
                    "Data:\n" + payload
                )
                response = client.models.generate_content(
                    model='gemini-3.6-flash', contents=[prompt],
                    config=dict(response_mime_type="application/json", response_schema=AIWorksheetSolutions, temperature=0.1)
                )
                for item in json.loads(response.text).get("solutions", []):
                    cleaned_step = item["steps"].replace("**", "").replace(r"\n", "\n")
                    ai_steps[item["q_num"]] = cleaned_step
            except Exception:
                pass
            
            fig_ws, axes = plt.subplots(5, 4, figsize=(8.27, 11.69))
            fig_ws.subplots_adjust(left=0.03, right=0.97, top=0.92, bottom=0.03, wspace=0.15, hspace=0.25)
            fig_ws.suptitle("NCEA Level 2 Calculus Practice Worksheet", fontsize=16, fontweight='bold', ha='center')
            
            for idx, p_data in enumerate(problems):
                row, col = divmod(idx, 4)
                ax = axes[row, col]
                ax.axis('off')
                ax.text(0.05, 0.95, f"Q{idx+1}: {p_data['instruction']}", fontsize=7.5, fontweight='bold', va='top')
                ax.text(0.05, 0.70, f"${p_data['q_latex']}$", fontsize=12, va='top')
                
            pdf.savefig(fig_ws); plt.close(fig_ws)

            fig_ans, ax_ans = plt.subplots(figsize=(8.27, 11.69))
            ax_ans.axis('off')
            ax_ans.text(0.5, 0.96, "Answer Key & Steps", fontsize=16, fontweight='bold', ha='center')
            for i in range(10):
                left_idx, right_idx = i, i + 10
                txt_l = f"Q{left_idx+1}: ${problems[left_idx]['a_latex']}$\n{ai_steps.get(left_idx+1, '')}"
                txt_r = f"Q{right_idx+1}: ${problems[right_idx]['a_latex']}$\n{ai_steps.get(right_idx+1, '')}"
                y_pos = 0.90 - (i * 0.088)
                ax_ans.text(0.04, y_pos, txt_l, fontsize=7.0, va='top', wrap=True)
                ax_ans.text(0.52, y_pos, txt_r, fontsize=7.0, va='top', wrap=True)
            pdf.savefig(fig_ans); plt.close(fig_ans)
    except Exception as e:
        st.error(f"PDF Generation Error: {e}")
        raise e

    buffer.seek(0)
    return buffer.getvalue()

# --- State Management ---
if 'generating' not in st.session_state: st.session_state.generating = True
if 'calc_topic' not in st.session_state: st.session_state.calc_topic = "Mixed"
if 'calc_level' not in st.session_state: st.session_state.calc_level = "Basic Polynomials"
if 'interaction_mode' not in st.session_state: st.session_state.interaction_mode = "Solve"
if 'camera_mode' not in st.session_state: st.session_state.camera_mode = "None"
if 'problem_suite_refresh_id' not in st.session_state: st.session_state.problem_suite_refresh_id = 0
if 'id_feedback' not in st.session_state: st.session_state.id_feedback = ""
if 'current_marking_color_index' not in st.session_state: st.session_state.current_marking_color_index = 0
if 'pdf_bytes' not in st.session_state: st.session_state.pdf_bytes = None

def handle_settings_change():
    st.session_state.generating = True
    st.session_state.id_feedback = ""
    st.session_state.current_marking_color_index = 0 
    st.session_state.pdf_bytes = None
    st.session_state.problem_suite_refresh_id += 1 

# --- UI Setup ---
st.title("NCEA 2 - CALCULUS (Core Mechanics) 📈")

col_actions, col_set = st.columns([5, 1])
with col_actions:
    with st.popover("📄 Worksheet Actions", use_container_width=True):
        st.markdown("**1. Create a physical worksheet**")
        if st.session_state.pdf_bytes is None:
            if st.button("⚙️ Generate Worksheet PDF", use_container_width=True):
                with st.spinner("Compiling Master PDF Grid..."):
                    try:
                        st.session_state.pdf_bytes = create_pdf_bytes(st.session_state.calc_topic, st.session_state.calc_level)
                    except Exception:
                        st.session_state.pdf_bytes = None
                st.rerun()
        else:
            timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
            st.download_button("⬇ Download Worksheet", data=st.session_state.pdf_bytes, file_name=f"Calc_Core_Mechanics_{timestamp_str}.pdf", mime="application/pdf", use_container_width=True, type="primary")
            if st.button("🗑️ Clear / Reset PDF", use_container_width=True):
                st.session_state.pdf_bytes = None
                st.rerun()
        
        st.markdown("<hr style='margin: 0.5em 0px; border-color: #444;'>", unsafe_allow_html=True)
        marker_url = st.secrets.get("WORKSHEET_MARKER_APP_URL", "#")
        st.markdown(f"**2. Mark physical worksheets**")
        st.markdown(f'<a href="{marker_url}" target="_blank" rel="noopener noreferrer"><button style="width:100%; background-color:#28a745; color:white; border:none; padding:0.5rem; border-radius:4px; font-weight:bold; cursor:pointer;">📸 Mark My Worksheet</button></a>', unsafe_allow_html=True)

with col_set:
    with st.popover("⚙️", use_container_width=True):
        st.write("**Settings**")
        st.selectbox("Focus Area", ["Mixed", "Differentiate", "Integrate"], key="calc_topic", on_change=handle_settings_change)
        st.radio("Difficulty", ["Basic Polynomials", "Negative & Fractional Indices"], key="calc_level", on_change=handle_settings_change)
        st.radio("Interaction Mode", ["Solve", "Recognition"], key="interaction_mode", on_change=handle_settings_change)
        st.radio("Camera Mode", ["None", "App", "Native"], key="camera_mode", horizontal=True, on_change=handle_settings_change)
        st.toggle("Canvas Controls", key="show_controls", value=False, on_change=handle_settings_change)

# --- Master App Logic ---
if st.session_state.generating:
    with st.spinner("Generating calculus problem..."):
        p_data = generate_calculus_problem(st.session_state.calc_topic, st.session_state.calc_level)
        st.session_state.calc_problem_data = p_data
        st.session_state.problem_image_context = draw_calculus_image(p_data, st.session_state.interaction_mode, st.session_state.calc_level)
        st.session_state.generating = False
        st.rerun()

else:
    bg_image = st.session_state.problem_image_context
    p_data = st.session_state.calc_problem_data
    
    if st.session_state.interaction_mode == "Recognition":
        if st.session_state.calc_level == "Negative & Fractional Indices":
            st.markdown("Scratchpad:")
            st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)", stroke_width=3, stroke_color="#1E90FF",
                background_image=bg_image, update_streamlit=True, height=350, width=380,
                drawing_mode="freedraw", key=f"scratchpad_{st.session_state.problem_suite_refresh_id}"
            )
        else:
            st.image(bg_image, use_container_width=True)
        
        if 'id_eq_options' not in st.session_state or st.session_state.get('last_refresh_id') != st.session_state.problem_suite_refresh_id:
            options = [f"${p_data['a_latex']}$", f"${p_data['dist1']}$", f"${p_data['dist2']}$"]
            random.shuffle(options)
            st.session_state.id_eq_options = options
            st.session_state.last_refresh_id = st.session_state.problem_suite_refresh_id

        st.write("Which of the following is the correct mathematical conclusion?")
        for idx, opt in enumerate(st.session_state.id_eq_options):
            if st.button(opt, use_container_width=True, key=f"eq_btn_{idx}"):
                if opt == f"${p_data['a_latex']}$":
                    st.session_state.id_feedback = "Correct! Spot on calculus mechanics."
                else:
                    if "c" not in opt and p_data['operation'] == "Integrate":
                        st.session_state.id_feedback = "Not quite! Did you forget the constant of integration (+ c)?"
                    elif "c" in opt and p_data['operation'] == "Differentiate":
                        st.session_state.id_feedback = "Careful! You integrated instead of differentiating."
                    else:
                        st.session_state.id_feedback = "Not quite. Check your exponent rules and coefficients!"
        
        f_msg = st.session_state.get('id_feedback', '')
        if f_msg:
            if "Correct" in f_msg: st.success(f"🌟 {f_msg}")
            else: st.warning(f"🤖 {f_msg}")
            
    else:
        calc_rules = (
            f"This is an NCEA Level 2 Calculus problem. Instruction: {p_data['instruction']}. "
            f"Question expression: {p_data['q_latex']}. "
            f"The exact correct final algebraic answer is: {p_data['a_latex']}. "
            "CRITICAL CALCULUS GRADING RULES:\n"
            "1. If the problem asks to integrate, the student MUST include the constant of integration (usually '+ c' or '+ C'). If it is missing, you MUST mark it INCORRECT and remind them to add it.\n"
            "2. Students should ideally show the step of rewriting negative or fractional indices (e.g., rewriting 3/x^2 as 3x^-2) before differentiating or integrating. If they skip this but get the correct answer, that is acceptable.\n"
            "3. They may leave their final answer with negative or fractional indices, OR convert it back to fraction/surd form. Both are mathematically valid for full marks."
        )

        ai_marking_component.render_grading_suite(
            bg_image=bg_image,
            height_px=450,
            key_prefix=f"calc_suite_{st.session_state.problem_suite_refresh_id}",
            solution_requirement="demonstrated",
            problem_context=calc_rules,
            show_controls=st.session_state.show_controls,
            camera_mode=st.session_state.camera_mode 
        )

    st.markdown("<hr style='margin: 0.5em 0px; border-color: #444;'>", unsafe_allow_html=True)
    st.markdown('<div id="next-problem-btn"></div>', unsafe_allow_html=True)
    if st.button("Give me a new problem!", use_container_width=True):
        handle_settings_change()
        st.rerun()