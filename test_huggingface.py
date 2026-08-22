import os

from dotenv import load_dotenv
from huggingface_hub import InferenceClient


if __name__ == "__main__":
    load_dotenv()
    token = os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        print("ERROR: HUGGINGFACE_TOKEN was not found.")
        exit()

    print("Hugging Face token loaded successfully.")
    client = InferenceClient(
        api_key=token,
        provider="auto"
    )
    response = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=[
            {
                "role": "user",
                "content": "Explain RAG in two simple sentences."
            }
        ]
    )
    print("\nHugging Face response:\n")
    print(response.choices[0].message.content)