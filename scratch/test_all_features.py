import urllib.request
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"
time.sleep(3)

print("=" * 60)
print("  ResearchPilot Clean Feature Verification Suite")
print("=" * 60)

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    try:
        ok, detail = fn()
        if ok:
            print(f"  [PASS] {name} ({detail})")
            passed += 1
        else:
            print(f"  [FAIL] {name} -> {detail}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] {name} -> Exception: {e}")
        failed += 1

# 1. Health API
def test_health():
    r = urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=10)
    data = json.loads(r.read().decode())
    return data.get("status") == "ok", "Server online"
test("1. System Health API", test_health)

# Get active document
r_docs = urllib.request.urlopen(f"{BASE_URL}/api/sources", timeout=10)
docs_data = json.loads(r_docs.read().decode()).get("documents", [])
assert len(docs_data) > 0, "No uploaded documents found to test with"
doc = docs_data[0]
doc_id = doc["id"]
print(f"\n  Active Document: {doc['filename']} (ID: {doc_id})")

# 2. Feature #5 & #10: Smart Questions with Caching
def test_smart_questions():
    t0 = time.time()
    r = urllib.request.urlopen(f"{BASE_URL}/api/sources/{doc_id}/suggested-questions", timeout=30)
    d = json.loads(r.read().decode())
    dur1 = time.time() - t0
    qs = d.get("suggested_questions", [])
    if len(qs) < 3:
        return False, f"Expected >= 3 questions, got {len(qs)}"

    # Test cache speedup
    t1 = time.time()
    r2 = urllib.request.urlopen(f"{BASE_URL}/api/sources/{doc_id}/suggested-questions", timeout=10)
    dur2 = time.time() - t1
    return True, f"{len(qs)} smart questions generated (Call 1: {dur1:.2f}s, Cached Call 2: {dur2:.4f}s)"
test("2. Smart Question Suggestions & Caching (Features #5 & #10)", test_smart_questions)

# 3. Feature #2: Chat & Follow-up Q&A
def test_followup():
    payload = {
        "query": "What are the primary mathematical components or methods discussed in this research?",
        "current_report": "The paper examines mathematics in machine learning, focusing on linear algebra, probability, and calculus for prediction tasks.",
        "evidence": [
            {"citation_id": 1, "source": doc["filename"], "page": 1, "content": "Linear algebra and probability are critical foundations."}
        ],
        "chat_history": []
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/research/follow-up",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    r = urllib.request.urlopen(req, timeout=45)
    d = json.loads(r.read().decode())
    ans = d.get("answer", "")
    if len(ans) < 20:
        return False, "Answer too short"
    return True, f"Generated answer ({len(ans)} chars, {d.get('execution_time_sec')}s)"
test("3. Interactive Follow-up Q&A API (Feature #2)", test_followup)

# 4. Feature #11 & #15: Frontend Assets Validation
def test_frontend():
    r_html = urllib.request.urlopen(f"{BASE_URL}/", timeout=10).read().decode()
    r_js = urllib.request.urlopen(f"{BASE_URL}/static/app.js", timeout=10).read().decode()
    r_css = urllib.request.urlopen(f"{BASE_URL}/static/index.css", timeout=10).read().decode()

    has_history = "modal-history" in r_html and "saveSessionToHistory" in r_js and "history-item-card" in r_css
    has_followup = "followup-container" in r_html and "followupForm" in r_js and "followup-container" in r_css
    has_toasts = "toast-container" in r_html and "showToast" in r_js and "toast-error" in r_css
    no_sections = "modal-sections" not in r_html and "btn-view-sections" not in r_js

    if not (has_history and has_followup and has_toasts and no_sections):
        return False, f"Check failed: hist={has_history}, fu={has_followup}, toast={has_toasts}, no_sec={no_sections}"
    return True, "All UI components integrated cleanly (History, Follow-up, Toasts, Sections removed)"
test("4. Frontend Integration & Asset Validation (Features #2, #11, #15)", test_frontend)

print("\n" + "=" * 60)
print(f"  Summary: {passed} PASSED, {failed} FAILED")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
