import streamlit as st
import re
import json
import matplotlib.pyplot as plt

# Load rules engine
with open("lab_rules_engine_all_labs.json", "r") as f:
    rules_engine = json.load(f)

# Define parser
def parse_lab_values(ehr_text, known_labs):
    parsed_labs = []
    known_labs_lower = {lab.lower(): lab for lab in known_labs}
    lab_pattern = r"([A-Za-z /()\[\]]+)[\s:=\-]+([0-9.]+)(?:\s*[^\d\n]*)?"
    matches = re.findall(lab_pattern, ehr_text)

    for lab_name, value in matches:
        cleaned_name = lab_name.strip().lower()
        matched_key = None
        for known in known_labs_lower:
            if cleaned_name in known or known in cleaned_name:
                matched_key = known_labs_lower[known]
                break
        if matched_key:
            try:
                parsed_labs.append({
                    "lab": matched_key,
                    "value": float(value)
                })
            except ValueError:
                continue
    return parsed_labs

# Define evaluator
def evaluate_lab_value(lab_name, value):
    thresholds = rules_engine.get(lab_name, {}).get("thresholds", [])
    evaluation = "Normal"

    def within_range(val, range_str):
        range_str = range_str.replace(",", "")
        if "–" in range_str:
            low, high = map(float, range_str.split("–"))
            return low <= val <= high
        elif "-" in range_str:
            low, high = map(float, range_str.split("-"))
            return low <= val <= high
        elif "<" in range_str:
            bound = float(re.findall(r"\d+\.?\d*", range_str)[0])
            return val < bound
        elif ">" in range_str:
            bound = float(re.findall(r"\d+\.?\d*", range_str)[0])
            return val > bound
        return False

    for t in thresholds:
        if within_range(value, t["threshold"]):
            evaluation = t["severity"]
            break

    return evaluation

# Map severity to urgency (simplified)
urgency_map = {
    "Critical Low": "Emergent",
    "Critical High": "Emergent",
    "Severe": "Urgent (within 24 hrs)",
    "High": "Routine (1–2 weeks)",
    "Low": "Routine (1–2 weeks)",
    "Moderate": "Prompt (1–3 days)",
    "Mild": "Monitor / Repeat",
    "Normal": "No action required"
}

# Visual bar chart
def plot_lab_bar(lab, value, thresholds):
    severities = ["Critical Low", "Low", "Mild", "Normal", "Moderate", "High", "Severe", "Critical High"]
    x_vals = []
    labels = []
    for t in thresholds:
        match = re.findall(r"\d+\.?\d*", t["threshold"])
        if match:
            x_vals.append(float(match[0]))
            labels.append(t["severity"])
    if not x_vals:
        return
    fig, ax = plt.subplots()
    ax.barh([""], [value], color="blue")
    ax.set_xlim(min(x_vals) - 5, max(x_vals) + 5)
    ax.set_title(f"{lab} = {value}")
    st.pyplot(fig)

# Streamlit UI
st.title("🧪 EHR Lab Parser & Management Assistant")

user_input = st.text_area("Paste EHR lab data below:")

if st.button("Evaluate Labs") and user_input:
    known_labs = list(rules_engine.keys())
    parsed = parse_lab_values(user_input, known_labs)

    if parsed:
        st.subheader("📋 Evaluation Results")
        emr_notes = []
        for item in parsed:
            lab = item["lab"]
            value = item["value"]
            severity = evaluate_lab_value(lab, value)
            urgency = urgency_map.get(severity, "Unknown")
            recommendation = f"Follow up {urgency.lower()} due to {severity.lower()} result."
            emr_note = f"{lab}: {value} ({severity}) - {recommendation.capitalize()}"
            emr_notes.append(emr_note)

            st.markdown(f"**{lab}**: {value} — **{severity}**")
            st.markdown(f"*Urgency:* {urgency}")
            st.markdown(f"*Recommendation:* {recommendation}")
            if lab in rules_engine:
                plot_lab_bar(lab, value, rules_engine[lab]["thresholds"])
            st.markdown("---")

        st.subheader("📄 EMR Documentation Snippet")
        st.text("\n".join(emr_notes))
    else:
        st.warning("⚠️ No recognized labs found in input.")
