import pandas as pd
import numpy as np
import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from tqdm import tqdm
import multiprocessing
import os
import logging
from concurrent.futures import ProcessPoolExecutor

# Download NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('preprocessing.log'),
        logging.StreamHandler()
    ]
)

class BankingTextPreprocessor:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Banking-specific stop words to remove
        self.stop_words.update([
            'please', 'could', 'would', 'also', 'may', 'might', 'shall', 
            'should', 'hello', 'hi', 'hey', 'thanks', 'thank', 'dear'
        ])
        
        # Banking terms to preserve (won't be lemmatized or removed)
        self.banking_terms = {
            # Account types
            'savings', 'current', 'salary', 'fixed', 'deposit', 'fd', 'rd', 'recurring',
            # Transactions
            'transfer', 'neft', 'rtgs', 'imps', 'upi', 'transaction', 'balance',
            # Cards
            'debit', 'credit', 'card', 'pin', 'cvv', 'expiry', 'limit',
            # Loans
            'loan', 'emi', 'interest', 'principal', 'tenure', 'maturity',
            # Banking operations
            'cheque', 'draft', 'withdrawal', 'deposit', 'overdraft', 'standing', 'instruction',
            # Security
            'otp', 'password', 'authentication', 'verification', 'kyc', 'pan', 'aadhaar',
            # Digital banking
            'netbanking', 'mobilebanking', 'app', 'login', 'logout', 'username'
        }
        
        # Currency and numbers pattern
        self.currency_pattern = re.compile(r'(\$|€|£|₹|¥|₩|₽|₿|rs|inr|usd)\s?\d+([.,]\d+)*')
        self.number_pattern = re.compile(r'\d+([.,]\d+)*')
        
        # Special characters to preserve
        self.special_chars = {'@', '#', '%', '&', '*', '-', '_', '/'}
        
        # Contractions mapping
        self.contractions = {
            "won't": "will not", "can't": "cannot", "n't": " not", "'re": " are",
            "'s": " is", "'d": " would", "'ll": " will", "'t": " not", "'ve": " have",
            "'m": " am"
        }

    def clean_text(self, text):
        """Basic text cleaning while preserving banking-specific patterns"""
        if not isinstance(text, str):
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Preserve currency values
        text = self.currency_pattern.sub(' CURRENCY ', text)
        
        # Preserve account numbers (long numbers)
        text = self.number_pattern.sub(lambda x: ' NUMBER ' if len(x.group()) > 3 else x.group(), text)
        
        # Expand contractions
        for contraction, expansion in self.contractions.items():
            text = text.replace(contraction, expansion)
        
        # Remove URLs
        text = re.sub(r'https?://\S+|www\.\S+', ' URL ', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', ' EMAIL ', text)
        
        # Remove non-alphanumeric characters except preserved ones
        text = ''.join(
            char if char.isalnum() or char in self.special_chars or char.isspace() 
            else ' ' 
            for char in text
        )
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text

    def tokenize(self, text):
        """Tokenize text while preserving banking terms"""
        tokens = word_tokenize(text)
        return tokens

    def process_tokens(self, tokens):
        """Process tokens with banking-specific rules"""
        processed_tokens = []
        for token in tokens:
            # Preserve banking terms exactly as they are
            if token in self.banking_terms:
                processed_tokens.append(token)
                continue
                
            # Remove stop words for non-banking terms
            if token in self.stop_words:
                continue
                
            # Lemmatize non-banking terms
            lemma = self.lemmatizer.lemmatize(token)
            processed_tokens.append(lemma)
            
        return processed_tokens

    def preprocess_text(self, text):
        """Complete text preprocessing pipeline"""
        try:
            cleaned = self.clean_text(text)
            tokens = self.tokenize(cleaned)
            processed = self.process_tokens(tokens)
            return ' '.join(processed)
        except Exception as e:
            logging.error(f"Error preprocessing text: {str(e)}")
            return ""

def process_dataset_chunk(args):
    """Process a chunk of dataset in parallel"""
    chunk, preprocessor, text_columns = args
    for col in text_columns:
        if col in chunk.columns:
            chunk[f'processed_{col}'] = chunk[col].apply(preprocessor.preprocess_text)
    return chunk

class BankingDatasetPreprocessor:
    def __init__(self):
        self.preprocessor = BankingTextPreprocessor()
        self.processed_dir = 'processed_datasets'
        os.makedirs(self.processed_dir, exist_ok=True)
        
        # Define text columns for each dataset
        self.dataset_config = {
            'user_details': [],
            'transaction_details': ['description'],
            'credit_cards': [],
            'loans': [],
            'complaints': ['description'],
            'fraud_reports': ['description'],
            'faqs': ['question', 'answer'],
            'assistance': ['query']
        }

    def preprocess_dataset(self, dataset_name):
        """Preprocess a single dataset"""
        try:
            input_path = f'datasets/{dataset_name}.csv'
            output_path = f'{self.processed_dir}/processed_{dataset_name}.csv'
            
            if not os.path.exists(input_path):
                logging.warning(f"Dataset {input_path} not found")
                return
            
            logging.info(f"Processing {dataset_name} dataset...")
            
            # Read in chunks for memory efficiency
            chunks = pd.read_csv(input_path, chunksize=10000)
            processed_chunks = []
            
            with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()-1) as executor:
                args = [(chunk, self.preprocessor, self.dataset_config[dataset_name]) for chunk in chunks]
                
                for result in tqdm(executor.map(process_dataset_chunk, args), desc=f"Processing {dataset_name}"):
                    processed_chunks.append(result)
            
            # Combine and save
            pd.concat(processed_chunks).to_csv(output_path, index=False)
            logging.info(f"Saved processed {dataset_name} to {output_path}")
            
        except Exception as e:
            logging.error(f"Error processing {dataset_name}: {str(e)}")

    def preprocess_all_datasets(self):
        """Preprocess all banking datasets"""
        for dataset_name in self.dataset_config.keys():
            self.preprocess_dataset(dataset_name)
        
        # Create combined training data from relevant datasets
        self.create_training_data()

    def create_training_data(self):
        """Create combined training data from preprocessed datasets"""
        try:
            logging.info("Creating combined training data...")
            
            # Load and combine relevant datasets
            dfs = []
            
            # FAQs (questions and answers)
            if os.path.exists(f'{self.processed_dir}/processed_faqs.csv'):
                faqs = pd.read_csv(f'{self.processed_dir}/processed_faqs.csv')
                faqs['intent'] = 'faq'
                dfs.append(faqs[['processed_question', 'processed_answer', 'intent']].rename(columns={'processed_question': 'text', 'processed_answer': 'response'}))
            
            # Complaints
            if os.path.exists(f'{self.processed_dir}/processed_complaints.csv'):
                complaints = pd.read_csv(f'{self.processed_dir}/processed_complaints.csv')
                complaints['intent'] = 'complaint'
                complaints['response'] = 'Thank you for reporting this issue. Our team will look into it.'
                dfs.append(complaints[['processed_description', 'response', 'intent']].rename(columns={'processed_description': 'text'}))
            
            # Assistance queries
            if os.path.exists(f'{self.processed_dir}/processed_assistance.csv'):
                assistance = pd.read_csv(f'{self.processed_dir}/processed_assistance.csv')
                assistance['intent'] = 'assistance'
                assistance['response'] = 'Our customer support team will contact you shortly.'
                dfs.append(assistance[['processed_query', 'response', 'intent']].rename(columns={'processed_query': 'text'}))
            
            # Fraud reports
            if os.path.exists(f'{self.processed_dir}/processed_fraud_reports.csv'):
                fraud = pd.read_csv(f'{self.processed_dir}/processed_fraud_reports.csv')
                fraud['intent'] = 'fraud'
                fraud['response'] = 'We take fraud seriously. Our security team will investigate this immediately.'
                dfs.append(fraud[['processed_description', 'response', 'intent']].rename(columns={'processed_description': 'text'}))
            
            # Transaction descriptions
            if os.path.exists(f'{self.processed_dir}/processed_transaction_details.csv'):
                transactions = pd.read_csv(f'{self.processed_dir}/processed_transaction_details.csv')
                transactions['intent'] = 'transaction'
                transactions['response'] = 'Your transaction details have been recorded.'
                dfs.append(transactions[['processed_description', 'response', 'intent']].rename(columns={'processed_description': 'text'}))
            
            if dfs:
                combined = pd.concat(dfs, ignore_index=True)
                combined.to_csv(f'{self.processed_dir}/combined_training_data.csv', index=False)
                logging.info("Saved combined training data")
                
                # Create intent mapping file
                intent_counts = combined['intent'].value_counts().to_dict()
                pd.DataFrame({
                    'intent': list(intent_counts.keys()),
                    'count': list(intent_counts.values()),
                    'sample_response': combined.drop_duplicates('intent')['response'].values
                }).to_csv(f'{self.processed_dir}/intent_mapping.csv', index=False)
            else:
                logging.warning("No datasets found to combine for training data")
                
        except Exception as e:
            logging.error(f"Error creating training data: {str(e)}")

def main():
    preprocessor = BankingDatasetPreprocessor()
    preprocessor.preprocess_all_datasets()

if __name__ == "__main__":
    main()