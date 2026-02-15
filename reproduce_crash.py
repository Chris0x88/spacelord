from pacman_app import PacmanApp
from pacman_logger import set_verbose

def reproduce():
    set_verbose(True)
    app = PacmanApp()
    
    print("\n--- Testing Convert HTS-WBTC -> WBTC_LZ ---")
    # Simulate: convert HTS-WBTC for 0.00001 WBTC_LZ
    # Translator resolves HTS-WBTC -> WBTC_HTS (or similar)
    
    # We'll use the exact strings the CLI would likely produce after translation
    # "HTS-WBTC" usually resolves to "WBTC_HTS" if we look at pacman_translator or aliases
    # But let's try direct variants first
    
    route = app.get_route("WBTC_HTS", "WBTC_LZ", 0.00001, strict_wrap=True)
    
    if route:
        print("Route found.")
        print("Steps:", len(route.steps))
        step = route.steps[0]
        print("Step 0 Details:", step.details)
        print("Step 0 to_token:", step.to_token)
        
        if "token_out_id" in step.details:
            print("PASS: token_out_id is present in App results.")
        else:
            print("FAIL: token_out_id MISSING in App results.")
            
        # Also check executor association logic simulation
        # app.executor._ensure_association(route) # We can't run this easily without private key, but we can check the route object
    else:
        print("FAIL: No route found.")

if __name__ == "__main__":
    reproduce()
