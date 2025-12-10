#!/usr/bin/env python3
"""
KRIZZY OPS V2 LLM Worker

Simple CLI tool to exercise the V2 LLM Control API.
Sends commands to POST /v2/llm/command and displays results.

Usage:
    python v2_llm_worker.py --mode rei_batch
    python v2_llm_worker.py --mode govcon_score_example
    python v2_llm_worker.py --mode buyers_score_example
    python v2_llm_worker.py --mode outbound_write_example
    python v2_llm_worker.py --mode dev_fix_example
"""

import os
import sys
import argparse
import json
import requests
from typing import Dict, Any

from app_v2.agent.prompt import SYSTEM_PROMPT


def get_v2_api_url() -> str:
    """
    Get V2 API base URL.

    Hard-wired to production Railway URL so we never hit localhost by accident.
    If you REALLY want to override, set V2_APP_URL; otherwise this stays prod.
    """
    return os.environ.get(
        "V2_APP_URL",
        "https://krizzyopslaunch-production.up.railway.app"
    )


def call_llm_command(api_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call POST /v2/llm/command with given payload.

    Args:
        api_url: Base URL of V2 API
        payload: Command payload (engine, action, payload)

    Returns:
        Response JSON
    """
    endpoint = f"{api_url}/v2/llm/command"

    print(f"\n{'='*60}")
    print(f"REQUEST TO: {endpoint}")
    print(f"{'='*60}")
    print(json.dumps(payload, indent=2))
    print(f"{'='*60}\n")

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"{'='*60}")
        print(f"RESPONSE: {response.status_code}")
        print(f"{'='*60}")

        if response.ok:
            result = response.json()
            print(json.dumps(result, indent=2))
        else:
            print(f"ERROR: {response.status_code}")
            print(response.text)

        print(f"{'='*60}\n")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"\n❌ REQUEST FAILED: {e}\n")
        sys.exit(1)


def mode_rei_batch(api_url: str):
    """Run REI batch processing (input + underwriting)"""
    payload = {
        "engine": "rei",
        "action": "run",
        "payload": {
            "batch": 150
        }
    }
    call_llm_command(api_url, payload)


def mode_govcon_score_example(api_url: str):
    """Score a sample GovCon opportunity"""
    payload = {
        "engine": "govcon",
        "action": "score",
        "payload": {
            "naics": "236220",
            "set_aside": "Small Business",
            "description": "Construction and maintenance services for federal facilities. Includes HVAC repair, electrical work, and general building maintenance.",
            "title": "Facility Maintenance Services - DOD",
            "agency": "Department of Defense"
        }
    }
    call_llm_command(api_url, payload)


def mode_buyers_score_example(api_url: str):
    """Score a sample buyer profile"""
    payload = {
        "engine": "buyers",
        "action": "score",
        "payload": {
            "name": "John Smith Capital",
            "market": "Tampa Bay",
            "notes": "Cash buyer, actively buying, closes in 7 days, proof of funds available",
            "liquidity": "high",
            "strategy": "flip"
        }
    }
    call_llm_command(api_url, payload)


def mode_outbound_write_example(api_url: str):
    """Generate outbound copy for buyers"""
    payload = {
        "engine": "outbound",
        "action": "write",
        "payload": {
            "role": "buyers",
            "market": "Tampa",
            "deal_count": 3
        }
    }
    call_llm_command(api_url, payload)


def mode_dev_fix_example(api_url: str):
    """Diagnose a sample error"""
    payload = {
        "engine": "dev",
        "action": "fix",
        "payload": {
            "error": "422 Unprocessable Entity: invalid field 'Spread_Value' in Leads_REI table",
            "context": {
                "table": "Leads_REI",
                "failed_fields": ["Spread_Value"]
            }
        }
    }
    call_llm_command(api_url, payload)


def mode_rei_normalize_example(api_url: str):
    """Normalize raw REI text to structured data"""
    payload = {
        "engine": "rei",
        "action": "normalize",
        "payload": {
            "text": "Property at 123 Main St, Tampa FL 33609. Asking $250,000. ARV is $340,000. Needs about $35,000 in repairs (roof and HVAC)."
        }
    }
    call_llm_command(api_url, payload)


def mode_rei_score_example(api_url: str):
    """Score a sample REI deal"""
    payload = {
        "engine": "rei",
        "action": "score",
        "payload": {
            "asking": 250000,
            "arv": 340000,
            "repairs": 35000
        }
    }
    call_llm_command(api_url, payload)


def mode_dev_health(api_url: str):
    """Check V2 system health"""
    payload = {
        "engine": "dev",
        "action": "health",
        "payload": {}
    }
    call_llm_command(api_url, payload)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="KRIZZY OPS V2 LLM Worker - Exercise V2 LLM Control API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available modes:
  rei_batch              - Run REI batch processing (input + underwriting)
  rei_normalize_example  - Normalize raw REI text to structured data
  rei_score_example      - Score a sample REI deal
  govcon_score_example   - Score a sample GovCon opportunity
  buyers_score_example   - Score a sample buyer profile
  outbound_write_example - Generate outbound copy for buyers
  dev_fix_example        - Diagnose a sample error
  dev_health             - Check V2 system health

Environment:
  V2_APP_URL            - Base URL of V2 API (default: http://localhost:8080)

Examples:
  python v2_llm_worker.py --mode rei_batch
  V2_APP_URL=https://my-v2.railway.app python v2_llm_worker.py --mode dev_health
        """
    )

    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=[
            "rei_batch",
            "rei_normalize_example",
            "rei_score_example",
            "govcon_score_example",
            "buyers_score_example",
            "outbound_write_example",
            "dev_fix_example",
            "dev_health"
        ],
        help="Execution mode"
    )

    args = parser.parse_args()

    # Get API URL
    api_url = get_v2_api_url()

    print(f"\n{'#'*60}")
    print(f"# KRIZZY OPS V2 LLM WORKER")
    print(f"# Mode: {args.mode}")
    print(f"# API: {api_url}")
    print(f"{'#'*60}\n")

    # Display system prompt info
    print(f"System Prompt Length: {len(SYSTEM_PROMPT)} characters")
    print(f"First 200 chars: {SYSTEM_PROMPT[:200]}...\n")

    # Route to appropriate mode handler
    mode_handlers = {
        "rei_batch": mode_rei_batch,
        "rei_normalize_example": mode_rei_normalize_example,
        "rei_score_example": mode_rei_score_example,
        "govcon_score_example": mode_govcon_score_example,
        "buyers_score_example": mode_buyers_score_example,
        "outbound_write_example": mode_outbound_write_example,
        "dev_fix_example": mode_dev_fix_example,
        "dev_health": mode_dev_health,
    }

    handler = mode_handlers[args.mode]
    handler(api_url)

    print(f"\n✅ {args.mode} completed successfully\n")


if __name__ == "__main__":
    main()
