# Banking Chatbot with Gemini

A banking chatbot application that uses Google's Gemini model to provide intelligent responses to banking queries.

## Features

- Natural language understanding using Google's Gemini model
- User authentication system
- Chat history tracking
- Multi-language support
- Voice input and text-to-speech capabilities
- Responsive web interface

## Setup Instructions

1. Clone the repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with the following variables (use `.env.template` as a reference):
   ```
   SECRET_KEY=your-secret-key-here
   GEMINI_API_KEY=your-gemini-api-key-here
   ```
4. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
5. Run the application:
   ```
   python app.py
   ```
6. Access the application at `http://localhost:5000`

## Project Structure

- `app.py`: Main Flask application
- `chatbot_model.py`: Gemini-based chatbot implementation
- `intents.json`: Intent definitions and training patterns
- `response_templates.json`: Response templates for different intents
- `templates/`: HTML templates for the web interface
- `static/`: Static assets (CSS, JS, images)

## How It Works

1. The chatbot uses Google's Gemini model to understand user queries and determine the intent
2. Based on the identified intent, it generates contextually relevant responses
3. The conversation history is stored in a SQLite database
4. The web interface provides a user-friendly way to interact with the chatbot

## Extending the Chatbot

To add new intents:
1. Add new intent definitions to `intents.json`
2. Add corresponding response templates to `response_templates.json`
3. Restart the application

## License

MIT