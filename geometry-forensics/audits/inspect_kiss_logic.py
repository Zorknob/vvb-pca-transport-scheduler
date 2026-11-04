# inspect_kiss_logic.py — Inspecting prefer_kiss_height and apply_switch
import inspect
from vvb_min260112 import prefer_kiss_height, apply_switch

def main():
    print("=== Source Code Inspection: prefer_kiss_height ===")
    print(inspect.getsource(prefer_kiss_height))
    
    print("\n=== Source Code Inspection: apply_switch ===")
    print(inspect.getsource(apply_switch))

if __name__ == "__main__":
    main()