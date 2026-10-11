import time
import requests
import os

DATASET_DIR = "evaluation_dataset"
UPLOAD_URL = "http://127.0.0.1:8000/documents"

def run_evaluation():
    if not os.path.exists(DATASET_DIR):
        print(f"Error: Directory '{DATASET_DIR}' not found. Run generate_dataset.py first.")
        return

    print("=========================================")
    print("   STARTING PIPELINE METRICS EVALUATION  ")
    print("=========================================")
    
    files = [f for f in os.listdir(DATASET_DIR) if os.path.isfile(os.path.join(DATASET_DIR, f))]
    
    if not files:
        print("Error: No files found in dataset directory.")
        return

    total_latency = 0
    success_count = 0
    
    for filename in files:
        file_path = os.path.join(DATASET_DIR, filename)
        start_time = time.time()
        
        try:
            with open(file_path, "rb") as f:
                # FastAPI expects a file upload object
                files_payload = {"file": (filename, f, "application/pdf")}
                response = requests.post(UPLOAD_URL, files=files_payload)
                
            latency = time.time() - start_time
            total_latency += latency
            
            # Check if it was accepted (200, 201, 202) 
            # OR if it's our malicious fake file, it SHOULD be rejected (400+)
            if response.status_code in [200, 201, 202]:
                success_count += 1
                print(f"[✓] ACCEPTED: {filename:<22} | Latency: {latency:.3f}s | Status: {response.status_code}")
            elif "fake" in filename and response.status_code >= 400:
                success_count += 1
                print(f"[✓] REJECTED (Security Pass): {filename:<10} | Latency: {latency:.3f}s | Status: {response.status_code}")
            else:
                print(f"[X] UNEXPECTED: {filename:<20} | Latency: {latency:.3f}s | Status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"[!] FAILED: {filename} - Is your FastAPI server running?")
            return
        except Exception as e:
            print(f"[!] ERROR: {filename} | {str(e)}")

    # Calculate final metrics
    avg_latency = total_latency / len(files)
    success_rate = (success_count / len(files)) * 100

    print("=========================================")
    print("          GENUINE METRICS REPORT         ")
    print("=========================================")
    print(f"Total Documents Evaluated: {len(files)}")
    print(f"Overall System Success Rate: {success_rate:.1f}%")
    print(f"Average Processing Latency:  {avg_latency:.3f}s per document")
    print("=========================================")
    print("Take these numbers and put them in your EVALUATION.md!")

if __name__ == "__main__":
    run_evaluation()