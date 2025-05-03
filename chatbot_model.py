import json
import random
import logging
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

class BankingChatbot:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Load intents
        self.intents = None
        self.load_intents()
        
        # Initialize user accounts data (in a real system, this would come from a database)
        self.accounts = {
            "checking": {
                "account_number": "1234567890",
                "balance": 1250.75,
                "transactions": [
                    {"date": "2025-05-01", "description": "Grocery Store", "amount": -65.42, "id": "T12345"},
                    {"date": "2025-05-02", "description": "Salary Deposit", "amount": 2500.00, "id": "T12346"},
                    {"date": "2025-05-02", "description": "Rent Payment", "amount": -1200.00, "id": "T12347"},
                    {"date": "2025-04-28", "description": "Restaurant", "amount": -45.80, "id": "T12348"},
                    {"date": "2025-04-25", "description": "Gas Station", "amount": -35.50, "id": "T12349"}
                ]
            },
            "savings": {
                "account_number": "0987654321",
                "balance": 5432.10,
                "transactions": [
                    {"date": "2025-05-01", "description": "Interest Payment", "amount": 12.33, "id": "T22345"},
                    {"date": "2025-04-15", "description": "Transfer from Checking", "amount": 500.00, "id": "T22346"},
                    {"date": "2025-04-01", "description": "Interest Payment", "amount": 11.98, "id": "T22347"}
                ]
            }
        }
        
        # Initialize conversation context
        self.context = {
            "current_intent": None,
            "active_account": "checking",  # Default account
            "mentioned_entities": {},
            "conversation_state": "initial",  # Can be: initial, awaiting_account, awaiting_amount, etc.
            "pending_actions": {},
            "conversation_history": []
        }
        
        logging.info("Enhanced banking chatbot initialized successfully")

    def load_intents(self):
        try:
            with open('intents.json', 'r') as f:
                self.intents = json.load(f)
            logging.info("Intents loaded successfully")
        except Exception as e:
            logging.error(f"Error loading intents: {str(e)}")
            # Create default intents if file not found
            self.intents = {
                "intents": [
                    {
                        "tag": "greeting",
                        "patterns": ["Hi", "Hello", "Hey", "Good morning"],
                        "responses": ["Hello! How can I assist you with your banking needs today?"]
                    },
                    {
                        "tag": "balance_inquiry",
                        "patterns": ["What's my balance", "How much money do I have"],
                        "responses": ["Your current balance is [AMOUNT]."]
                    },
                    {
                        "tag": "transfer_money",
                        "patterns": ["I want to transfer money", "Send money"],
                        "responses": ["I can help you transfer money."]
                    },
                    {
                        "tag": "transaction_history",
                        "patterns": ["Show my transactions", "Transaction history"],
                        "responses": ["Here are your recent transactions: [TRANSACTIONS]"]
                    }
                ]
            }

    def extract_entities(self, text):
        """Extract entities like dates, amounts, account types from text"""
        text = text.lower()
        entities = {}
        
        # Extract account types
        account_types = ["checking", "savings"]
        for account in account_types:
            if account in text:
                entities["account_type"] = account
        
        # Extract transaction IDs
        transaction_id_pattern = r'(?:transaction|id|#)\s*([t#]?\d{5,})'
        match = re.search(transaction_id_pattern, text, re.IGNORECASE)
        if match:
            entities["transaction_id"] = match.group(1).upper()
            if not entities["transaction_id"].startswith("T"):
                entities["transaction_id"] = "T" + entities["transaction_id"].lstrip("#T")
        
        # Extract dates
        # Direct date mentions
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YYYY
            r'(\d{4}-\d{1,2}-\d{1,2})'      # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(1)
                    if '/' in date_str:
                        month, day, year = date_str.split('/')
                        if len(year) == 2:
                            year = '20' + year
                        entities["date"] = f"{year}-{int(month):02d}-{int(day):02d}"
                    else:
                        entities["date"] = date_str
                except:
                    pass
        
        # Relative date mentions
        today = datetime.now()
        if "today" in text:
            entities["date"] = today.strftime("%Y-%m-%d")
        elif "yesterday" in text:
            yesterday = today - timedelta(days=1)
            entities["date"] = yesterday.strftime("%Y-%m-%d")
        elif "this week" in text:
            entities["date_range"] = {
                "start": (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d"),
                "end": today.strftime("%Y-%m-%d")
            }
        elif "last week" in text:
            start = today - timedelta(days=today.weekday() + 7)
            end = start + timedelta(days=6)
            entities["date_range"] = {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d")
            }
        elif "this month" in text:
            entities["date_range"] = {
                "start": today.strftime("%Y-%m-01"),
                "end": today.strftime("%Y-%m-%d")
            }
        elif "last month" in text:
            last_month = today.replace(day=1) - timedelta(days=1)
            start = last_month.replace(day=1)
            entities["date_range"] = {
                "start": start.strftime("%Y-%m-%d"),
                "end": last_month.strftime("%Y-%m-%d")
            }
        
        # Extract amounts
        amount_patterns = [
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*dollars'  # 1,234.56 dollars
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    entities["amount"] = float(amount_str)
                except:
                    pass
        
        # Extract recipient information for transfers
        if "to " in text and " account" in text:
            recipient_pattern = r'to\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)\s+account'
            match = re.search(recipient_pattern, text)
            if match:
                entities["recipient"] = match.group(1).strip()
        
        return entities

    def get_intent_and_entities(self, text):
        """Determine intent and extract entities from user message"""
        # Extract entities first
        entities = self.extract_entities(text)
        
        # Basic intent detection
        text_lower = text.lower()
        
        # Check for follow-up intents based on conversation state
        if self.context["conversation_state"] == "awaiting_account":
            if any(acc in text_lower for acc in ["checking", "savings"]):
                return "account_selection", 0.9, entities
        
        elif self.context["conversation_state"] == "awaiting_amount":
            if "amount" in entities or any(word in text_lower for word in ["dollars", "$"]):
                return "amount_specification", 0.9, entities
        
        elif self.context["conversation_state"] == "awaiting_confirmation":
            if any(word in text_lower for word in ["yes", "confirm", "proceed", "ok", "sure"]):
                return "confirmation_yes", 0.9, entities
            elif any(word in text_lower for word in ["no", "cancel", "stop", "don't"]):
                return "confirmation_no", 0.9, entities
        
        # Check for specific transaction queries
        if "transaction" in text_lower and any(id_word in text_lower for id_word in ["id", "#", "number"]):
            return "specific_transaction", 0.9, entities
        
        # Check for date-specific transaction queries
        if ("transactions" in text_lower or "spending" in text_lower) and ("date" in entities or "date_range" in entities):
            return "date_transactions", 0.9, entities
        
        # Check for account-specific queries
        if "account" in text_lower and any(acc in text_lower for acc in ["checking", "savings"]):
            if "balance" in text_lower:
                return "account_balance", 0.9, entities
            elif "transactions" in text_lower:
                return "account_transactions", 0.9, entities
        
        # Standard intent detection
        if any(word in text_lower for word in ["hi", "hello", "hey", "good morning", "good afternoon"]):
            return "greeting", 0.9, entities
            
        if any(word in text_lower for word in ["balance", "how much", "money", "available"]):
            return "balance_inquiry", 0.8, entities
            
        if any(word in text_lower for word in ["transfer", "send money", "payment", "pay"]):
            return "transfer_money", 0.8, entities
            
        if any(word in text_lower for word in ["transactions", "history", "recent", "spending", "purchases"]):
            return "transaction_history", 0.8, entities
            
        # Default to greeting
        return "greeting", 0.5, entities

    def format_transaction(self, transaction):
        """Format a transaction for display"""
        sign = "+" if transaction["amount"] > 0 else ""
        return f"{transaction['date']} | {transaction['description']} | {sign}${abs(transaction['amount']):.2f} | ID: {transaction['id']}"

    def get_account_balance(self, account_type=None):
        """Get balance for the specified account or active account"""
        if not account_type:
            account_type = self.context["active_account"]
        
        if account_type in self.accounts:
            return self.accounts[account_type]["balance"]
        return None

    def get_transactions(self, account_type=None, date=None, date_range=None, transaction_id=None, limit=5):
        """Get transactions based on filters"""
        if not account_type:
            account_type = self.context["active_account"]
        
        if account_type not in self.accounts:
            return []
        
        transactions = self.accounts[account_type]["transactions"]
        
        # Filter by transaction ID
        if transaction_id:
            return [t for t in transactions if t["id"] == transaction_id]
        
        # Filter by date
        if date:
            transactions = [t for t in transactions if t["date"] == date]
        
        # Filter by date range
        if date_range:
            transactions = [t for t in transactions if date_range["start"] <= t["date"] <= date_range["end"]]
        
        # Sort by date (newest first)
        transactions = sorted(transactions, key=lambda t: t["date"], reverse=True)
        
        # Limit number of transactions
        return transactions[:limit]

    def update_context(self, intent, entities, user_message, bot_response):
        """Update conversation context with new information"""
        # Update current intent
        self.context["current_intent"] = intent
        
        # Update mentioned entities
        self.context["mentioned_entities"].update(entities)
        
        # Update active account if specified
        if "account_type" in entities:
            self.context["active_account"] = entities["account_type"]
        
        # Update conversation state based on intent
        if intent == "transfer_money":
            if "amount" in entities and "recipient" in entities:
                self.context["conversation_state"] = "awaiting_confirmation"
                self.context["pending_actions"] = {
                    "type": "transfer",
                    "amount": entities["amount"],
                    "recipient": entities["recipient"],
                    "from_account": self.context["active_account"]
                }
            elif "amount" in entities:
                self.context["conversation_state"] = "awaiting_recipient"
                self.context["pending_actions"] = {
                    "type": "transfer",
                    "amount": entities["amount"]
                }
            elif "recipient" in entities:
                self.context["conversation_state"] = "awaiting_amount"
                self.context["pending_actions"] = {
                    "type": "transfer",
                    "recipient": entities["recipient"]
                }
            else:
                self.context["conversation_state"] = "awaiting_details"
        
        elif intent == "confirmation_yes":
            if self.context["pending_actions"].get("type") == "transfer":
                self.context["conversation_state"] = "transfer_completed"
            else:
                self.context["conversation_state"] = "initial"
        
        elif intent == "confirmation_no":
            self.context["conversation_state"] = "initial"
            self.context["pending_actions"] = {}
        
        else:
            self.context["conversation_state"] = "initial"
        
        # Add to conversation history
        self.context["conversation_history"].append({
            "user": user_message,
            "bot": bot_response,
            "intent": intent,
            "entities": entities
        })
        
        # Limit conversation history to last 10 exchanges
        if len(self.context["conversation_history"]) > 10:
            self.context["conversation_history"] = self.context["conversation_history"][-10:]

    def generate_response(self, intent, entities, user_message):
        """Generate a dynamic response based on intent, entities, and context"""
        
        # Handle greeting intent
        if intent == "greeting":
            greeting_responses = [
                "Hello! How can I assist you with your banking needs today?",
                "Hi there! How may I help you with your accounts?",
                "Welcome back! What would you like to do with your banking today?"
            ]
            return random.choice(greeting_responses)
        
        # Handle balance inquiry intent
        elif intent == "balance_inquiry" or intent == "account_balance":
            account_type = entities.get("account_type", self.context["active_account"])
            balance = self.get_account_balance(account_type)
            
            if balance is not None:
                responses = [
                    f"Your {account_type} account balance is ${balance:.2f}. Would you like to see your recent transactions?",
                    f"The balance in your {account_type} account is ${balance:.2f}. Is there anything else you'd like to know?",
                    f"You have ${balance:.2f} in your {account_type} account. Can I help you with anything else?"
                ]
                return random.choice(responses)
            else:
                return f"I couldn't find information for your {account_type} account."
        
        # Handle transaction history intent
        elif intent == "transaction_history" or intent == "account_transactions":
            account_type = entities.get("account_type", self.context["active_account"])
            transactions = self.get_transactions(account_type)
            
            if transactions:
                transactions_text = "\n- " + "\n- ".join([self.format_transaction(t) for t in transactions])
                return f"Here are your recent transactions from your {account_type} account:{transactions_text}"
            else:
                return f"I couldn't find any recent transactions for your {account_type} account."
        
        # Handle date-specific transaction queries
        elif intent == "date_transactions":
            account_type = entities.get("account_type", self.context["active_account"])
            
            if "date" in entities:
                date = entities["date"]
                transactions = self.get_transactions(account_type, date=date)
                
                if transactions:
                    transactions_text = "\n- " + "\n- ".join([self.format_transaction(t) for t in transactions])
                    return f"Here are your transactions from {date} for your {account_type} account:{transactions_text}"
                else:
                    return f"I couldn't find any transactions on {date} for your {account_type} account."
            
            elif "date_range" in entities:
                date_range = entities["date_range"]
                transactions = self.get_transactions(account_type, date_range=date_range)
                
                if transactions:
                    transactions_text = "\n- " + "\n- ".join([self.format_transaction(t) for t in transactions])
                    return f"Here are your transactions from {date_range['start']} to {date_range['end']} for your {account_type} account:{transactions_text}"
                else:
                    return f"I couldn't find any transactions between {date_range['start']} and {date_range['end']} for your {account_type} account."
        
        # Handle specific transaction queries
        elif intent == "specific_transaction":
            if "transaction_id" in entities:
                transaction_id = entities["transaction_id"]
                account_type = entities.get("account_type", self.context["active_account"])
                
                transactions = self.get_transactions(account_type, transaction_id=transaction_id)
                
                if transactions:
                    transaction = transactions[0]
                    return f"Transaction {transaction_id}: {transaction['date']} | {transaction['description']} | ${abs(transaction['amount']):.2f} | {'Credit' if transaction['amount'] > 0 else 'Debit'}"
                else:
                    return f"I couldn't find transaction {transaction_id} in your {account_type} account."
        
        # Handle transfer money intent
        elif intent == "transfer_money":
            if "amount" in entities and "recipient" in entities:
                amount = entities["amount"]
                recipient = entities["recipient"]
                account_type = entities.get("account_type", self.context["active_account"])
                
                return f"I'll set up a transfer of ${amount:.2f} from your {account_type} account to {recipient}'s account. Would you like to proceed?"
            
            elif "amount" in entities:
                amount = entities["amount"]
                return f"I'll help you transfer ${amount:.2f}. Who would you like to send it to?"
            
            elif "recipient" in entities:
                recipient = entities["recipient"]
                return f"How much would you like to transfer to {recipient}?"
            
            else:
                return "I can help you transfer money. Please provide the recipient's name and the amount you'd like to transfer."
        
        # Handle account selection
        elif intent == "account_selection":
            if "account_type" in entities:
                account_type = entities["account_type"]
                self.context["active_account"] = account_type
                
                if self.context["pending_actions"].get("type") == "transfer":
                    self.context["pending_actions"]["from_account"] = account_type
                    
                    if "amount" in self.context["pending_actions"] and "recipient" in self.context["pending_actions"]:
                        amount = self.context["pending_actions"]["amount"]
                        recipient = self.context["pending_actions"]["recipient"]
                        return f"I'll set up a transfer of ${amount:.2f} from your {account_type} account to {recipient}'s account. Would you like to proceed?"
                    
                    elif "amount" in self.context["pending_actions"]:
                        amount = self.context["pending_actions"]["amount"]
                        return f"I'll help you transfer ${amount:.2f} from your {account_type} account. Who would you like to send it to?"
                    
                    elif "recipient" in self.context["pending_actions"]:
                        recipient = self.context["pending_actions"]["recipient"]
                        return f"How much would you like to transfer to {recipient} from your {account_type} account?"
                
                return f"I've switched to your {account_type} account. How can I help you with this account?"
        
        # Handle amount specification
        elif intent == "amount_specification":
            if "amount" in entities:
                amount = entities["amount"]
                self.context["pending_actions"]["amount"] = amount
                
                if "recipient" in self.context["pending_actions"]:
                    recipient = self.context["pending_actions"]["recipient"]
                    account_type = self.context["active_account"]
                    return f"I'll set up a transfer of ${amount:.2f} from your {account_type} account to {recipient}'s account. Would you like to proceed?"
                
                return f"I'll help you transfer ${amount:.2f}. Who would you like to send it to?"
        
        # Handle confirmation
        elif intent == "confirmation_yes":
            if self.context["pending_actions"].get("type") == "transfer":
                amount = self.context["pending_actions"].get("amount", 0)
                recipient = self.context["pending_actions"].get("recipient", "the recipient")
                account_type = self.context["pending_actions"].get("from_account", self.context["active_account"])
                
                # In a real system, this would actually perform the transfer
                return f"I've transferred ${amount:.2f} from your {account_type} account to {recipient}'s account. The transaction has been completed successfully."
        
        elif intent == "confirmation_no":
            return "I've cancelled that request. Is there something else I can help you with?"
        
        # Fallback response
        return "I'm not sure how to respond to that. Could you please rephrase your question?"

    def predict(self, text):
        """Process user input and generate a response"""
        try:
            # Get intent and entities
            intent, confidence, entities = self.get_intent_and_entities(text)
            
            # Generate response
            response = self.generate_response(intent, entities, text)
            
            # Update conversation context
            self.update_context(intent, entities, text, response)

            return intent, confidence, response

        except Exception as e:
            logging.error(f"Error in prediction: {str(e)}")
            return "error", 0.0, "I'm sorry, I encountered an error. Please try again."

    def set_user_data(self, data):
        """Set user-specific data"""
        if "accounts" in data:
            self.accounts.update(data["accounts"])
