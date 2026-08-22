import os
from dotenv import load_dotenv
from google import genai

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY was not found.")
        exit()

    print("API key loaded successfully.")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents="Explain RAG in 2 simple sentences."
    )
    print("\nGemini response:\n")
    print(response.text)