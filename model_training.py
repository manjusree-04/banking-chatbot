# model_training.py
import torch
from transformers import BertTokenizer, BertForSequenceClassification
from torch.optim import AdamW  # Changed import location
from torch.utils.data import Dataset, DataLoader, random_split
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import json
import os
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training.log'),
        logging.StreamHandler()
    ]
)

class BankingDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

class BankingBERTModel:
    def __init__(self, model_path='models/banking_bert'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_path = model_path
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        self.label_encoders = {}
        self.max_len = 128
        self.batch_size = 32
        
    def prepare_data(self):
        logging.info("Loading and preparing datasets...")
        
        # Load all datasets
        datasets = {
            'faqs': pd.read_csv('processed_datasets/processed_faqs.csv'),
            'complaints': pd.read_csv('processed_datasets/processed_complaints.csv'),
            'assistance': pd.read_csv('processed_datasets/processed_assistance.csv'),
            'fraud_reports': pd.read_csv('processed_datasets/processed_fraud_reports.csv')
        }

        # Prepare training data
        training_data = []
        labels = []
        
        # Process FAQs
        logging.info("Processing FAQs dataset...")
        for _, row in datasets['faqs'].iterrows():
            training_data.append(row['processed_question'])
            labels.append(f"FAQ_{row['category']}")
            training_data.append(row['processed_answer'])
            labels.append(f"FAQ_ANSWER_{row['category']}")

        # Process Complaints
        logging.info("Processing Complaints dataset...")
        for _, row in datasets['complaints'].iterrows():
            training_data.append(row['processed_description'])
            labels.append(f"COMPLAINT_{row['type']}")

        # Process Assistance queries
        logging.info("Processing Assistance dataset...")
        for _, row in datasets['assistance'].iterrows():
            training_data.append(row['processed_query'])
            labels.append(f"ASSISTANCE_{row['type']}")

        # Process Fraud Reports
        logging.info("Processing Fraud Reports dataset...")
        for _, row in datasets['fraud_reports'].iterrows():
            training_data.append(row['processed_description'])
            labels.append(f"FRAUD_{row['fraud_type']}")

        # Encode labels
        self.label_encoder = LabelEncoder()
        encoded_labels = self.label_encoder.fit_transform(labels)

        # Save label encoder classes for inference
        self.save_label_encoder(self.label_encoder.classes_)

        # Create dataset
        dataset = BankingDataset(
            texts=training_data,
            labels=encoded_labels,
            tokenizer=self.tokenizer,
            max_len=self.max_len
        )

        # Split dataset
        train_size = int(0.8 * len(dataset))
        val_size = len(dataset) - train_size
        train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

        # Create data loaders
        self.train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=0  # Changed to 0 for Windows compatibility
        )
        
        self.val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=0  # Changed to 0 for Windows compatibility
        )

        return len(self.label_encoder.classes_)

    def save_label_encoder(self, classes):
        os.makedirs('models', exist_ok=True)
        with open('models/label_classes.json', 'w') as f:
            json.dump(classes.tolist(), f)

    def train(self, epochs=5):
        logging.info("Preparing model for training...")
        num_labels = self.prepare_data()
        
        # Initialize model
        model = BertForSequenceClassification.from_pretrained(
            'bert-base-uncased',
            num_labels=num_labels
        )
        model = model.to(self.device)

        # Initialize optimizer
        optimizer = AdamW(model.parameters(), lr=2e-5)
        
        # Training loop
        logging.info("Starting training...")
        best_accuracy = 0
        
        for epoch in range(epochs):
            logging.info(f"\nEpoch {epoch + 1}/{epochs}")
            model.train()
            total_loss = 0
            progress_bar = tqdm(self.train_loader, desc="Training")
            
            for batch in progress_bar:
                optimizer.zero_grad()
                
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )

                loss = outputs.loss
                total_loss += loss.item()
                
                loss.backward()
                optimizer.step()
                
                progress_bar.set_postfix({'loss': f"{loss.item():.4f}"})

            # Validation
            model.eval()
            val_accuracy = 0
            val_steps = 0
            
            logging.info("\nRunning validation...")
            with torch.no_grad():
                for batch in tqdm(self.val_loader, desc="Validation"):
                    input_ids = batch['input_ids'].to(self.device)
                    attention_mask = batch['attention_mask'].to(self.device)
                    labels = batch['labels'].to(self.device)

                    outputs = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask
                    )
                    
                    predictions = torch.argmax(outputs.logits, dim=1)
                    val_accuracy += (predictions == labels).sum().item()
                    val_steps += labels.size(0)

            accuracy = val_accuracy / val_steps
            logging.info(f"\nValidation Accuracy: {accuracy:.4f}")

            # Save best model
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                logging.info(f"Saving best model with accuracy: {accuracy:.4f}")
                model.save_pretrained(self.model_path)
                self.tokenizer.save_pretrained(self.model_path)

    def load_model(self):
        """Load the trained model for inference"""
        self.model = BertForSequenceClassification.from_pretrained(self.model_path)
        self.model.to(self.device)
        self.model.eval()
        
        # Load label classes
        with open('models/label_classes.json', 'r') as f:
            self.label_classes = json.load(f)

    def predict(self, text):
        """Make prediction for a single text input"""
        if not hasattr(self, 'model'):
            self.load_model()

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )

        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            prediction = torch.argmax(outputs.logits, dim=1)
            
        predicted_label = self.label_classes[prediction.item()]
        return predicted_label

def main():
    logging.info("Initializing Banking BERT Model Training...")
    
    # Create model trainer
    trainer = BankingBERTModel()
    
    # Train the model
    trainer.train(epochs=5)
    
    # Test prediction
    test_texts = [
        "How do I check my account balance?",
        "I noticed an unauthorized transaction on my account",
        "I need help with my credit card application",
        "My card was stolen and used for fraudulent purchases"
    ]
    
    logging.info("\nTesting model predictions:")
    for text in test_texts:
        prediction = trainer.predict(text)
        logging.info(f"\nInput: {text}")
        logging.info(f"Predicted category: {prediction}")

if __name__ == "__main__":
    main()
