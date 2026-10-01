import streamlit as st
import random
import io
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- Force Matplotlib to use classic LaTeX styling ---
plt.rcParams['mathtext.fontset'] = 'cm'
plt.rcParams['font.family'] = 'serif'

from PIL import Image
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

    else: # Advanced (Negative & Fractional Indices)
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
def draw_calculus_image(problem_data, mode="Solve"):
    width_px = 380
    height_px = 450 if mode == "Solve" else 180
    
    fig, ax = plt.subplots(figsize=(width_px/100, height_px/100), dpi=100)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    # Move text higher up to close the gap
    text_y = 0.95 if mode == "Solve" else 0.90
    ax.text(0.05, text_y, problem_data['instruction'], fontsize=11, fontweight='normal', fontfamily='sans-serif', va='top', ha='left')
    
    is_tall = "\\int" in problem_data['q_latex'] or "\\frac" in problem_data['q_latex']
    fs = 20 if is_tall else 18
    
    # Tightly stack the equation just below the text
    if mode == "Solve":
        eq_y = 0.85 if is_tall else 0.88
    else:
        eq_y = 0.55 if is_tall else 0.65
        
    ax.text(0.05, eq_y, f"${problem_data['q_latex']}$", fontsize=fs, va='top', ha='left', color='black')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor='white', transparent=False)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert('RGBA').copy()

# --- State Management ---
if 'generating' not in st.session_state: st.session_state.generating = True
if 'calc_topic' not in st.session_state: st.session_state.calc_topic = "Mixed"
if 'calc_level' not in st.session_state: st.session_state.calc_level = "Basic Polynomials"
if 'interaction_mode' not in st.session_state: st.session_state.interaction_mode = "Solve"
if 'problem_suite_refresh_id' not in st.session_state: st.session_state.problem_suite_refresh_id = 0
if 'id_feedback' not in st.session_state: st.session_state.id_feedback = ""

def handle_settings_change():
    st.session_state.generating = True
    st.session_state.id_feedback = ""
    st.session_state.problem_suite_refresh_id += 1 

# --- UI Setup ---
st.title("NCEA 2 - CALCULUS (Core Mechanics) 📈")

col_empty, col_set = st.columns([5, 1])
with col_set:
    with st.popover("⚙️", use_container_width=True):
        st.write("**Settings**")
        st.selectbox("Focus Area", ["Mixed", "Differentiate", "Integrate"], key="calc_topic", on_change=handle_settings_change)
        st.radio("Difficulty", ["Basic Polynomials", "Negative & Fractional Indices"], key="calc_level", on_change=handle_settings_change)
        st.radio("Interaction Mode", ["Recognition", "Solve"], key="interaction_mode", on_change=handle_settings_change)
        st.toggle("Canvas Controls", key="show_controls", value=True, on_change=handle_settings_change)

# --- Master App Logic ---
if st.session_state.generating:
    with st.spinner("Generating calculus problem..."):
        p_data = generate_calculus_problem(st.session_state.calc_topic, st.session_state.calc_level)
        st.session_state.calc_problem_data = p_data
        st.session_state.problem_image_context = draw_calculus_image(p_data, st.session_state.interaction_mode)
        st.session_state.generating = False
        st.rerun()

else:
    bg_image = st.session_state.problem_image_context
    p_data = st.session_state.calc_problem_data
    
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
            camera_mode="None" 
        )

    st.markdown("<hr style='margin: 0.5em 0px; border-color: #444;'>", unsafe_allow_html=True)
    st.markdown('<div id="next-problem-btn"></div>', unsafe_allow_html=True)
    if st.button("Give me a new problem!", use_container_width=True):
        handle_settings_change()
        st.rerun()