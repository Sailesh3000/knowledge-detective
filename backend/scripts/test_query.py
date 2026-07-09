import sys
import os
import json
import logging

# Ensure backend root is in search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_query")

from app.query import QueryEngine

def run_tests():
    print("\n==================================================")
    print("Step 6: Testing Reasoning Query Engine (Hybrid RAG)")
    print("==================================================")

    engine = QueryEngine()

    test_questions = [
        "Why did we choose Neo4j over PostgreSQL?",
        "What decision was made about the Google OAuth flow?",
        "Who participated in the kickoff meeting?",
        "What is our frontend architecture?",
        "What is our deployment strategy for production?" # Unanswerable test (no context in corpus)
    ]

    for i, question in enumerate(test_questions):
        print(f"\n--- [Test Question #{i+1}] {question} ---")
        try:
            response = engine.ask(question)
            
            print(f"Plan Strategy: {response['plan']['search_type'].upper()}")
            print(f"Plan Sub-queries: {response['plan']['sub_queries']}")
            print(f"Entities: {response['plan']['entities']}")
            print(f"Topics: {response['plan']['topics']}")
            print("\nFinal Answer:")
            print(response['answer'])
            
            print("\nCitations Used:")
            for cite in response['citations']:
                print(f"  * [{cite['source'].upper()}] {cite['title']} (Author: {cite['author']})")
                
            print(f"\nTime Taken: {response['elapsed_seconds']}s")
            print("-" * 50)
        except Exception as e:
            logger.error(f"Error processing question '{question}': {str(e)}")

    print("\n==================================================")
    print("Testing completed!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
