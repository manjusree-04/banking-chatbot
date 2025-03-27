# dataset_creation.py
import pandas as pd
import numpy as np
from faker import Faker
import random
import os
from datetime import datetime, timedelta

fake = Faker()
NUM_RECORDS = 100000

def create_user_details():
    data = {
        'user_id': range(1, NUM_RECORDS + 1),
        'name': [fake.name() for _ in range(NUM_RECORDS)],
        'email': [fake.email() for _ in range(NUM_RECORDS)],
        'phone': [fake.phone_number() for _ in range(NUM_RECORDS)],
        'address': [fake.address() for _ in range(NUM_RECORDS)],
        'date_of_birth': [fake.date_of_birth(minimum_age=18, maximum_age=90) for _ in range(NUM_RECORDS)],
        'occupation': [fake.job() for _ in range(NUM_RECORDS)],
        'annual_income': [random.randint(300000, 2000000) for _ in range(NUM_RECORDS)]
    }
    return pd.DataFrame(data)

def create_transaction_details():
    transaction_types = ['deposit', 'withdrawal', 'transfer', 'payment', 'refund']
    transaction_status = ['completed', 'pending', 'failed']
    data = {
        'transaction_id': range(1, NUM_RECORDS + 1),
        'user_id': [random.randint(1, NUM_RECORDS) for _ in range(NUM_RECORDS)],
        'type': [random.choice(transaction_types) for _ in range(NUM_RECORDS)],
        'amount': [round(random.uniform(100, 100000), 2) for _ in range(NUM_RECORDS)],
        'timestamp': [fake.date_time_between(start_date='-1y', end_date='now') for _ in range(NUM_RECORDS)],
        'status': [random.choice(transaction_status) for _ in range(NUM_RECORDS)],
        'description': [fake.text(max_nb_chars=50) for _ in range(NUM_RECORDS)]
    }
    return pd.DataFrame(data)

def create_credit_cards_dataset():
    card_types = ['Visa', 'MasterCard', 'American Express', 'Discover']
    card_status = ['active', 'blocked', 'expired']
    data = {
        'card_id': range(1, NUM_RECORDS + 1),
        'user_id': [random.randint(1, NUM_RECORDS) for _ in range(NUM_RECORDS)],
        'card_type': [random.choice(card_types) for _ in range(NUM_RECORDS)],
        'card_number': [fake.credit_card_number() for _ in range(NUM_RECORDS)],
        'expiry_date': [fake.credit_card_expire() for _ in range(NUM_RECORDS)],
        'credit_limit': [random.choice([50000, 100000, 200000, 500000]) for _ in range(NUM_RECORDS)],
        'current_balance': [round(random.uniform(0, 100000), 2) for _ in range(NUM_RECORDS)],
        'status': [random.choice(card_status) for _ in range(NUM_RECORDS)]
    }
    return pd.DataFrame(data)

def create_loans_dataset():
    loan_types = ['Personal', 'Home', 'Auto', 'Education', 'Business']
    loan_status = ['approved', 'pending', 'rejected', 'closed']
    data = {
        'loan_id': range(1, NUM_RECORDS + 1),
        'user_id': [random.randint(1, NUM_RECORDS) for _ in range(NUM_RECORDS)],
        'loan_type': [random.choice(loan_types) for _ in range(NUM_RECORDS)],
        'amount': [round(random.uniform(100000, 10000000), 2) for _ in range(NUM_RECORDS)],
        'interest_rate': [round(random.uniform(7, 15), 2) for _ in range(NUM_RECORDS)],
        'term_months': [random.choice([12, 24, 36, 48, 60, 120, 180, 240]) for _ in range(NUM_RECORDS)],
        'status': [random.choice(loan_status) for _ in range(NUM_RECORDS)],
        'application_date': [fake.date_time_between(start_date='-2y', end_date='now') for _ in range(NUM_RECORDS)]
    }
    return pd.DataFrame(data)

def create_complaints_dataset():
    complaint_types = ['Service Issues', 'Technical Problems', 'Account Issues', 'Card Problems', 'Loan Issues', 'Staff Behavior']
    priority_levels = ['Low', 'Medium', 'High', 'Critical']
    status = ['Open', 'In Progress', 'Resolved', 'Closed']
    data = {
        'complaint_id': range(1, NUM_RECORDS + 1),
        'user_id': [random.randint(1, NUM_RECORDS) for _ in range(NUM_RECORDS)],
        'type': [random.choice(complaint_types) for _ in range(NUM_RECORDS)],
        'description': [fake.text(max_nb_chars=200) for _ in range(NUM_RECORDS)],
        'priority': [random.choice(priority_levels) for _ in range(NUM_RECORDS)],
        'status': [random.choice(status) for _ in range(NUM_RECORDS)],
        'created_at': [fake.date_time_between(start_date='-1y', end_date='now') for _ in range(NUM_RECORDS)],
        'resolved_at': [fake.date_time_between(start_date='-1y', end_date='now') for _ in range(NUM_RECORDS)]
    }
    return pd.DataFrame(data)

def create_fraud_reports_dataset():
    fraud_types = ['Unauthorized Transaction', 'Identity Theft', 'Phishing', 'Card Skimming', 'Account Takeover']
    status = ['Under Investigation', 'Resolved', 'Closed', 'Pending']
    data = {
        'report_id': range(1, NUM_RECORDS + 1),
        'user_id': [random.randint(1, NUM_RECORDS) for _ in range(NUM_RECORDS)],
        'fraud_type': [random.choice(fraud_types) for _ in range(NUM_RECORDS)],
        'description': [fake.text(max_nb_chars=200) for _ in range(NUM_RECORDS)],
        'amount_involved': [round(random.uniform(1000, 500000), 2) for _ in range(NUM_RECORDS)],
        'reported_date': [fake.date_time_between(start_date='-1y', end_date='now') for _ in range(NUM_RECORDS)],
        'status': [random.choice(status) for _ in range(NUM_RECORDS)]
    }
    return pd.DataFrame(data)

def create_faqs_dataset():
    # Creating a comprehensive FAQ dataset for banking
    questions = []
    answers = []
    
    # Account Related
    questions.extend([
        "How do I open a new account?",
        "What documents are required for account opening?",
        "How do I check my account balance?",
        "What are the different types of accounts available?",
        "How do I close my account?",
        # Add more account-related questions
    ])
    
    answers.extend([
        "Visit our nearest branch with required documents or apply online through our website.",
        "You need ID proof, address proof, PAN card, and passport-size photographs.",
        "You can check balance through net banking, mobile app, ATM, or by visiting branch.",
        "We offer savings, current, salary, and fixed deposit accounts.",
        "Submit an account closure form at your branch with required documents.",
        # Add corresponding answers
    ])
    
    # Add more categories (Cards, Loans, Net Banking, etc.)
    # Extend this to create 100,000 records by adding variations and combinations
    
    # Generate variations to reach 100,000 records
    base_len = len(questions)
    while len(questions) < NUM_RECORDS:
        idx = random.randint(0, base_len - 1)
        questions.append(questions[idx])
        answers.append(answers[idx])
    
    return pd.DataFrame({
        'question_id': range(1, NUM_RECORDS + 1),
        'question': questions[:NUM_RECORDS],
        'answer': answers[:NUM_RECORDS],
        'category': [random.choice(['Account', 'Cards', 'Loans', 'Net Banking', 'General']) for _ in range(NUM_RECORDS)]
    })

def create_assistance_dataset():
    assistance_types = ['General Query', 'Technical Support', 'Account Support', 'Product Information', 'Service Request']
    status = ['Pending', 'In Progress', 'Resolved', 'Closed']
    data = {
        'assistance_id': range(1, NUM_RECORDS + 1),
        'user_id': [random.randint(1, NUM_RECORDS) for _ in range(NUM_RECORDS)],
        'type': [random.choice(assistance_types) for _ in range(NUM_RECORDS)],
        'query': [fake.text(max_nb_chars=150) for _ in range(NUM_RECORDS)],
        'status': [random.choice(status) for _ in range(NUM_RECORDS)],
        'created_at': [fake.date_time_between(start_date='-1y', end_date='now') for _ in range(NUM_RECORDS)],
        'response_time': [random.randint(1, 72) for _ in range(NUM_RECORDS)]  # in hours
    }
    return pd.DataFrame(data)

def main():
    # Create directory if it doesn't exist
    if not os.path.exists('datasets'):
        os.makedirs('datasets')

    # Create and save all datasets
    print("Creating datasets...")
    
    datasets = {
        'user_details.csv': create_user_details(),
        'transaction_details.csv': create_transaction_details(),
        'credit_cards.csv': create_credit_cards_dataset(),
        'loans.csv': create_loans_dataset(),
        'complaints.csv': create_complaints_dataset(),
        'fraud_reports.csv': create_fraud_reports_dataset(),
        'faqs.csv': create_faqs_dataset(),
        'assistance.csv': create_assistance_dataset()
    }

    for filename, df in datasets.items():
        print(f"Saving {filename}...")
        df.to_csv(f'datasets/{filename}', index=False)
        print(f"Saved {filename} with {len(df)} records")

if __name__ == "__main__":
    main()