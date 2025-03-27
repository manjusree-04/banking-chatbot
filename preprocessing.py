# preprocessing.py
import pandas as pd
import numpy as np
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize
import nltk
import re
from tqdm import tqdm
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import logging
import os

# Download required NLTK data
try:
    nltk.download(['punkt', 'stopwords', 'wordnet', 'averaged_perceptron_tagger'])
except:
    print("NLTK data already downloaded or error in downloading")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('preprocessing.log'),
        logging.StreamHandler()
    ]
)

# Contractions dictionary
CONTRACTION_MAP = {
    "ain't": "is not",
    "aren't": "are not",
    "can't": "cannot",
    "couldn't": "could not",
    "didn't": "did not",
    "doesn't": "does not",
    "don't": "do not",
    "hadn't": "had not",
    "hasn't": "has not",
    "haven't": "have not",
    "he'd": "he would",
    "he'll": "he will",
    "he's": "he is",
    "i'd": "i would",
    "i'll": "i will",
    "i'm": "i am",
    "i've": "i have",
    "isn't": "is not",
    "it's": "it is",
    "let's": "let us",
    "mightn't": "might not",
    "mustn't": "must not",
    "shan't": "shall not",
    "she'd": "she would",
    "she'll": "she will",
    "she's": "she is",
    "shouldn't": "should not",
    "that's": "that is",
    "there's": "there is",
    "they'd": "they would",
    "they'll": "they will",
    "they're": "they are",
    "they've": "they have",
    "we'd": "we would",
    "we're": "we are",
    "we've": "we have",
    "weren't": "were not",
    "what'll": "what will",
    "what're": "what are",
    "what's": "what is",
    "what've": "what have",
    "where's": "where is",
    "who'd": "who would",
    "who'll": "who will",
    "who're": "who are",
    "who's": "who is",
    "who've": "who have",
    "won't": "will not",
    "wouldn't": "would not",
    "you'd": "you would",
    "you'll": "you will",
    "you're": "you are",
    "you've": "you have"
}

class TextPreprocessor:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Add banking-specific stop words
        self.stop_words.update([
            'bank', 'banking', 'please', 'need', 'help', 'hello', 'hi', 'hey',
            'thanks', 'thank', 'you', 'dear', 'sir', 'madam', 'would', 'could'
        ])
        
        # Banking specific terms to preserve
        self.banking_terms = {
            'atm', 'pin', 'credit', 'debit', 'card', 'loan', 'emi', 'kyc',
            'upi', 'neft', 'rtgs', 'imps', 'fd', 'rd', 'savings', 'current',
            'balance', 'transfer', 'deposit', 'withdraw', 'statement', 'account',
            'interest', 'bank', 'branch', 'cheque', 'check', 'draft', 'payment',
            'transaction', 'online', 'mobile', 'password', 'username', 'login',
            'logout', 'profile', 'beneficiary', 'payee', 'mandate', 'salary',
            'pension', 'insurance', 'investment', 'mutual', 'fund', 'stock',
            'share', 'bond', 'dividend', 'tax', 'gst', 'pan', 'aadhar', 'kyc'
        }

    def expand_contractions(self, text):
        """Expand contractions in text"""
        for contraction, expansion in CONTRACTION_MAP.items():
            text = text.replace(contraction, expansion)
        return text

    def clean_text(self, text):
        """Clean and normalize text"""
        try:
            # Convert to string if not already
            text = str(text)
            
            # Convert to lowercase
            text = text.lower()
            
            # Expand contractions
            text = self.expand_contractions(text)
            
            # Handle special cases for banking terms
            words = text.split()
            cleaned_words = []
            for word in words:
                # Preserve banking terms
                if word.lower() in self.banking_terms:
                    cleaned_words.append(word)
                else:
                    # Remove special characters and numbers, except for specific patterns
                    cleaned_word = re.sub(r'[^a-zA-Z\s]', '', word)
                    if cleaned_word:
                        cleaned_words.append(cleaned_word)
            
            text = ' '.join(cleaned_words)
            
            # Remove extra whitespace
            text = ' '.join(text.split())
            
            return text
        except Exception as e:
            logging.error(f"Error in clean_text: {str(e)}")
            return text

    def tokenize(self, text):
        """Tokenize text into words"""
        try:
            return word_tokenize(text)
        except Exception as e:
            logging.error(f"Error in tokenize: {str(e)}")
            return []

    def remove_stopwords(self, tokens):
        """Remove stopwords while preserving banking terms"""
        try:
            return [token for token in tokens 
                   if token not in self.stop_words or token in self.banking_terms]
        except Exception as e:
            logging.error(f"Error in remove_stopwords: {str(e)}")
            return tokens

    def lemmatize(self, tokens):
        """Lemmatize tokens while preserving banking terms"""
        try:
            return [self.lemmatizer.lemmatize(token) if token not in self.banking_terms 
                   else token for token in tokens]
        except Exception as e:
            logging.error(f"Error in lemmatize: {str(e)}")
            return tokens

    def preprocess(self, text):
        """Complete preprocessing pipeline"""
        try:
            cleaned_text = self.clean_text(text)
            tokens = self.tokenize(cleaned_text)
            tokens = self.remove_stopwords(tokens)
            tokens = self.lemmatize(tokens)
            return ' '.join(tokens)
        except Exception as e:
            logging.error(f"Error in preprocess: {str(e)}")
            return text

def process_chunk(args):
    """Process a chunk of data"""
    chunk, preprocessor, text_column = args
    return chunk[text_column].apply(preprocessor.preprocess)

class DatasetPreprocessor:
    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.processed_data_dir = 'processed_datasets'
        os.makedirs(self.processed_data_dir, exist_ok=True)

    def preprocess_dataset(self, df, text_columns, chunk_size=10000):
        """Preprocess a dataset using multiprocessing"""
        try:
            num_processes = multiprocessing.cpu_count() - 1
            
            for text_column in text_columns:
                logging.info(f"Processing column: {text_column}")
                
                # Split dataframe into chunks
                chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]
                
                processed_chunks = []
                with ProcessPoolExecutor(max_workers=num_processes) as executor:
                    args = [(chunk, self.preprocessor, text_column) for chunk in chunks]
                    
                    # Process chunks in parallel with progress bar
                    for processed_chunk in tqdm(
                        executor.map(process_chunk, args),
                        total=len(chunks),
                        desc=f"Processing {text_column}"
                    ):
                        processed_chunks.append(processed_chunk)
                
                # Combine processed chunks
                df[f'processed_{text_column}'] = pd.concat(processed_chunks)
                
            return df
        
        except Exception as e:
            logging.error(f"Error in preprocess_dataset: {str(e)}")
            return df

    def preprocess_all_datasets(self):
        """Preprocess all datasets"""
        try:
            # Process FAQs dataset
            logging.info("Processing FAQs dataset...")
            faqs_df = pd.read_csv('datasets/faqs.csv')
            faqs_df = self.preprocess_dataset(faqs_df, ['question', 'answer'])
            faqs_df.to_csv(f'{self.processed_data_dir}/processed_faqs.csv', index=False)

            # Process Complaints dataset
            logging.info("Processing Complaints dataset...")
            complaints_df = pd.read_csv('datasets/complaints.csv')
            complaints_df = self.preprocess_dataset(complaints_df, ['description'])
            complaints_df.to_csv(f'{self.processed_data_dir}/processed_complaints.csv', index=False)

            # Process Assistance dataset
            logging.info("Processing Assistance dataset...")
            assistance_df = pd.read_csv('datasets/assistance.csv')
            assistance_df = self.preprocess_dataset(assistance_df, ['query'])
            assistance_df.to_csv(f'{self.processed_data_dir}/processed_assistance.csv', index=False)

            # Process Fraud Reports dataset
            logging.info("Processing Fraud Reports dataset...")
            fraud_df = pd.read_csv('datasets/fraud_reports.csv')
            fraud_df = self.preprocess_dataset(fraud_df, ['description'])
            fraud_df.to_csv(f'{self.processed_data_dir}/processed_fraud_reports.csv', index=False)

            # Process Transaction Details dataset
            logging.info("Processing Transaction Details dataset...")
            transactions_df = pd.read_csv('datasets/transaction_details.csv')
            transactions_df = self.preprocess_dataset(transactions_df, ['description'])
            transactions_df.to_csv(f'{self.processed_data_dir}/processed_transactions.csv', index=False)

            logging.info("All datasets processed successfully!")

        except Exception as e:
            logging.error(f"Error in preprocess_all_datasets: {str(e)}")

    def analyze_text_lengths(self, df, text_column):
        """Analyze text lengths for proper sequence length determination"""
        lengths = df[text_column].str.len()
        return {
            'mean': lengths.mean(),
            'median': lengths.median(),
            'std': lengths.std(),
            '95th_percentile': lengths.quantile(0.95),
            'max': lengths.max()
        }

def main():
    logging.info("Starting preprocessing pipeline...")
    
    preprocessor = DatasetPreprocessor()
    preprocessor.preprocess_all_datasets()
    
    # Analyze processed datasets
    logging.info("Analyzing processed datasets...")
    
    datasets = {
        'FAQs': ('processed_datasets/processed_faqs.csv', ['processed_question', 'processed_answer']),
        'Complaints': ('processed_datasets/processed_complaints.csv', ['processed_description']),
        'Assistance': ('processed_datasets/processed_assistance.csv', ['processed_query']),
        'Fraud Reports': ('processed_datasets/processed_fraud_reports.csv', ['processed_description']),
        'Transactions': ('processed_datasets/processed_transactions.csv', ['processed_description'])
    }
    
    for dataset_name, (file_path, columns) in datasets.items():
        try:
            df = pd.read_csv(file_path)
            for column in columns:
                stats = preprocessor.analyze_text_lengths(df, column)
                logging.info(f"\n{dataset_name} - {column} statistics:")
                for metric, value in stats.items():
                    logging.info(f"{metric}: {value:.2f}")
        except Exception as e:
            logging.error(f"Error analyzing {dataset_name}: {str(e)}")

if __name__ == "__main__":
    main()
