import time

def mock_background_task(user_email: str):
    time.sleep(2)
    print(f"Sent welcome email to {user_email}")
