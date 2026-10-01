import streamlit as st
import random
import io
import json
import re
import base64
import numpy as np
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

st.set_page_config(page_title="NCEA 2 - CALCULUS (Curve Geometry)", page_icon="📐", layout="centered")

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

def format_alg(expr):
    expr = expr.replace("+ -", "- ").replace("- -", "+ ")
    expr = re.sub(r'\b1x\^2\b', 'x^2', expr)
    expr = re.sub(r'\b-1x\^2\b', '-x^2', expr)
    expr = re.sub(r'\b1x\b', 'x', expr)
    expr = re.sub(r'\b-1x\b', '-x', expr)
    expr = re.sub(r'[+-]\s*0x\b', '', expr)
    expr = re.sub(r'[+-]\s*0\b', '', expr)
    expr = " ".join(expr.split())
    if expr.startswith("+ "): expr = expr[2:]
    return expr.strip()

# --- Math Engine: LEVEL 2 GEOMETRY GENERATOR ---
def generate_geometry_problem(topic="Mixed"):
    topics = ["Gradient at Point", "Turning Point", "Equation of Tangent"]
    if topic == "Mixed":
        topic = random.choice(topics)

    a = random.choice([-2, -1, 1, 2, 3])
    
    if topic == "Turning Point":
        # Ensure integer coordinates for the turning point
        x_tp = random.randint(-3, 3)
        b = -2 * a * x_tp
        c = random.randint(-5, 5)
        y_tp = a * (x_tp**2) + b * x_tp + c
        
        q_latex = format_alg(f"f(x) = {a}x^2 + {b}x + {c}")
        instruction = "Find the coordinates of the turning point for the curve:"
        a_latex = f"({x_tp}, {y_tp})"
        dist1 = f"({-x_tp}, {y_tp})" 
        dist2 = f"({x_tp}, {-y_tp})"
        
        plot_data = {'type': 'tp', 'a': a, 'b': b, 'c': c, 'x': x_tp, 'y': y_tp}

    else:
        b = random.randint(-5, 5)
        c = random.randint(-5, 5)
        x_1 = random.randint(-3, 3)
        y_1 = a * (x_1**2) + b * x_1 + c
        m = 2 * a * x_1 + b
        
        q_latex = format_alg(f"f(x) = {a}x^2 + {b}x + {c}")
        
        if topic == "Gradient at Point":
            instruction = f"Find the gradient of the curve at the point where $x = {x_1}$ for:"
            a_latex = f"m = {m}"
            dist1 = format_alg(f"m = {2*a}x + {b}") 
            dist2 = f"m = {-m}" 
            plot_data = {'type': 'grad', 'a': a, 'b': b, 'c': c, 'x': x_1, 'y': y_1, 'm': m}
            
        elif topic == "Equation of Tangent":
            instruction = f"Find the equation of the tangent to the curve at $x = {x_1}$ for:"
            y_int = y_1 - m * x_1
            a_latex = format_alg(f"y = {m}x + {y_int}")
            
            # Distractor 1: Normal line (if m != 0)
            if m != 0:
                m_norm_str = f"{-1}/{m}" if m > 0 else f"1/{-m}"
                dist1 = format_alg(f"y = {m_norm_str}x + {y_int}")
            else:
                dist1 = format_alg(f"x = {x_1}")
                
            # Distractor 2: Forgot to multiply x_1 by m
            dist2 = format_alg(f"y = {m}x + {y_1}")
            
            plot_data = {'type': 'tangent', 'a': a, 'b': b, 'c': c, 'x': x_1, 'y': y_1, 'm': m, 'y_int': y_int}

    return {
        "topic": topic,
        "instruction": instruction,
        "q_latex": q_latex,
        "a_latex": a_latex,
        "dist1": dist1,
        "dist2": dist2,
        "plot_data": plot_data
    }

# --- Visual Engine: CANVAS RENDERER ---
def draw_geometry_image(problem_data, mode="Solve"):
    width_px = 380
    
    if mode == "Solve":
        height_px = 450
        fig, ax = plt.subplots(figsize=(width_px/100, height_px/100), dpi=100)
        fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        ax.text(0.05, 0.95, problem_data['instruction'], fontsize=11, fontweight='normal', fontfamily='sans-serif', va='top', ha='left', wrap=True)
        ax.text(0.05, 0.82, f"${problem_data['q_latex']}$", fontsize=18, va='top', ha='left', color='black')
        
    else:
        # Recognition Mode: Plot the actual geometry!
        height_px = 350
        fig, ax = plt.subplots(figsize=(width_px/100, height_px/100), dpi=100)
        
        pd = problem_data['plot_data']
        x_val = pd['x']
        
        # Generate x values for the curve
        x = np.linspace(x_val - 4, x_val + 4, 100)
        y = pd['a'] * x**2 + pd['b'] * x + pd['c']
        
        ax.plot(x, y, color='#1E90FF', linewidth=2, label='f(x)')
        ax.scatter([x_val], [pd['y']], color='red', zorder=5)
        
        if pd['type'] == 'tp':
            ax.axhline(pd['y'], color='red', linestyle='--', alpha=0.5)
            ax.set_title("Identify the coordinates of the turning point:", fontsize=11, fontfamily='sans-serif')
        else:
            # Draw tangent line segment
            t_x = np.linspace(x_val - 2, x_val + 2, 10)
            t_y = pd['m'] * (t_x - x_val) + pd['y']
            ax.plot(t_x, t_y, color='red', linestyle='-', linewidth=1.5, label='Tangent')
            
            if pd['type'] == 'grad':
                ax.set_title(f"Identify the gradient (m) at x = {x_val}:", fontsize=11, fontfamily='sans-serif')
            else:
                ax.set_title(f"Identify the equation of the tangent at x = {x_val}:", fontsize=11, fontfamily='sans-serif')
                
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.set_aspect('auto')
        fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor='white', transparent=False)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert('RGBA').copy()

# --- Worksheet PDF Generator ---
def create_pdf_bytes(topic):
    buffer = io.BytesIO()
    try:
        with PdfPages(buffer) as pdf:
            problems = [generate_geometry_problem(topic) for _ in range(20)]
            ai_steps = {}
            try:
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                payload = "".join([f"Q{i+1}: {p['instruction']} {p['q_latex']} | Final Ans: {p['a_latex']}\n" for i, p in enumerate(problems)])
                prompt = (
                    "Write concise step-by-step calculus solutions using valid LaTeX math expressions enclosed in single dollar signs. "
                    "For tangency, show differentiation, substitution, and y-y1=m(x-x1) setup. "
                    "Use \\n to break steps. Data:\n" + payload
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
            fig_ws.suptitle("NCEA Level 2 Calculus: Curve Geometry", fontsize=16, fontweight='bold', ha='center')
            
            for idx, p_data in enumerate(problems):
                row, col = divmod(idx, 4)
                ax = axes[row, col]
                ax.axis('off')
                ax.text(0.05, 0.95, f"Q{idx+1}: {p_data['instruction']}", fontsize=7.0, fontweight='bold', va='top', wrap=True)
                ax.text(0.05, 0.65, f"${p_data['q_latex']}$", fontsize=11, va='top')
                
            pdf.savefig(fig_ws); plt.close(fig_ws)

            fig_ans, ax_ans = plt.subplots(figsize=(8.27, 11.69))
            ax_ans.axis('off')
            ax_ans.text(0.5, 0.96, "Answer Key & Steps", fontsize=16, fontweight='bold', ha='center')
            for i in range(10):
                left_idx, right_idx = i, i + 10
                txt_l = f"Q{left_idx+1}: ${problems[left_idx]['a_latex']}$\n{ai_steps.get(left_idx+1, '')}"
                txt_r = f"Q{right_idx+1}: ${problems[right_idx]['a_latex']}$\n{ai_steps.get(right_idx+1, '')}"
                y_pos = 0.90 - (i * 0.088)
                ax_ans.text(0.04, y_pos, txt_l, fontsize=6.5, va='top', wrap=True)
                ax_ans.text(0.52, y_pos, txt_r, fontsize=6.5, va='top', wrap=True)
            pdf.savefig(fig_ans); plt.close(fig_ans)
    except Exception as e:
        st.error(f"PDF Generation Error: {e}")
        raise e

    buffer.seek(0)
    return buffer.getvalue()

# --- State Management ---
if 'generating' not in st.session_state: st.session_state.generating = True
if 'geom_topic' not in st.session_state: st.session_state.geom_topic = "Mixed"
if 'interaction_mode' not in st.session_state: st.session_state.interaction_mode = "Solve"
if 'camera_mode' not in st.session_state: st.session_state.camera_mode = "None"
if 'problem_suite_refresh_id' not in st.session_state: st.session_state.problem_suite_refresh_id = 0
if 'id_feedback' not in st.session_state: st.session_state.id_feedback = ""
if 'pdf_bytes' not in st.session_state: st.session_state.pdf_bytes = None

def handle_settings_change():
    st.session_state.generating = True
    st.session_state.id_feedback = ""
    st.session_state.pdf_bytes = None
    st.session_state.problem_suite_refresh_id += 1 

# --- UI Setup ---
st.title("NCEA 2 - CALCULUS (Curve Geometry) 📐")

col_actions, col_set = st.columns([5, 1])
with col_actions:
    with st.popover("📄 Worksheet Actions", use_container_width=True):
        st.markdown("**1. Create a physical worksheet**")
        if st.session_state.pdf_bytes is None:
            if st.button("⚙️ Generate Worksheet PDF", use_container_width=True):
                with st.spinner("Compiling Master PDF Grid..."):
                    try:
                        st.session_state.pdf_bytes = create_pdf_bytes(st.session_state.geom_topic)
                    except Exception:
                        st.session_state.pdf_bytes = None
                st.rerun()
        else:
            timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
            st.download_button("⬇ Download Worksheet", data=st.session_state.pdf_bytes, file_name=f"Calc_Geometry_{timestamp_str}.pdf", mime="application/pdf", use_container_width=True, type="primary")
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
        st.selectbox("Focus Area", ["Mixed", "Gradient at Point", "Turning Point", "Equation of Tangent"], key="geom_topic", on_change=handle_settings_change)
        st.radio("Interaction Mode", ["Solve", "Recognition"], key="interaction_mode", on_change=handle_settings_change)
        st.radio("Camera Mode", ["None", "App", "Native"], key="camera_mode", horizontal=True, on_change=handle_settings_change)
        st.toggle("Canvas Controls", key="show_controls", value=False, on_change=handle_settings_change)

# --- Master App Logic ---
if st.session_state.generating:
    with st.spinner("Generating geometric profile..."):
        p_data = generate_geometry_problem(st.session_state.geom_topic)
        st.session_state.geom_problem_data = p_data
        st.session_state.problem_image_context = draw_geometry_image(p_data, st.session_state.interaction_mode)
        st.session_state.generating = False
        st.rerun()

else:
    bg_image = st.session_state.problem_image_context
    p_data = st.session_state.geom_problem_data
    
    if st.session_state.interaction_mode == "Recognition":
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
                    st.session_state.id_feedback = "Correct! Excellent geometric reasoning."
                else:
                    if p_data['topic'] == "Gradient at Point" and "x" in opt:
                        st.session_state.id_feedback = "Careful! That's the gradient function. You need to substitute the x-value to find the numerical gradient."
                    elif p_data['topic'] == "Equation of Tangent" and p_data['dist1'] in opt:
                        st.session_state.id_feedback = "Not quite. Check your gradient 'm'. Did you accidentally find the normal instead of the tangent?"
                    else:
                        st.session_state.id_feedback = "Not quite! Check your substitution and signs."
        
        f_msg = st.session_state.get('id_feedback', '')
        if f_msg:
            if "Correct" in f_msg: st.success(f"🌟 {f_msg}")
            else: st.warning(f"🤖 {f_msg}")
            
    else:
        geom_rules = (
            f"This is an NCEA Level 2 Calculus problem: {p_data['topic']}. Instruction: {p_data['instruction']}. "
            f"Question expression: {p_data['q_latex']}. "
            f"The exact correct final algebraic answer is: {p_data['a_latex']}. "
            "CRITICAL CURVE GEOMETRY GRADING RULES:\n"
            "1. If finding a turning point, the student MUST provide both the x and y coordinates (or solve for both clearly). Finding just x is incomplete.\n"
            "2. If finding the equation of a tangent, they must demonstrate finding the gradient function, substituting the x-value, and calculating the final linear equation (y = mx + c or y - y1 = m(x - x1)).\n"
            "3. If they make a small arithmetic error substituting into the original function but their calculus and geometry method is flawless, gently correct the arithmetic but validate the method."
        )

        ai_marking_component.render_grading_suite(
            bg_image=bg_image,
            height_px=450,
            key_prefix=f"geom_suite_{st.session_state.problem_suite_refresh_id}",
            solution_requirement="demonstrated",
            problem_context=geom_rules,
            show_controls=st.session_state.show_controls,
            camera_mode=st.session_state.camera_mode 
        )

    st.markdown("<hr style='margin: 0.5em 0px; border-color: #444;'>", unsafe_allow_html=True)
    st.markdown('<div id="next-problem-btn"></div>', unsafe_allow_html=True)
    if st.button("Give me a new problem!", use_container_width=True):
        handle_settings_change()
        st.rerun()