import streamlit as st
import io
import re
from PIL import Image
from google import genai
from streamlit_drawable_canvas import st_canvas

# --- REUSABLE GRADING COMPONENT (UNIVERSAL VISION ENGINE) ---
def render_grading_suite(
    bg_image, 
    height_px, 
    key_prefix="generic_marking", 
    show_experimental_toolbar=False,
    solution_requirement="demonstrated",
    problem_context="",
    show_controls=True,
    camera_mode="App"
):
    """
    Encapsulated logic for problem canvas, markup, Undo/Clear, Photo Snap, and AI Grading.
    Accepts optional toggles for UI elements (show_controls, camera_mode).
    """
    
    # --- Internal Key Encapsulation ---
    k = lambda part: f"_{key_prefix}_{part}"
    CANVAS_KEY = k("canvas_k")
    EXP_TOOLBAR_KEY = k("exp_tk")
    FEEDBACK_KEY = k("feedb")
    CORRECT_STATE_KEY = k("is_corr")
    TOOL_SELECTOR_KEY = k("tool_sel")
    STROKE_HIST_KEY = k("shist")
    INITIAL_DWG_KEY = k("initd")
    CAMERA_STATE_KEY = k("cam_s")

    PEN_COLORS = ["#1E90FF", "#FF2400", "#32CD32", "#9400D3", "#FF8C00"]
    COLOR_NAMES = ["BLUE", "RED", "GREEN", "PURPLE", "ORANGE"]

    if 'current_marking_color_index' not in st.session_state:
        st.session_state.current_marking_color_index = 0
        
    if k("init") not in st.session_state or st.session_state.get(k("init")) == False:
        st.session_state[FEEDBACK_KEY] = ""
        st.session_state[CANVAS_KEY] = 0
        st.session_state[EXP_TOOLBAR_KEY] = 0
        st.session_state[TOOL_SELECTOR_KEY] = "🖌️"
        st.session_state[STROKE_HIST_KEY] = [[]]
        st.session_state[INITIAL_DWG_KEY] = {"version": "4.4.0", "objects": []}
        st.session_state[CORRECT_STATE_KEY] = False
        st.session_state[CAMERA_STATE_KEY] = False
        st.session_state[k("init")] = True

    current_color_index = st.session_state.current_marking_color_index
    current_color_name = COLOR_NAMES[current_color_index]
    
    current_tool = st.session_state.get(TOOL_SELECTOR_KEY, "🖌️") if show_controls else "🖌️"
    active_stroke_color = PEN_COLORS[current_color_index] if current_tool == "🖌️" else "#FFFFFE"
    active_stroke_width = 3 if current_tool == "🖌️" else 15

    st.write(f"Current pen: **{current_color_name}**")
    
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)", stroke_width=active_stroke_width, stroke_color=active_stroke_color,
        background_image=bg_image, update_streamlit=True, height=height_px, width=380,
        drawing_mode="freedraw", return_image_data=True, initial_drawing=st.session_state.get(INITIAL_DWG_KEY, {"version": "4.4.0", "objects": []}),
        key=k(f"canvas_{st.session_state.get(CANVAS_KEY, 0)}")
    )

    # Conditionally render our custom UI button controls
    if show_controls or camera_mode != "None":
        st.markdown("<hr style='margin: 0.5em 0px; border-color: #444;'>", unsafe_allow_html=True)
        t_col1, t_col2, t_col3, t_col4 = st.columns([1.5, 1, 1, 1.2])
        
        if show_controls:
            with t_col1: 
                st.radio("Tool", ["🖌️", "🧽"], horizontal=True, label_visibility="collapsed", key=TOOL_SELECTOR_KEY)
            with t_col2:
                if st.button("↩️", use_container_width=True, help="Undo", key=k("btn_undo")):
                    hist = st.session_state.get(STROKE_HIST_KEY, [[]])
                    if len(hist) > 1:
                        hist.pop()
                        st.session_state[INITIAL_DWG_KEY] = {"version": "4.4.0", "objects": hist[-1]}
                        st.session_state[CANVAS_KEY] = st.session_state.get(CANVAS_KEY, 0) + 1
                        st.rerun()
            with t_col3:
                if st.button("🗑️", use_container_width=True, help="Clear Workings", key=k("btn_clear")):
                    st.session_state[STROKE_HIST_KEY] = [[]]
                    st.session_state[INITIAL_DWG_KEY] = {"version": "4.4.0", "objects": []}
                    st.session_state[CANVAS_KEY] = st.session_state.get(CANVAS_KEY, 0) + 1
                    st.rerun()
                    
        if camera_mode != "None":
            with t_col4:
                if st.button("📸 Paper", use_container_width=True, help="Snap photo of paper workings", key=k("btn_photo")):
                    st.session_state[CAMERA_STATE_KEY] = not st.session_state.get(CAMERA_STATE_KEY, False)
                    st.rerun()
            
    current_objects = canvas_result.json_data.get("objects", []) if canvas_result.json_data else []
    stroke_hist = st.session_state.get(STROKE_HIST_KEY, [[]])
    if len(current_objects) > 0 and len(stroke_hist) > 0:
        if len(current_objects) > len(stroke_hist[-1]):
            if current_objects[-1].get("stroke", "").upper() == "#FFFFFE":
                e = current_objects[-1]
                E_L, E_R, E_T, E_B = e.get("left",0)-15, e.get("left",0)+(e.get("width",0)*e.get("scaleX",1))+15, e.get("top",0)-15, e.get("top",0)+(e.get("height",0)*e.get("scaleY",1))+15
                objects_to_keep = [obj for obj in stroke_hist[-1] if not (E_R < obj.get("left",0) or E_L > obj.get("left",0)+(obj.get("width",0)*obj.get("scaleX",1)) or E_B < obj.get("top",0) or E_T > obj.get("top",0)+(obj.get("height",0)*obj.get("scaleX",1)))]
                stroke_hist.append(objects_to_keep)
                st.session_state[INITIAL_DWG_KEY] = {"version": "4.4.0", "objects": objects_to_keep}
                st.session_state[CANVAS_KEY] = st.session_state.get(CANVAS_KEY, 0) + 1
                st.rerun()
            else:
                stroke_hist.append(current_objects.copy())

    camera_picture = None
    if camera_mode != "None" and st.session_state.get(CAMERA_STATE_KEY, False):
        if camera_mode == 'App':
            camera_picture = st.camera_input("Snap a photo:", key=k("cam_input")) 
        else:
            camera_picture = st.file_uploader("Upload photo:", type=['png', 'jpg'], key=k("cam_input"))

    color_sequence_str = ", ".join(COLOR_NAMES)
    
    if solution_requirement == "numeric":
        requirement_rule = (
            "- REQUIREMENT (NUMERIC STRICT): The student MUST fully calculate out the final decimal number. "
            "If they stop at an unevaluated expression or radical, you MUST mark it INCORRECT."
        )
    else:
        requirement_rule = (
            "- REQUIREMENT (DEMONSTRATED): Demonstrating the correct mathematical setup is sufficient, but the student MUST isolate the target variable as the subject of the equation."
        )
    
    context_section = f"\nGROUND TRUTH PROBLEM CONTEXT:\n{problem_context}\n" if problem_context else ""
    
    marking_prompt = f"""
    You are an expert, encouraging math tutor grading a student's handwritten work.
    The problem to be solved is rendered on the provided canvas/image.
    {context_section}
    The student is using a sequence of handwritten pen colors to show their progress over time. 
    The full sequence of colors they cycle through is: {color_sequence_str}.
    They are currently writing in: {current_color_name}.
    
    {requirement_rule}

    IMPORTANT GRADING RULES FOR DIGITAL INK CORRECTIONS:
    1. The student is writing on a digital canvas and may not use an eraser. Their LATEST, definitive attempt is written in the active {current_color_name} ink. Treat all other colors as older mistakes or superseded workings.
    2. Sign Overwriting: If a student sketches a vertical line or a plus sign over an existing minus sign, evaluate it as a positive sign. If they sketch a horizontal line over an existing plus sign, evaluate it as a minus sign. Always trust the {current_color_name} ink modifier.
    3. Overlapping Strikethroughs: Students will often leave old strikethrough lines on incorrectly eliminated terms. Ignore superseded strikethroughs from older colors. Only evaluate the eliminations and the final answer written in the active {current_color_name} ink.
    
    CRITICAL VISUAL GRADING RULE:
    - If the student solves the problem correctly using the chronology of their workings and fulfills the stated requirement above, reply EXACTLY with "CORRECT:" on the first line, followed by a brief congratulatory message.
    - If their solution or step-by-step working is incorrect or misses the required format, reply EXACTLY with "INCORRECT:" on the first line, followed by a brief hint on what to do next. Do NOT give them the final answer.
    """

    st.markdown("<hr style='margin: 0.5em 0px; border-color: #444;'>", unsafe_allow_html=True)
    if st.button("Check My Answer!", type="primary", use_container_width=True, key=k("check_btn")):
        payload_images = []
        if canvas_result.image_data is not None and len(stroke_hist[-1]) > 0:
            ink = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').resize(bg_image.size, Image.Resampling.LANCZOS)
            payload_images.append(Image.alpha_composite(bg_image.convert("RGBA"), ink).convert("RGB"))
        if camera_picture: payload_images.append(Image.open(camera_picture).convert('RGB').resize((1024, 1024)))
            
        if not payload_images: 
            st.error("Please draw your workings on the canvas or snap a photo first!")
        else:
            with st.spinner("Reviewing your workings..."):
                try:
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[marking_prompt] + payload_images
                    )
                    
                    response_text = response.text.strip()
                    if response_text.upper().startswith("CORRECT"):
                        st.session_state[CORRECT_STATE_KEY] = True
                        cleaned = re.sub(r'(?i)^CORRECT:?\s*', '', response_text).strip()
                        st.session_state[FEEDBACK_KEY] = cleaned if cleaned else "Perfect! You solved it correctly."
                    else:
                        st.session_state[CORRECT_STATE_KEY] = False
                        cleaned = re.sub(r'(?i)^INCORRECT:?\s*', '', response_text).strip()
                        st.session_state[FEEDBACK_KEY] = cleaned if cleaned else "Something doesn't look quite right. Give it another try!"
                        st.session_state.current_marking_color_index = (st.session_state.current_marking_color_index + 1) % len(PEN_COLORS)
                        
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

    feedback_msg = st.session_state.get(FEEDBACK_KEY, "")
    if feedback_msg:
        if st.session_state.get(CORRECT_STATE_KEY, False):
            st.success(f"🌟 **Awesome job!** {feedback_msg}")
        else:
            st.warning(f"🤖 **Tutor says:** {feedback_msg}")