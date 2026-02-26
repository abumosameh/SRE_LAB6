import requests
import time
import random
import logging

# Set up some basic logging so we can visualize what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Resiliency Patterns Implementations ---

class CircuitBreaker:
    """
    A simple implementation of the Circuit Breaker pattern.
    Transitions between CLOSED, OPEN, and HALF_OPEN states.
    """
    def __init__(self, failure_threshold=3, recovery_timeout=10):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None

    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logging.warning("Circuit breaker transitioning to HALF_OPEN to test the waters...")
                self.state = "HALF_OPEN"
            else:
                logging.error("Circuit is OPEN. Failing fast to prevent cascading failure.")
                raise Exception("CircuitBreaker is OPEN")

        try:
            response = func(*args, **kwargs)
            if response.status_code >= 500:
                raise Exception(f"Server Error {response.status_code}")
            
            # If successful, reset everything
            self.failure_count = 0
            self.state = "CLOSED"
            return response
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            logging.error(f"Request failed. Failure count: {self.failure_count}")
            
            if self.failure_count >= self.failure_threshold:
                logging.critical("Failure threshold reached! Tripping the Circuit Breaker to OPEN.")
                self.state = "OPEN"
            
            raise e

def exponential_backoff_retry(max_retries=3, base_delay=1, max_delay=8):
    """
    Decorator for Retry with Exponential Backoff and Jitter.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    # We set a strict timeout here. If it takes too long, we retry.
                    return func(*args, timeout=3, **kwargs)
                except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                    retries += 1
                    if retries > max_retries:
                        logging.error(f"Max retries ({max_retries}) exhausted. Giving up.")
                        raise e
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    jitter = random.uniform(0, 0.5) 
                    total_delay = delay + jitter
                    
                    logging.warning(f"Timeout/Error occurred. Retrying in {total_delay:.2f} seconds... (Attempt {retries}/{max_retries})")
                    time.sleep(total_delay)
        return wrapper
    return decorator


# --- Graceful Degradation Application ---

class ECommerceApp:
    def __init__(self, base_url):
        self.base_url = base_url
        self.unreliable_circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=5)
        self.system_load = 0 # Simulated load metric (0 to 100)
    
    def view_product(self):
        """Tier 1: Critical functionality. Must work. Calls /healthy"""
        logging.info("--- Fetching Tier 1 (Product Info) ---")
        try:
            response = requests.get(f"{self.base_url}/healthy")
            logging.info(f"Success: {response.json()['message']}")
        except Exception as e:
            logging.critical("Tier 1 Failed! Entire site is down.")

    def load_reviews(self):
        """Tier 2: Important. Uses Circuit Breaker and Fallback. Calls /unreliable"""
        logging.info("--- Fetching Tier 2 (User Reviews) ---")
        try:
            response = self.unreliable_circuit_breaker.call(requests.get, f"{self.base_url}/unreliable")
            logging.info(f"Success: {response.json()['message']}")
        except Exception as e:
            # Fallback mechanism
            logging.info("Fallback activated: Displaying cached user reviews instead of live data.")

    @exponential_backoff_retry(max_retries=3)
    def fetch_recommendations_with_retry(self):
        return requests.get(f"{self.base_url}/slow")

    def load_recommendations(self):
        """Tier 3: Nice-to-have. Uses Load Shedding and Retries. Calls /slow"""
        logging.info("--- Fetching Tier 3 (Recommendations) ---")
        
        # Load Shedding Mechanism
        if self.system_load > 80:
            logging.warning("Load shedding active! System under heavy load. Gracefully disabling recommendations.")
            return

        try:
            response = self.fetch_recommendations_with_retry()
            logging.info(f"Success: {response.json()['message']}")
        except Exception as e:
            logging.info("Graceful degradation: Recommendations area hidden from UI.")


# --- Chaos Monkey (Bonus Challenge) ---

class ChaosMonkey:
    def __init__(self, app):
        self.app = app
        
    def inject_load_spike(self):
        logging.critical("🐵 CHAOS MONKEY: Injecting massive server load!")
        self.app.system_load = 95
        
    def resolve_load_spike(self):
        logging.info("🐵 CHAOS MONKEY: Server load normalized.")
        self.app.system_load = 20

# --- Main Execution ---
if __name__ == "__main__":
    # Note: Replace this with your actual API Gateway URL generated by Terraform
    API_URL = "https://your-api-id.execute-api.us-east-1.amazonaws.com/dev"
    
    app = ECommerceApp(API_URL)
    chaos = ChaosMonkey(app)
    
    print("\n========== STARTING NORMAL OPERATIONS ==========")
    for _ in range(3):
        app.view_product()
        app.load_reviews()
        time.sleep(1)
        
    print("\n========== STARTING CHAOS / DEGRADATION TEST ==========")
    chaos.inject_load_spike()
    
    # Try fetching everything during high load
    app.view_product()        # Should succeed
    app.load_reviews()        # Might fail/fallback
    app.load_recommendations() # Should be shed immediately due to load
    
    print("\n========== TESTING RETRY WITH BACKOFF ==========")
    chaos.resolve_load_spike()
    app.load_recommendations() # Will hit the slow endpoint and likely timeout/retry
