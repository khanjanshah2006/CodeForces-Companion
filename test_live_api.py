import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def run_e2e_test():
    HANDLE = "tourist"

    print(f"\n--- Starting E2E Test Sequence for handle: '{HANDLE}' ---")
    
    # Test 1: The Initial Sync
    print("\n[Test 1] Initial Sync: POST /sync/{HANDLE}")
    sync_url = f"{BASE_URL}/sync/{HANDLE}"
    try:
        sync_res = requests.post(sync_url)
        print(f"Status Code: {sync_res.status_code}")
        if sync_res.ok:
            data = sync_res.json()
            acc_rate = data.get("overall_acceptance_rate")
            weak_tags = data.get("weak_tags", [])[:3]
            tag_names = [tag.get('tag') for tag in weak_tags]
            
            print(f"Overall Acceptance Rate: {acc_rate}")
            print(f"Top 3 Weak Tags: {tag_names}")
        else:
            print(f"Response: {sync_res.text}")
    except Exception as e:
        print(f"Error during Sync: {e}")

    # Test 2: The POTD Generator
    print("\n[Test 2] POTD Generator: GET /potd/{HANDLE}")
    potd_url = f"{BASE_URL}/potd/{HANDLE}"
    first_problem_id = None
    try:
        potd_res_1 = requests.get(potd_url)
        print(f"Call 1 Status Code: {potd_res_1.status_code}")
        if potd_res_1.ok:
            data_1 = potd_res_1.json()
            first_problem_id = data_1.get("problem_id")
            print(f"Generated problem_id: {first_problem_id}")
            print(f"Status: {data_1.get('status')}")
        else:
            print(f"Response: {potd_res_1.text}")

        # Idempotency Check
        print("\n[Test 2.1] Idempotency Check: GET /potd/{HANDLE} (Again)")
        potd_res_2 = requests.get(potd_url)
        print(f"Call 2 Status Code: {potd_res_2.status_code}")
        if potd_res_2.ok:
            data_2 = potd_res_2.json()
            second_problem_id = data_2.get("problem_id")
            print(f"Generated problem_id: {second_problem_id}")
            print(f"Status: {data_2.get('status')}")
            
            if first_problem_id and second_problem_id:
                assert first_problem_id == second_problem_id, f"Idempotency failed! {first_problem_id} != {second_problem_id}"
                print("Idempotency check PASSED: problem_id matched perfectly.")
        else:
            print(f"Response: {potd_res_2.text}")
    except Exception as e:
        print(f"Error during POTD Generation: {e}")

    # Test 3: The Verification Engine
    print("\n[Test 3] Verification Engine: POST /potd/{HANDLE}/verify")
    verify_url = f"{BASE_URL}/potd/{HANDLE}/verify"
    try:
        verify_res = requests.post(verify_url)
        print(f"Status Code: {verify_res.status_code}")
        if verify_res.ok:
            data = verify_res.json()
            print(f"Response JSON:\n{json.dumps(data, indent=2)}")
            print(f"Returned Status: {data.get('status')}")
        else:
            print(f"Response: {verify_res.text}")
    except Exception as e:
        print(f"Error during Verification: {e}")

if __name__ == "__main__":
    print("================================================================")
    print("! DEVELOPER REMINDER !")
    print("Please ensure your FastAPI server is currently running!")
    print("You can start it in a separate terminal using:")
    print("    cd Server && uvicorn server:app --reload")
    print("================================================================\n")
    run_e2e_test()
