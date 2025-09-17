# train_enron.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

# 1️⃣ Load the Enron dataset
# Replace the path with your actual CSV path
data_path = "C:\\Users\\sibhi\\PhishNet\\Dataset\\emails.csv"
data = pd.read_csv(data_path, encoding="latin-1")

# Check the first few rows
print(data.head())

# Assuming the CSV has columns: "message" and "label"
# You might need to adjust based on actual CSV headers
# For this example, let's create a 'Spam' column:
# Spam=1, Ham=0 (if label exists)
if "label" in data.columns:
    data["Spam"] = data["label"].apply(lambda x: 1 if x.lower() == "spam" else 0)
elif "message" in data.columns:
    # If no label exists, you might need to create manually or skip
    raise ValueError("No label column found. Need labeled data!")
else:
    raise ValueError("Expected columns not found in dataset.")

# 2️⃣ Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    data["message"], data["Spam"], test_size=0.25, random_state=42
)

# 3️⃣ Build pipeline: CountVectorizer + MultinomialNB
clf = Pipeline([
    ("vectorizer", CountVectorizer(stop_words="english")),
    ("nb", MultinomialNB())
])

# 4️⃣ Train the model
print("Training model on Enron dataset... this may take a while.")
clf.fit(X_train, y_train)

# 5️⃣ Evaluate
y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print("✅ Training complete")
print(f"Accuracy: {acc:.4f}")
print("\nClassification Report:\n")
print(classification_report(y_test, y_pred, target_names=["Ham", "Spam"]))

# 6️⃣ Save the trained model
os.makedirs("models", exist_ok=True)
joblib.dump(clf, "models/enron_spam_model.joblib")
print("\n💾 Model saved to models/enron_spam_model.joblib")
