#!/usr/bin/env python3
"""
Full extraction and gap assessment script
Extracts data from all companies, creates indexes, and generates gap assessment
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agent.gap_assessment_agent import GapAssessmentAgent
import json

def main():
    print("=" * 80)
    print("FULL EXTRACTION AND GAP ASSESSMENT")
    print("=" * 80)
    
    # Initialize agent
    print("\n[1/6] Initializing agent...")
    try:
        agent = GapAssessmentAgent()
        print("✓ Agent initialized")
        print(f"  Embedding model: {agent.embedding_client.model_name}")
        print(f"  Dimension: {agent.vector_db.dimension}")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Get all companies from config
    companies = agent.config["companies"]
    primary = companies["primary"]
    benchmarks = companies["benchmark_companies"]
    all_companies = [primary] + benchmarks
    
    print(f"\n[2/6] Extracting data for all companies...")
    print(f"Companies: {', '.join(all_companies)}")
    
    # Check force_refresh config
    force_refresh = agent.config.get("extraction", {}).get("force_refresh", False)
    if not force_refresh:
        print(f"\n⚠ force_refresh is False in config - extraction will be skipped")
        print(f"  Set force_refresh=True in config/agent_config.json to enable extraction")
        use_force = False
    else:
        use_force = True
    
    extraction_results = {}
    for company in all_companies:
        print(f"\n{'='*60}")
        print(f"Processing: {company.upper()}")
        print(f"{'='*60}")
        
        try:
            # Only use force=True if force_refresh is True in config
            result = agent.extraction_tool.extract_company_data(company, force=use_force)
            extraction_results[company] = result
            
            if result.get('status') == 'success':
                print(f"✓ {company.upper()}: {result.get('chunks_stored', 0)} chunks, {result.get('vectors_stored', 0)} vectors")
            elif result.get('status') == 'skipped':
                print(f"⊘ {company.upper()}: {result.get('reason', 'Skipped')}")
            else:
                print(f"✗ {company.upper()}: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"✗ {company.upper()}: Failed - {e}")
            extraction_results[company] = {"status": "error", "error": str(e)}
    
    # Check all indexes
    print(f"\n[3/6] Checking all Pinecone indexes...")
    indexes = agent.vector_db.list_indexes()
    print(f"Available indexes: {indexes}")
    
    for idx in indexes:
        try:
            stats = agent.vector_db.get_index_stats(idx)
            print(f"  {idx}: {stats.get('vector_count', 0)} vectors")
        except Exception as e:
            print(f"  {idx}: Error getting stats - {e}")
    
    # Test RAG search
    print(f"\n[4/6] Testing RAG search across all indexes...")
    test_query = "What are the strategic initiatives in tax technology and compliance?"
    
    try:
        search_results = agent.rag_tool.search(test_query)
        
        if search_results.get('error'):
            print(f"  Error: {search_results.get('error')}")
        else:
            primary_count = len(search_results.get('primary', []))
            benchmark_count = sum(len(v) for v in search_results.get('benchmarks', {}).values())
            print(f"  ✓ Primary results: {primary_count}")
            print(f"  ✓ Benchmark results: {benchmark_count}")
            
            if primary_count > 0:
                print(f"  Top primary result score: {search_results['primary'][0].get('score', 0):.3f}")
    except Exception as e:
        print(f"  ✗ RAG search failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Generate gap assessment
    print(f"\n[5/6] Generating complete gap assessment...")
    assessment_query = "What are the gaps in BP's tax technology and compliance digitization compared to industry benchmarks (KPMG, EY, Deloitte, PWC)?"
    
    try:
        # Don't force extraction - respect force_refresh config
        assessment_result = agent.assess_gaps(
            query=assessment_query,
            force_extraction=False  # Don't force - will respect force_refresh config
        )
        
        if assessment_result.get('error'):
            print(f"  Error: {assessment_result.get('error')}")
        elif assessment_result.get('status') == 'quota_exceeded':
            print(f"  ⚠ LLM quota exceeded (assessment generation uses Gemini)")
            print(f"  Search results available: {len(search_results.get('primary', []))} primary results")
        else:
            print(f"  ✓ Gap assessment generated successfully")
            
            if 'assessment' in assessment_result:
                assessment = assessment_result['assessment']
                print(f"  Assessment keys: {list(assessment.keys())}")
                
                # Save assessment to file
                output_file = "gap_assessment_result.json"
                with open(output_file, 'w') as f:
                    json.dump(assessment_result, f, indent=2)
                print(f"  ✓ Assessment saved to: {output_file}")
    except Exception as e:
        print(f"  ✗ Assessment generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print(f"\n[6/6] Summary")
    print("=" * 80)
    
    successful = sum(1 for r in extraction_results.values() if r.get('status') == 'success')
    print(f"Companies extracted: {successful}/{len(all_companies)}")
    print(f"Pinecone indexes: {len(indexes)}")
    
    total_vectors = sum(
        agent.vector_db.get_index_stats(idx).get('vector_count', 0)
        for idx in indexes
    )
    print(f"Total vectors stored: {total_vectors}")
    
    print("\n" + "=" * 80)
    print("Extraction and Assessment Complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Check gap_assessment_result.json for full assessment")
    print("2. Start API: uvicorn api.gap_assessment_api:app --host 0.0.0.0 --port 8000")
    print("3. Query API: POST http://localhost:8000/assess")
    print("=" * 80)

if __name__ == "__main__":
    main()

