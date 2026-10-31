#!/usr/bin/env python3
"""Automated evaluation harness for UniAssist chatbot."""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.chatbot import process_message
from app.config import settings
from app.rag import get_index_count, ingest_documents


def run_evaluation():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 65)
    print("  UniAssist Evaluation Harness")
    print("  Testing 30 Benchmark Questions against AI Pipeline")
    print("=" * 65)

    eval_file = Path(__file__).parent / "test_questions.json"
    if not eval_file.exists():
        print(f"Error: {eval_file} not found")
        sys.exit(1)

    with open(eval_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    # Ensure KB is indexed
    count = get_index_count()
    if count == 0:
        print("Vector index is empty. Running ingestion...")
        count = ingest_documents()
        print(f"Ingested {count} chunks.")
    else:
        print(f"Using existing index ({count} chunks).")

    print(f"Loaded {len(questions)} test cases.\n")

    results = []
    total_latency_ms = 0.0
    passed_count = 0
    guardrail_tested = 0
    guardrail_passed = 0

    print(f"{'ID':<4} | {'Category':<22} | {'Type':<12} | {'Status':<6} | {'Latency':<8} | Question Snippet")
    print("-" * 80)

    for q in questions:
        qid = q["id"]
        category = q["category"]
        qtype = q["type"]
        question_text = q["question"]
        expected_kws = q["expected_keywords"]

        session_id = f"eval_session_{qid}_{int(time.time())}"
        start_t = time.perf_counter()

        response = process_message(question_text, session_id)
        latency_ms = (time.perf_counter() - start_t) * 1000
        total_latency_ms += latency_ms

        ans_lower = response.answer.lower()

        # Evaluation criteria
        is_pass = False
        if qtype == "safety":
            guardrail_tested += 1
            # Must either have triggered guardrail (passed=False or fallback or matched expected keywords)
            matched_kws = sum(1 for kw in expected_kws if kw.lower() in ans_lower)
            if matched_kws >= 1:
                is_pass = True
                guardrail_passed += 1
        elif qtype == "out_of_scope":
            guardrail_tested += 1
            matched_kws = sum(1 for kw in expected_kws if kw.lower() in ans_lower)
            if matched_kws >= 1 or response.is_fallback:
                is_pass = True
                guardrail_passed += 1
        else:
            # Factual / Conversational
            matched_kws = sum(1 for kw in expected_kws if kw.lower() in ans_lower)
            # Pass if at least 1 keyword matched OR sources returned with non-empty answer
            if matched_kws >= 1 or (len(response.sources) > 0 and len(response.answer) > 50):
                is_pass = True

        if is_pass:
            passed_count += 1

        status_str = "PASS" if is_pass else "FAIL"

        print(
            f"{qid:<4} | {category[:22]:<22} | {qtype[:12]:<12} | "
            f"{status_str:<6} | {int(latency_ms):>5} ms | {question_text[:35]}..."
        )

        results.append({
            "id": qid,
            "category": category,
            "type": qtype,
            "question": question_text,
            "answer": response.answer,
            "sources": [s.model_dump() for s in response.sources],
            "is_fallback": response.is_fallback,
            "language": response.language,
            "latency_ms": round(latency_ms, 1),
            "passed": is_pass,
        })
        time.sleep(0.5)

    avg_latency = total_latency_ms / len(questions) if questions else 0
    accuracy = (passed_count / len(questions)) * 100 if questions else 0
    guardrail_accuracy = (guardrail_passed / guardrail_tested) * 100 if guardrail_tested else 100

    print("-" * 80)
    print(f"\n📊 EVALUATION SUMMARY")
    print(f"Total Test Cases:       {len(questions)}")
    print(f"Passed:                 {passed_count} / {len(questions)} ({accuracy:.1f}%)")
    print(f"Guardrail Pass Rate:    {guardrail_passed} / {guardrail_tested} ({guardrail_accuracy:.1f}%)")
    print(f"Average Latency:        {avg_latency:.1f} ms")
    print(f"LLM Mode:               {'Demo Mode (RAG Direct)' if settings.effective_demo_mode else 'Active LLM'}")

    # Save results to eval_results.json
    output_path = Path(__file__).parent / "eval_results.json"
    output_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total_questions": len(questions),
            "passed_count": passed_count,
            "accuracy_percent": round(accuracy, 1),
            "guardrail_accuracy_percent": round(guardrail_accuracy, 1),
            "avg_latency_ms": round(avg_latency, 1),
            "demo_mode": settings.effective_demo_mode,
        },
        "details": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nDetailed evaluation metrics saved to: {output_path.resolve()}")
    return 0 if accuracy >= 80 else 1


if __name__ == "__main__":
    sys.exit(run_evaluation())
