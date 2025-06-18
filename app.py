
import streamlit as st
import re
import json
import matplotlib.pyplot as plt

# Load rules and synonyms
with open("lab_rules_engine_all_labs.json", "r") as f:
    rules_engine = json.load(f)

with open("lab_synonyms.json", "r") as f:
    lab_synonyms = json.load(f)

# Flatten synonyms for reverse lookup
synonym_to_standard = {}
for standard_name, synonyms in lab_synonyms.items():
    for s in synonyms:
        synonym_to_standard[s.lower()] = standard_name

def normalize_lab_name(name):
    cleaned = name.strip().lower().replace(":", "").replace("=", "").replace("/", " ").replace("-", " ").replace("_", " ")
    for synonym, standard in synonym_to_standard.items():
        if synonym in cleaned:
            return standard
    return None

def parse_lab_values(ehr_text):
    parsed_labs = []
    lab_pattern = r"([A-Za-z0-9 /()%\[\]_:-]+)[\s:=\-]+([0-9.]+)(?:\s*[a-zA-Z/%]*)?"
    matches = re.findall(lab_pattern, ehr_text)

    for lab_name, value in matches:
        standard_lab = normalize_lab_name(lab_name)
        if standard_lab:
            try:
                parsed_labs.append({
                    "lab": standard_lab,
                    "value": float(re.findall(r"\d+\.?\d*", value)[0])
                })
            except (ValueError, IndexError):
                continue
    return parsed_labs

def evaluate_lab_value(lab_name, value):
    thresholds = rules_engine.get(lab_name, {}).get("thresholds", [])
    evaluation = "Normal"

    def within_range(val, range_str):
        try:
            range_str = (range_str.replace(",", "")
                                   .replace("–", "-")
                                   .replace("—", "-")
                                   .replace("−", "-"))
            if "-" in range_str:
                low, high = map(float, range_str.split("-"))
                return low <= val <= high
            elif "<" in range_str:
                bound = float(re.findall(r"\d+\.?\d*", range_str)[0])
                return val < bound
            elif ">" in range_str:
                bound = float(re.findall(r"\d+\.?\d*", range_str)[0])
                return val > bound
        except:
            return False
        return False

    for t in thresholds:
        if within_range(value, t["threshold"]):
            evaluation = t["severity"]
            break

    return evaluation

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

st.title("EHR Lab Parser & Management Assistant")

user_input = st.text_area("Paste EHR lab data below:")

if st.button("Evaluate Labs") and user_input:
    parsed = parse_lab_values(user_input)

    if parsed:
        results = []
        st.subheader("Evaluation Results")

        for item in parsed:
            lab = item["lab"]
            value = item["value"]
            severity = evaluate_lab_value(lab, value)
            urgency = urgency_map.get(severity, "Unknown")
            rec = f"Follow up {urgency.lower()} due to {severity.lower()} result."
            emr = f"{lab}: {value} ({severity}) - {rec}"

            results.append({
                "Lab": lab,
                "Value": value,
                "Severity": severity,
                "Urgency": urgency,
                "Recommendation": rec,
                "EMR": emr
            })

            st.markdown(f"**{lab}**: {value} — {severity}")
            st.markdown(f"*Urgency:* {urgency}")
            st.markdown(f"*Recommendation:* {rec}")
            st.markdown(f"*EMR Note:* `{emr}`\n")

            # Optional bar plot
            fig, ax = plt.subplots()
            ax.barh([lab], [value])
            ax.set_xlabel("Lab Value")
            ax.set_title(f"{lab} = {value}")
            st.pyplot(fig)

    else:
        st.warning("No recognized labs found in input.")
