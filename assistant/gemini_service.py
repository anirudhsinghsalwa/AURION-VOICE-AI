import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

def get_gemini_response(message: str, history: list = None) -> str:
    """
    Sends a message to the Google Gemini API, including conversation history, and returns the response.
    Handles configuration and API call errors gracefully.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        error_msg = "GEMINI_API_KEY is missing. Please add it to your environment or .env file."
        logger.error(error_msg)
        return "I'm having trouble connecting to my intelligence system. Please configure the GEMINI_API_KEY environment variable."

    try:
        # Configure the Generative AI client
        genai.configure(api_key=api_key)

        # Define the system prompt to establish the AURION personality
        system_instruction = (
            "You are AURION, a smart, highly capable, real-time AI voice assistant SaaS. "
            "You are helpful, clean, and speak with a friendly, professional tone. "
            "When responding, keep your answers engaging, natural, and relatively concise (since they "
            "might be read aloud by the browser's Text-To-Speech system). "
            "However, if the user asks for code, detailed explanations, summaries, or complex reasoning, "
            "provide full, beautifully formatted Markdown answers. "
            "Always be direct and avoid unnecessary conversational filler."
        )

        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=system_instruction
        )

        # Reconstruct the conversation history into the format Gemini expects
        contents = []
        if history:
            # We limit history to the last 10 messages to keep request sizes manageable
            for turn in history[-10:]:
                role = "user" if turn.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [turn.get("content", "")]
                })

        # Append the new user message
        contents.append({
            "role": "user",
            "parts": [message]
        })

        # Generate content
        response = model.generate_content(contents)
        if response and response.text:
            return response.text.strip()
        else:
            return "I generated an empty response. Please try again."

    except Exception as e:
        logger.error(f"Error querying Gemini: {str(e)}", exc_info=True)
        return f"I ran into an issue communicating with my AI model. Details: {str(e)}"
