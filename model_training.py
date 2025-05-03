import json
import random
import logging
import os
import google.generativeai as genai
from dotenv import load_dotenv

class BankingChatbot:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configure Google Generative AI with API key
        # Replace this with your actual API key if .env isn't working
        api_key = "AIzaSyAe1e8xzYwlCa-5zBRlNjDH02LAqRW-gX0"  # Replace with your actual API key
        
        # Configure the Gemini API
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logging.info("Gemini model initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing Gemini model: {str(e)}")
            self.model = None
        
        # Load intents
        self.intents = None
        self.load_intents()
        
        # Initialize conversation context
        self.context = {
            "current_intent": None,
            "user_data": {},
            "conversation_history": []
        }

    def load_intents(self):
        with open('intents.json', 'r') as f:
            self.intents = json.load(f)
            logging.info("Intents loaded successfully")

    def train(self):
        """
        No traditional training needed for Gemini model.
        This method is kept for compatibility with the existing code.
        """
        logging.info("Gemini model doesn't require traditional training.")
        return

    def load_model(self):
        """
        No model loading needed for Gemini model.
        This method is kept for compatibility with the existing code.
        """
        logging.info("Gemini model is already initialized.")
        return

    def get_intent(self, text):
        """Use Gemini to determine the intent of the user's message"""
        if not self.model:
            logging.error("Gemini model not initialized")
            return "error", 0.0
        
        # Create a prompt for intent classification
        intent_options = ", ".join([f"'{intent['tag']}'" for intent in self.intents['intents']])
        prompt = f"""
        Classify the following user message into one of these intents: {intent_options}.
        
        User message: "{text}"
        
        Return only the intent name without any additional text or explanation.
        """
        
        try:
            response = self.model.generate_content(prompt)
            predicted_intent = response.text.strip().replace("'", "").replace('"', '')
            
            # Validate that the predicted intent exists in our intents
            valid_intents = [intent['tag'] for intent in self.intents['intents']]
            if predicted_intent in valid_intents:
                return predicted_intent, 0.9  # Confidence score is estimated
            else:
                # If Gemini returns an invalid intent, use a fallback
                logging.warning(f"Gemini returned invalid intent: {predicted_intent}")
                return "greeting", 0.5
                
        except Exception as e:
            logging.error(f"Error getting intent from Gemini: {str(e)}")
            return "error", 0.0

    def generate_response(self, intent_tag, user_message):
        """Generate a contextual response using Gemini"""
        if not self.model:
            logging.error("Gemini model not initialized")
            return "I'm sorry, I'm having trouble processing your request right now."
        
        # Get intent-specific response templates
        templates = []
        for intent in self.intents['intents']:
            if intent['tag'] == intent_tag:
                templates = intent['responses']
                break
        
        if not templates:
            return "I'm not sure how to respond to that. Could you please rephrase?"
        
        # Create context from conversation history
        conversation_context = "\n".join([
            f"User: {exchange['user']}\nBot: {exchange['bot']}"
            for exchange in self.context["conversation_history"][-3:]  # Last 3 exchanges
        ])
        
        # Create a prompt for response generation
        prompt = f"""
        You are an AI banking assistant. Generate a helpful, friendly response to the user's message.
        
        Intent: {intent_tag}
        
        Previous conversation:
        {conversation_context}
        
        User message: "{user_message}"
        
        Response templates for this intent:
        {templates}
        
        Generate a response that follows the style of the templates but is personalized to the user's specific query.
        """
        
        try:
            response = self.model.generate_content(prompt)
            generated_response = response.text.strip()
            
            # Customize response based on context and user data
            if intent_tag == "balance_inquiry" and "balance" in self.context["user_data"]:
                generated_response = generated_response.replace("[AMOUNT]", str(self.context["user_data"]["balance"]))
            
            elif intent_tag == "transaction_history" and "transactions" in self.context["user_data"]:
                generated_response = generated_response.replace("[TRANSACTIONS]", str(self.context["user_data"]["transactions"]))
            
            return generated_response
            
        except Exception as e:
            logging.error(f"Error generating response with Gemini: {str(e)}")
            return random.choice(templates)

    def update_context(self, intent_tag, user_message, bot_response):
        """Update conversation context with new exchange"""
        self.context["current_intent"] = intent_tag
        self.context["conversation_history"].append({
            "user": user_message,
            "bot": bot_response,
            "intent": intent_tag
        })
        
        # Limit conversation history to last 5 exchanges
        if len(self.context["conversation_history"]) > 5:
            self.context["conversation_history"] = self.context["conversation_history"][-5:]

    def predict(self, text):
        """Process user input and generate a response"""
        try:
            # Get intent using Gemini
            predicted_tag, confidence = self.get_intent(text)
            
            # Generate response using Gemini
            response = self.generate_response(predicted_tag, text)
            
            # Update conversation context
            self.update_context(predicted_tag, text, response)

            return predicted_tag, confidence, response

        except Exception as e:
            logging.error(f"Error in prediction: {str(e)}")
            return "error", 0.0, "I'm sorry, I encountered an error. Please try again."

    def set_user_data(self, data):
        """Set user-specific data for contextual responses"""
        self.context["user_data"].update(data)
# Add this at the end of the file
if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create an instance of the chatbot
    chatbot = BankingChatbot()
    
    # Test the chatbot with some example queries
    test_queries = [
        "Hello there",
        "What's my account balance?",
        "I want to transfer some money",
        "Show me my recent transactions"
    ]
    
    print("Testing Banking Chatbot with Gemini model:")
    print("-----------------------------------------")
    
    for query in test_queries:
        print(f"\nUser: {query}")
        intent, confidence, response = chatbot.predict(query)
        print(f"Intent: {intent} (confidence: {confidence:.2f})")
        print(f"Bot: {response}")
    
    print("\nTest complete!")
