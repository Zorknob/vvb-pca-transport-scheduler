# inspect_vvb_source.py — Inspecting radius_at_z and switching logic
import inspect
from vvb_min260112 import radius_at_z, SwitchPolicy

def main():
    print("=== Source Code Inspection: radius_at_z ===")
    print(inspect.getsource(radius_at_z))
    
    print("\n=== Source Code Inspection: SwitchPolicy ===")
    print(inspect.getsource(SwitchPolicy))

if __name__ == "__main__":
    main()