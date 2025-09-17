# train.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
import joblib

# 1. Load dataset
data = pd.read_csv("C:\\Users\\sibhi\\PhishNet\\Dataset\\spam.csv", encoding="latin-1")



# Clean dataset (some versions of spam.csv have extra columns)
if "Category" in data.columns and "Message" in data.columns:
    data = data[["Category", "Message"]]
else:
    data = data.iloc[:, :2]   # First 2 columns only
    data.columns = ["Category", "Message"]

# 2. Encode labels (ham=0, spam=1)
data["Spam"] = data["Category"].apply(lambda x: 1 if x == "spam" else 0)

# 3. Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    data["Message"], data["Spam"], test_size=0.25, random_state=42
)

# 4. Build pipeline
clf = Pipeline([
    ("vectorizer", CountVectorizer()),
    ("nb", MultinomialNB())
])

# 5. Train model
clf.fit(X_train, y_train)

# 6. Evaluate
y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print("✅ Training complete")
print(f"Accuracy: {acc:.4f}")
print("\nClassification Report:\n")
print(classification_report(y_test, y_pred, target_names=["Ham", "Spam"]))

# 7. Save model
os.makedirs("models", exist_ok=True)
joblib.dump(clf, "models/spam_model_v1.joblib")

print("\n💾 Model saved to models/spam_model_v1.joblib")

joblib.dump(clf, "spam_model.pkl")
print("✅ Model saved as spam_model.pkl")
