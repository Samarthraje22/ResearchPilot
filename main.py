from core.llm.factory import get_llm


def main():

    print("\n==============================")
    print("       ResearchPilot")
    print("==============================")

    llm = get_llm()

    print("\nLLM is ready!\n")

    response = llm.generate(
        "Explain RAG in one simple sentence."
    )

    print("Response:")
    print(response)


if __name__ == "__main__":
    main()