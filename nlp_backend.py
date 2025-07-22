import pandas as pd
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
from collections import Counter
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from credentials import EMAIL, PASSWORD

type_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
ner_model = AutoModelForTokenClassification.from_pretrained("Babelscape/wikineural-multilingual-ner")
ner_tokenizer = AutoTokenizer.from_pretrained("Babelscape/wikineural-multilingual-ner")
ner_pipeline = pipeline("ner", model=ner_model, tokenizer=ner_tokenizer, grouped_entities=True)

type_labels = ["Infrastructure", "Academics", "Administration", "Faculty", "Hostel", "Safety", "Other"]
ethical_severity = {
    "Infrastructure": 0.6,
    "Academics": 0.4,
    "Administration": 0.5,
    "Faculty": 0.3,
    "Hostel": 0.7,
    "Safety": 1.0,
    "Other": 0.2
}

def classify_grievance_type(text):
    result = type_classifier(text, type_labels, multi_label=False)
    return result['labels'][0]

def extract_named_entities(text):
    ner_results = ner_pipeline(text)
    return ", ".join(f"{e['entity_group']}: {e['word']}" for e in ner_results)

def assign_priority(row, counts, total):
    freq = counts[row['grievance_type']] / total
    severity = ethical_severity.get(row['grievance_type'], 0.2)
    bonus = 0.2 if str(row.get("Written Complaint Submitted", "")).strip().lower() == "yes" else 0
    return round(freq * 0.4 + severity * 0.4 + bonus, 2)

def generate_response(row):
    templates = {
        "Infrastructure": "We acknowledge your concern regarding infrastructure.",
        "Academics": "We will review your academic concern with urgency.",
        "Administration": "Our team will look into this matter soon.",
        "Faculty": "We value your feedback regarding faculty issues.",
        "Hostel": "Your hostel concern has been noted.",
        "Safety": "We are addressing your safety concern urgently.",
        "Other": "We have noted your concern and will review it."
    }
    base = templates.get(row['grievance_type'], "Thank you for your grievance.")
    return f"URGENT: {base}" if row['priority_score'] > 0.6 else base

def process_grievances(df):
    df['grievance_type'] = df['Brief Statement of Grievance'].apply(classify_grievance_type)
    type_counts = Counter(df['grievance_type'])
    total = len(df)

    df['priority_score'] = df.apply(lambda row: assign_priority(row, type_counts, total), axis=1)
    df['entities'] = df['Brief Statement of Grievance'].apply(extract_named_entities)
    df['automated_response'] = df.apply(generate_response, axis=1)

    return df, None

def send_email_response(row):
    subject = f"Grievance Acknowledgement - {row['grievance_type']}"
    body = f"Dear {row['Name of the student']},\n\n{row['automated_response']}\n\nRegards,\nAdmin"

    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = row['Mail id']
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, row['Mail id'], msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")
