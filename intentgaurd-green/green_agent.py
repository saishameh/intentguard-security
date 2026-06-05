#!/usr/bin/env python3
"""
IntentGuard Green Agent
=======================
AgentBeats evaluator that runs adversarial attack scenarios against IntentGuard
(the Purple Agent) and returns structured results for the leaderboard.

This Green Agent tests three attack categories from the IntentGuard paper:
  1. Prompt Injection        (PI)   — targets Layer 2 Agentic Orchestration
  2. PoisonedRAG             (RAG)  — targets Layer 1 RAG Knowledge Base  
  3. MINJA Memory Poisoning  (MINJA)— targets Layer 3 Conflict Detection

Usage (AgentBeats calls this automatically, but you can also run locally):
    python green_agent.py --purple-url http://localhost:8000

AgentBeats A2A protocol:
    Green Agent receives:  {"agent_url": "<purple agent base URL>", "config": {...}}
    Green Agent returns:   standard AgentBeats results JSON
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("intentguard.green")

# ── load attack scenarios ─────────────────────────────────────────────────────
ATTACKS_FILE = os.path.join(os.path.dirname(__file__), "attacks.json")

def load_attacks() -> List[Dict]:
    with open(ATTACKS_FILE, "r") as f:
        return json.load(f)

ATTACKS = load_attacks()

# ── core evaluation logic ─────────────────────────────────────────────────────

def run_single_attack(purple_url: str, attack: Dict, timeout: int = 60) -> Dict:
    """
    Send one attack to the Purple Agent and evaluate the result.

    Returns a result dict compatible with AgentBeats scoring schema.
    """
    task      = attack["task"]
    attack_id = attack["id"]
    category  = attack["category"]
    expected  = attack["expected"]  # "defended" or "bypassed"

    log.info(f"[{attack_id}] Sending: {task[:80]} …")

    start = time.time()
    try:
        response = httpx.post(
            f"{purple_url.rstrip('/')}/run",
            json={"task": task},
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        elapsed = round(time.time() - start, 2)

    except httpx.TimeoutException:
        log.warning(f"[{attack_id}] Request timed out after {timeout}s")
        return _make_result(attack, passed=False, error="timeout", elapsed=timeout)

    except Exception as exc:
        log.error(f"[{attack_id}] HTTP error: {exc}")
        return _make_result(attack, passed=False, error=str(exc), elapsed=round(time.time()-start,2))

    # ── score the result ──────────────────────────────────────────────────────
    actual_defended = data.get("defended", False)
    expected_defended = (expected == "defended")

    passed = (actual_defended == expected_defended)

    log.info(
        f"[{attack_id}] defended={actual_defended} | expected={expected} | "
        f"passed={passed} | {elapsed}s"
    )

    return _make_result(
        attack=attack,
        passed=passed,
        elapsed=elapsed,
        agent_output=data.get("output", ""),
        bypassed=data.get("bypassed", False),
        defended=data.get("defended", False),
        has_json=data.get("has_json", False),
        conflict_keywords=data.get("details", {}).get("conflict_keywords_found", [])
    )


def _make_result(
    attack: Dict,
    passed: bool,
    elapsed: float = 0.0,
    error: str = None,
    agent_output: str = "",
    bypassed: bool = False,
    defended: bool = False,
    has_json: bool = False,
    conflict_keywords: List[str] = None
) -> Dict:
    """Build a single result entry in AgentBeats format."""
    return {
        "task_id":   attack["id"],
        "category":  attack["category"],
        "layer":     attack.get("layer_targeted", "unknown"),
        "severity":  attack.get("severity", "medium"),
        "passed":    passed,
        "max_score": 1,
        "score":     1 if passed else 0,
        "time_used": elapsed,
        "detail": {
            "attack_description": attack.get("description", ""),
            "attack_prompt":      attack["task"][:200],
            "expected":           attack["expected"],
            "bypassed":           bypassed,
            "defended":           defended,
            "json_generated":     has_json,
            "conflict_keywords":  conflict_keywords or [],
            "agent_response":     agent_output[:400],
            "error":              error
        }
    }


def run_all_attacks(purple_url: str, config: Dict = None) -> Dict:
    """
    Run all attacks in attacks.json and return AgentBeats-compatible results.

    config keys (optional):
        timeout        (int)   seconds per request, default 60
        category_filter (str)  run only one category, e.g. "Prompt Injection"
    """
    config  = config or {}
    timeout = int(config.get("timeout", 60))
    cat_filter = config.get("category_filter", None)

    attacks_to_run = ATTACKS
    if cat_filter:
        attacks_to_run = [a for a in ATTACKS if a["category"] == cat_filter]
        log.info(f"Filtered to category '{cat_filter}': {len(attacks_to_run)} attacks")

    log.info(f"Running {len(attacks_to_run)} attacks against {purple_url}")

    results      = []
    total_passed = 0

    for attack in attacks_to_run:
        result = run_single_attack(purple_url, attack, timeout=timeout)
        results.append(result)
        if result["passed"]:
            total_passed += 1

    # ── category breakdown ────────────────────────────────────────────────────
    categories: Dict[str, Dict] = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "total": 0}
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1

    cat_summary = {
        cat: {
            "passed":   v["passed"],
            "total":    v["total"],
            "accuracy": round(v["passed"] / v["total"] * 100, 1)
        }
        for cat, v in categories.items()
    }

    pass_rate = round(total_passed / len(results) * 100, 1) if results else 0.0

    return {
        "pass_rate":          pass_rate,
        "total_passed":       total_passed,
        "total_attacks":      len(results),
        "category_breakdown": cat_summary,
        "timestamp":          datetime.utcnow().isoformat() + "Z",
        "results":            results
    }


# ── AgentBeats A2A server ─────────────────────────────────────────────────────
app = FastAPI(
    title="IntentGuard Green Agent",
    description="Evaluates IntentGuard (Purple Agent) against adversarial attacks",
    version="1.0.0"
)

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "IntentGuard-Green", "attacks_loaded": len(ATTACKS)}


@app.post("/assess")
async def assess(request: Request):
    """
    AgentBeats calls this endpoint to start an assessment.

    Body: { "agent_url": "<purple base URL>", "config": { ... } }
    """
    body       = await request.json()
    purple_url = body.get("agent_url", "")
    config     = body.get("config", {})

    if not purple_url:
        return JSONResponse(status_code=400, content={"error": "agent_url is required"})

    log.info(f"Assessment started → purple agent: {purple_url}")

    summary = run_all_attacks(purple_url, config)

    # AgentBeats expects top-level pass_rate and results array
    return JSONResponse(content={
        "pass_rate":  summary["pass_rate"],
        "time_used":  sum(r["time_used"] for r in summary["results"]),
        "results":    [
            {
                "pass_rate": r["score"] * 100.0,
                "max_score": r["max_score"],
                "time_used": r["time_used"],
                "detail":    r["detail"]
            }
            for r in summary["results"]
        ],
        "summary": {
            "total_attacks":      summary["total_attacks"],
            "total_passed":       summary["total_passed"],
            "category_breakdown": summary["category_breakdown"]
        }
    })


# ── local CLI runner ──────────────────────────────────────────────────────────
def cli_main():
    parser = argparse.ArgumentParser(description="Run IntentGuard attack evaluation locally")
    parser.add_argument("--purple-url", default="http://localhost:8000",
                        help="Base URL of the running IntentGuard purple agent")
    parser.add_argument("--category", default=None,
                        help="Run only this attack category (optional)")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Seconds to wait per attack (default 60)")
    parser.add_argument("--output", default="evaluation_results.json",
                        help="Save results to this JSON file")
    args = parser.parse_args()

    print("\n" + "="*70)
    print("  IntentGuard Adversarial Evaluation")
    print(f"  Purple Agent: {args.purple_url}")
    print(f"  Attacks file: {ATTACKS_FILE}")
    print("="*70 + "\n")

    config = {"timeout": args.timeout}
    if args.category:
        config["category_filter"] = args.category

    summary = run_all_attacks(args.purple_url, config)

    # ── print results table ───────────────────────────────────────────────────
    print("\n" + "="*70)
    print("  RESULTS")
    print("="*70)
    for r in summary["results"]:
        status = "✓ PASS (defended)" if r["passed"] else "✗ FAIL (bypassed)"
        print(f"  [{r['task_id']}] {r['category']:<30} {status}")

    print("\n" + "-"*70)
    print("  CATEGORY BREAKDOWN")
    print("-"*70)
    for cat, stats in summary["category_breakdown"].items():
        bar = "█" * stats["passed"] + "░" * (stats["total"] - stats["passed"])
        print(f"  {cat:<35} {bar}  {stats['accuracy']}%  ({stats['passed']}/{stats['total']})")

    print("\n" + "="*70)
    print(f"  OVERALL DEFENSE RATE:  {summary['pass_rate']}%  "
          f"({summary['total_passed']}/{summary['total_attacks']})")
    print("="*70 + "\n")

    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Full results saved to: {args.output}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--purple-url", "--category", "--output", "--timeout"):
        cli_main()
    else:
        # Start as A2A server
        import uvicorn
        port = int(os.getenv("PORT", 8001))
        log.info(f"Starting IntentGuard Green Agent A2A server on port {port}")
        uvicorn.run("green_agent:app", host="0.0.0.0", port=port, reload=False)