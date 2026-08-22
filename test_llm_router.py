from core.llm.router import LLMRouter


def test_router():
    print("\n" + "=" * 70)
    print("       ResearchPilot - Intelligent Multi-LLM Router Test")
    print("=" * 70)

    router = LLMRouter(primary_provider="gemini")

    # 1. Test strategy selection
    p_name, fallbacks = router.select_provider("Explain quantum neural networks in simple terms.")
    print(f"[1] Provider selection for simple prompt: {p_name} (Fallbacks: {fallbacks})")
    assert p_name in ["gemini", "huggingface", "ollama"], "Invalid provider selection!"

    # 2. Test offline mode strategy
    p_offline, fallbacks_off = router.select_provider("Synthesize findings offline", mode="offline")
    print(f"[2] Offline mode provider selection: {p_offline} (Fallbacks: {fallbacks_off})")
    assert p_offline == "ollama", "Offline mode should select Ollama!"

    # 3. Test execution and generation with fallback mechanism
    print("\n[3] Generating response via LLMRouter...")
    response = router.generate("Explain retrieval augmented generation in one concise sentence.")
    print(f"\nResponse:\n{response}\n")
    assert len(response) > 10, "Router generated empty response!"

    print("[PASS] Multi-LLM Router test completed successfully!")


if __name__ == "__main__":
    test_router()
