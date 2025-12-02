#!/usr/bin/env python3
"""
Script to update CORS origins in the FastAPI application.
Run this after deployment to add your production domain.

Usage:
    python update_cors.py your-domain.com
    python update_cors.py 54.123.45.67
"""

import sys
import re

API_FILE = "/opt/gap-assessment/api/gap_assessment_api.py"

def update_cors(domain: str):
    """Update CORS origins to include production domain"""

    with open(API_FILE, 'r') as f:
        content = f.read()

    # Pattern to match CORS allow_origins
    pattern = r'allow_origins=\[([^\]]+)\]'

    # New origins including production
    new_origins = f'''allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://{domain}",
        "https://{domain}"
    ]'''

    updated = re.sub(pattern, new_origins, content)

    with open(API_FILE, 'w') as f:
        f.write(updated)

    print(f"Updated CORS origins to include: {domain}")
    print("Restart the service: sudo systemctl restart gap-assessment")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_cors.py <domain-or-ip>")
        sys.exit(1)

    update_cors(sys.argv[1])