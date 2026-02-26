import json
import random
import time

# ---------------------------------------------------------
# Lab 6 - API Backend
# These three functions act as our mock microservices
# ---------------------------------------------------------

def healthy_handler(event, context):
    """
    Provides a 'healthy' endpoint that always succeeds.
    Simulates Tier 1 / Critical functionality.
    """
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "success", "message": "Critical data retrieved successfully."})
    }

def unreliable_handler(event, context):
    """
    Provides an 'unreliable' endpoint that fails randomly 50% of the time.
    Used to test the Circuit Breaker and Fallback patterns.
    """
    if random.random() < 0.5:
        # Simulate a crash or dependency failure
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal Server Error! The database is on fire."})
        }
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "success", "message": "User reviews loaded (you got lucky)."})
    }

def slow_handler(event, context):
    """
    Provides a 'slow' endpoint that responds with variable latency (1-10s).
    Used to test the Retry with Exponential Backoff pattern and Load Shedding.
    """
    delay = random.uniform(1, 10)
    time.sleep(delay)
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "status": "success", 
            "message": f"Personalized recommendations generated.",
            "latency_seconds": round(delay, 2)
        })
    }
