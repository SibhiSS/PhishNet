# generate_social_synthetic_1000.py
"""
Generate a 1000-row synthetic CSV for social-engineering (emotional attack) detection.

Creates: Dataset/social_synthetic_1000.csv
Columns: Message,Label
Label values: Attack or No Attack

Usage:
    python generate_social_synthetic_1000.py
"""
import os
import random
import csv

random.seed(42)

os.makedirs("Dataset", exist_ok=True)
OUT_PATH = os.path.join("Dataset", "social_synthetic_1000.csv")

# Configuration
TOTAL = 1000
ATTACK_RATIO = 0.61  # ~61% attacks
NUM_ATTACK = int(TOTAL * ATTACK_RATIO)
NUM_NO_ATTACK = TOTAL - NUM_ATTACK

first_names = [
    "Alex","Jordan","Taylor","Morgan","Casey","Riley","Sam","Chris","Jamie","Robin",
    "Pat","Lee","Drew","Devon","Avery","Cameron","Skyler","Shawn","Dana","Nikhil",
    "Priya","Arjun","Meera","Isha","Rahul","Sanjay","Anita","Vikram","Leena","Ravi"
]
last_names = [
    "Patel","Kumar","Singh","Sharma","Iyer","Gupta","Raghavan","Nair","Kapoor","Mehta",
    "Smith","Johnson","Brown","Davis","Miller","Wilson","Taylor","Anderson","Thomas","Jackson",
    "Ghosh","Verma","Chatterjee","Saxena","Fernando","Khan","Bose","Das","Mitra","Roy"
]
companies = [
    "Acme Corp","Notion","Globex","Innotech","Stellar Inc","Finity","BrightCo",
    "Nimbus Labs","Quantum Solutions","Astra Systems"
]
projects = [
    "budget report","financial forecast","Q3 deliverables","deployment script",
    "customer list","research notes","confidential roadmap","product spec",
    "sales pipeline","security audit"
]
reasons = ["urgent","sensitive","confidential","time-sensitive","important","private"]

# Templates
attack_templates = [
    "Hey, it's {name} from {company}. I need your help urgently with the {project} — can you share your login so I can finish this now?",
    "I'm really worried about your account — we saw suspicious activity. Please verify your credentials immediately here: {link}",
    "Huge congratulations! You've been selected for an exclusive reward. Click {link} and provide your details to claim it.",
    "I can't believe what happened to your colleague! You must be devastated. Can we chat? I need some information about your access.",
    "The boss is furious about the {project}. Can you send me the latest files so I can fix this before the meeting?",
    "Please, I'm stuck and really need your password to resolve an urgent issue with {company}. I promise it's quick.",
    "Your account has been compromised. Reset your password now at {link} or you'll lose access.",
    "Can you do me a favour? This is super important to me — send over the client list and I'll handle the rest.",
    "I heard there may be layoffs. Are you okay? If so, share your personal email so I can tell you privately.",
    "You've been pre-approved for an exclusive offer. I need your details to process it at {link}.",
    "Hey, I'm new here and everyone is so cold. Could you share your access so I can finish this task?",
    "I found something alarming about your account — please confirm your banking details at {link}.",
    "Your recent project was outstanding! Could you send me the full report (including attachments)?",
    "I saw a weird transaction on your account. Confirm your payment details here: {link}",
    "I hate to bother you, but I'm really stressed and need you to give me access to the server now.",
    "We need to verify your identity before payroll — confirm details at {link}",
    "There was a policy change affecting your account. Please confirm your SSN and DOB at {link}",
    "I've been assigned to audit the {project}; share the files and I'll mark them confidential.",
    "Your mailbox exceeded quota. Follow {link} to avoid losing emails.",
    "Immediate action required: confirm your credentials at {link} to prevent account suspension."
]

no_attack_templates = [
    "Hey {name}, just checking in — are you free for a quick sync on the {project} tomorrow?",
    "Thanks for the great work on the {project}. Let's celebrate at lunch on Friday.",
    "Reminder: the team meeting is at 10 AM. Agenda: {project} status and next steps.",
    "Please find attached the notes from today's call. Let me know if I missed anything.",
    "FYI: we've updated the internal wiki with the new onboarding steps.",
    "Great job on the presentation — the client loved it. Can you send the slides?",
    "Can you review this draft when you have a moment? No rush, just want your feedback.",
    "Happy Birthday {name}! Hope you have a great day.",
    "I'm impressed with your recent work — would you like to present it to the team?",
    "Would you be able to share the meeting minutes from last week?",
    "Let's schedule 1:1 next week to discuss career goals and development.",
    "Can you help me test the staging build later today? I need another pair of eyes.",
    "Thanks for your help earlier — the fix worked perfectly.",
    "Please update the spreadsheet with your holiday dates when you get a chance.",
    "Could you share the link to the document you mentioned? I couldn't find it.",
    "Quick FYI: the server maintenance is tomorrow night, expect brief downtime.",
    "Appreciate your input on the doc — minor edits only.",
    "Can we postpone the meeting to Thursday? I have a conflict.",
    "Thanks again for covering my shift — I owe you one.",
    "I'd love your feedback on the new template when you have time."
]

# Helper to produce a pseudo link
def make_link():
    domains = ["example.com", "notion.so", "acme-corp.com", "trust-pay.io", "secure-login.net", "safe-verify.org"]
    path = random.choice(["verify","claim","login","reset","offer","update","confirm","docs","secure","auth"])
    return f"https://{random.choice(domains)}/{path}?id={random.randint(10000,99999)}"

# Helper to randomize a name
def make_name():
    return f"{random.choice(first_names)} {random.choice(last_names)}"

rows = []

# Generate Attack rows
for i in range(NUM_ATTACK):
    template = random.choice(attack_templates)
    name = make_name()
    company = random.choice(companies)
    project = random.choice(projects)
    link = make_link()
    msg = template.format(name=name, company=company, project=project, link=link)
    # small random preface/suffix or slight rewording
    if random.random() < 0.15:
        msg = random.choice(["Urgent: ", "Important: ", "Please read: "]) + msg
    if random.random() < 0.12:
        msg += "\n\nThanks, " + random.choice([name.split()[0], "Team", "Admin"])
    # punctuation and casing noise
    if random.random() < 0.08:
        msg = msg.replace(".", "...")
    rows.append((msg, "Attack"))

# Generate No Attack rows
for i in range(NUM_NO_ATTACK):
    template = random.choice(no_attack_templates)
    name = random.choice(first_names)
    project = random.choice(projects)
    msg = template.format(name=name, project=project)
    if random.random() < 0.12:
        msg += "\n\nBest,\n" + random.choice(first_names)
    if random.random() < 0.06:
        msg += " " + random.choice(["Thanks!", "Appreciate it.", "Please advise."])
    rows.append((msg, "No Attack"))

# Shuffle overall dataset
random.shuffle(rows)

# Small perturbations to reduce exact duplicates
def perturb_text(t):
    if random.random() < 0.07:
        fillers = [
            "Let me know if that works.",
            "Please advise.",
            "Thanks in advance.",
            "Can you confirm?",
            "Appreciate your help.",
            "Ping me if you have questions."
        ]
        return t + " " + random.choice(fillers)
    return t

rows = [(perturb_text(m), label) for (m, label) in rows]

# Ensure length exactly TOTAL (just in case)
rows = rows[:TOTAL]

# Save to CSV
with open(OUT_PATH, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Message", "Label"])
    for m, label in rows:
        writer.writerow([m, label])

print(f"Generated {len(rows)} rows -> {OUT_PATH}")
