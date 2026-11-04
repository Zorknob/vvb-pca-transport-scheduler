# inspect_switching_logic.py — Inspecting step function and hop criteria
import inspect
from vvb_min260112 import step

def main():
    print("=== Source Code Inspection: step() ===")
    print(inspect.getsource(step))

if __name__ == "__main__":
    main()