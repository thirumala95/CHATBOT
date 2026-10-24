import csv
import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet


def load_disease_data():
    data = {}
    csv_path = os.path.join(os.path.dirname(__file__), "..", "disease_data.csv")
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            disease = row["disease"]
            symptoms = [s.strip().lower() for s in row["symptoms"].split(";")]
            data[disease] = {
                "symptoms": symptoms,
                "precautions": row["precautions"],
                "doctor_advice": row["doctor_advice"],
            }
    return data


DISEASE_DATA = load_disease_data()


def symptom_matches(extracted_word, disease_symptom):
    extracted_word = extracted_word.lower().strip()
    disease_symptom = disease_symptom.lower().strip()
    return extracted_word in disease_symptom or disease_symptom in extracted_word


class ActionMatchDisease(Action):
    def name(self):
        return "action_match_disease"

    def run(self, dispatcher, tracker, domain):
        symptoms = tracker.get_slot("symptom") or []
        symptoms = [s.lower().strip() for s in symptoms]

        if not symptoms:
            dispatcher.utter_message(text="Could you describe your symptoms more specifically? For example: fever, cough, headache, rash.")
            return [SlotSet("symptom", [])]

        scores = {}
        for disease, info in DISEASE_DATA.items():
            match_count = 0
            matched_csv_symptoms = set()
            for extracted in symptoms:
                for csv_symptom in info["symptoms"]:
                    if csv_symptom in matched_csv_symptoms:
                        continue
                    if symptom_matches(extracted, csv_symptom):
                        match_count += 1
                        matched_csv_symptoms.add(csv_symptom)
                        break
            if match_count > 0:
                scores[disease] = match_count

        if not scores:
            dispatcher.utter_message(text="I couldn't match your symptoms to a specific illness in my database. Please consult a doctor for proper evaluation.")
            return [SlotSet("symptom", [])]

        best_matches = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_score = best_matches[0][1]
        top_diseases = [d for d, s in best_matches if s == top_score]

        if len(top_diseases) == 1:
            disease = top_diseases[0]
            info = DISEASE_DATA[disease]
            message = (
                f"Based on your symptoms, this may be associated with **{disease}**.\n\n"
                f"Precautions: {info['precautions']}\n\n"
                f"{info['doctor_advice']}\n\n"
                f"This is not a medical diagnosis. Please consult a doctor for proper evaluation."
            )
        else:
            disease_list = ", ".join(top_diseases)
            message = (
                f"Based on your symptoms, this could be associated with a few possibilities: **{disease_list}**.\n\n"
                f"This is not a medical diagnosis. Please consult a doctor for proper evaluation."
            )

        dispatcher.utter_message(text=message)
        return [SlotSet("symptom", [])]
