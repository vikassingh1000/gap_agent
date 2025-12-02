#!/usr/bin/env python3
"""
Main script to run Gap Assessment Agent
"""
import os
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.gap_assessment_agent import GapAssessmentAgent


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Gap Assessment Agent')
    parser.add_argument(
        '--query',
        type=str,
        required=True,
        help='Assessment query/question'
    )
    parser.add_argument(
        '--force-extraction',
        action='store_true',
        help='Force data extraction even if recent data exists'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to agent configuration file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path for results (JSON)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Gap Assessment Agent")
    print("=" * 80)
    print(f"Query: {args.query}")
    print(f"Force Extraction: {args.force_extraction}")
    print("=" * 80)
    
    try:
        # Initialize agent
        print("\n[1/3] Initializing agent...")
        agent = GapAssessmentAgent(config_path=args.config)
        print("✓ Agent initialized")
        
        # Run assessment
        print("\n[2/3] Running gap assessment...")
        result = agent.assess_gaps(
            query=args.query,
            force_extraction=args.force_extraction
        )
        print("✓ Assessment complete")
        
        # Save results
        if args.output:
            import json
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n[3/3] Results saved to: {args.output}")
        else:
            print("\n[3/3] Results:")
            import json
            print(json.dumps(result, indent=2))
        
        # Save logs
        agent.logger.save_logs()
        
        print("\n" + "=" * 80)
        print("Assessment Complete!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

