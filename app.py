import groq
import gradio as gr
import PyPDF2
import json
import os
from fpdf import FPDF
import tempfile

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = groq.Groq(api_key=GROQ_API_KEY)

def extract_text(file):
    if file is None:
        return ""
    file_path = file.name if hasattr(file, "name") else file
    if file_path.endswith(".pdf"):
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text.strip()
    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "ResuMatch - AI Resume Analysis Report", ln=True, align="C")
    pdf.ln(4)

    pdf.set_draw_color(100, 100, 255)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(50, 50, 200)
    score_line = "Overall Match Score: " + str(data["overall_score"]) + " / 100  |  Grade: " + data["grade"] + " - " + data["grade_label"]
    pdf.cell(0, 10, score_line, ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    summary = data["summary"].encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 7, "Summary: " + summary)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Score Breakdown", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    for key, val in data["score_breakdown"].items():
        label = key.replace("_", " ").title()
        pdf.cell(0, 8, "  " + label + ": " + str(val) + " / 100", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Matched Skills", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    matched = ", ".join(data.get("matched_skills", [])) or "None found"
    pdf.multi_cell(0, 7, "  " + matched)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Missing Skills", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    missing = ", ".join(data.get("missing_skills", [])) or "None - great job!"
    pdf.multi_cell(0, 7, "  " + missing)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Improvement Suggestions", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for s in data.get("suggestions", []):
        pdf.set_text_color(60, 60, 60)
        text = s["text"].encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 7, "  [" + s["priority"] + "] " + text)
        pdf.ln(1)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "ATS Compatibility Check", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for check in data.get("ats_checks", []):
        status = check["status"]
        if status == "Pass":
            pdf.set_text_color(0, 150, 0)
        elif status == "Warn":
            pdf.set_text_color(200, 130, 0)
        else:
            pdf.set_text_color(200, 0, 0)
        note = check["note"].encode("latin-1", "replace").decode("latin-1")
        pdf.cell(0, 8, "  " + check["label"] + ": " + status + " - " + note, ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Your Strengths", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    strengths = data.get("strengths", "").encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 7, "  " + strengths)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Role Fit Analysis", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    narrative = data.get("role_fit_narrative", "").encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 7, "  " + narrative)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp.name)
    return tmp.name

def analyse_resume(resume_file, resume_text_input, jd_text):

    resume_text = ""
    if resume_file is not None:
        resume_text = extract_text(resume_file)
    if not resume_text and resume_text_input:
        resume_text = resume_text_input.strip()

    if not resume_text:
        return "Please upload a resume or paste your resume text.", "", "", "", "", None
    if not jd_text or not jd_text.strip():
        return "Please paste a job description.", "", "", "", "", None

    system_prompt = """You are an expert ATS analyst and career coach.
Analyse the resume against the job description.
Return ONLY valid JSON with no explanation, no markdown, no backticks.

JSON structure:
{
  "overall_score": <integer 0-100>,
  "grade": "<A+|A|B+|B|C+|C|D|F>",
  "grade_label": "<Excellent Match|Strong Match|Good Match|Fair Match|Weak Match|Poor Match>",
  "score_breakdown": {
    "skills_match": <integer 0-100>,
    "experience_match": <integer 0-100>,
    "education_match": <integer 0-100>,
    "keyword_density": <integer 0-100>
  },
  "summary": "<2-3 sentence overall assessment>",
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "suggestions": [
    {"priority": "High", "text": "<actionable suggestion>"},
    {"priority": "High", "text": "<actionable suggestion>"},
    {"priority": "Medium", "text": "<actionable suggestion>"},
    {"priority": "Medium", "text": "<actionable suggestion>"},
    {"priority": "Low", "text": "<actionable suggestion>"}
  ],
  "ats_checks": [
    {"label": "Keywords Optimisation", "status": "<Pass|Warn|Fail>", "note": "<brief note>"},
    {"label": "Quantified Achievements", "status": "<Pass|Warn|Fail>", "note": "<brief note>"},
    {"label": "Action Verbs", "status": "<Pass|Warn|Fail>", "note": "<brief note>"},
    {"label": "Work Experience Gaps", "status": "<Pass|Warn|Fail>", "note": "<brief note>"},
    {"label": "Education Match", "status": "<Pass|Warn|Fail>", "note": "<brief note>"}
  ],
  "strengths": "<paragraph about what the resume does well>",
  "role_fit_narrative": "<paragraph explaining overall fit and key gaps>"
}"""

    user_message = "RESUME:\n" + resume_text[:4000] + "\n\n---\n\nJOB DESCRIPTION:\n" + jd_text[:3000]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=1500
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        if data["overall_score"] >= 75:
            score_color = "Good Match"
        elif data["overall_score"] >= 50:
            score_color = "Fair Match"
        else:
            score_color = "Weak Match"

        score_output = "## Score: " + str(data["overall_score"]) + " / 100 - " + data["grade"] + " (" + data["grade_label"] + ")\n\n"
        score_output += "**Summary:** " + data["summary"] + "\n\n"
        score_output += "### Score Breakdown\n"
        score_output += "| Category | Score |\n|---|---|\n"
        score_output += "| Skills Match | " + str(data["score_breakdown"]["skills_match"]) + " / 100 |\n"
        score_output += "| Experience Match | " + str(data["score_breakdown"]["experience_match"]) + " / 100 |\n"
        score_output += "| Education Match | " + str(data["score_breakdown"]["education_match"]) + " / 100 |\n"
        score_output += "| Keyword Density | " + str(data["score_breakdown"]["keyword_density"]) + " / 100 |\n"

        matched = ", ".join(data.get("matched_skills", [])) or "None found"
        missing = ", ".join(data.get("missing_skills", [])) or "None - great job!"
        skills_output = "## Matched Skills\n" + matched + "\n\n## Missing Skills\n" + missing

        suggestions_output = "## Improvement Suggestions\n\n"
        for s in data.get("suggestions", []):
            suggestions_output += "**[" + s["priority"] + "]** " + s["text"] + "\n\n"

        ats_output = "## ATS Compatibility Check\n\n"
        ats_output += "| Check | Status | Note |\n|---|---|---|\n"
        for check in data.get("ats_checks", []):
            ats_output += "| " + check["label"] + " | " + check["status"] + " | " + check["note"] + " |\n"

        narrative_output = "## Your Strengths\n" + data.get("strengths", "-") + "\n\n"
        narrative_output += "## Role Fit Analysis\n" + data.get("role_fit_narrative", "-")

        pdf_path = generate_pdf(data)

        return score_output, skills_output, suggestions_output, ats_output, narrative_output, pdf_path

    except json.JSONDecodeError:
        return "AI returned unexpected response. Please try again.", "", "", "", "", None
    except Exception as e:
        return "Error: " + str(e), "", "", "", "", None


with gr.Blocks(title="ResuMatch - AI Resume Analyser", theme=gr.themes.Soft()) as app:

    gr.Markdown("# ResuMatch - AI Resume Analyser and Job Match Platform")
    gr.Markdown("Upload your resume and paste a job description to get an AI-powered match score and improvement tips")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Your Resume")
            resume_file = gr.File(
                label="Upload Resume (PDF or TXT)",
                file_types=[".pdf", ".txt"]
            )
            resume_text = gr.Textbox(
                label="Or paste resume text here",
                placeholder="Paste your full resume...",
                lines=12
            )
        with gr.Column(scale=1):
            gr.Markdown("### Job Description")
            jd_text = gr.Textbox(
                label="Paste Job Description",
                placeholder="Paste the full job description here...",
                lines=16
            )

    analyse_btn = gr.Button("Analyse with AI", variant="primary", size="lg")

    gr.Markdown("---")
    gr.Markdown("## Analysis Results")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Match Score")
            score_out = gr.Markdown()
        with gr.Column(scale=1):
            gr.Markdown("### Skills Analysis")
            skills_out = gr.Markdown()

    gr.Markdown("---")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Improvement Suggestions")
            suggestions_out = gr.Markdown()
        with gr.Column(scale=1):
            gr.Markdown("### ATS Check")
            ats_out = gr.Markdown()

    gr.Markdown("---")
    gr.Markdown("### Strengths and Role Fit")
    narrative_out = gr.Markdown()

    gr.Markdown("---")
    gr.Markdown("### Download Your Report")
    pdf_out = gr.File(label="Download PDF Report")

    analyse_btn.click(
        fn=analyse_resume,
        inputs=[resume_file, resume_text, jd_text],
        outputs=[score_out, skills_out, suggestions_out, ats_out, narrative_out, pdf_out]
    )

app.launch()