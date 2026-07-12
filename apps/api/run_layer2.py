import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../packages")))

from pipeline.orchestrator import PipelineOrchestrator

def run_test():
    pdf_file = r"C:\Users\Document\OneDrive\Desktop\TFG\Project\test_sample.pdf" 
    
    if not os.path.exists(pdf_file):
        print(f"Error: Cannot find sample file at {pdf_file}")
        return

    try:
        res = PipelineOrchestrator.run(pdf_file, mode="mock")
        print(json.dumps(res.to_master_report_dict(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_test()