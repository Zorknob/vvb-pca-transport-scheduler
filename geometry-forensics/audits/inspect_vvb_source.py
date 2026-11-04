# Copyright 2026 James Scott Graber and Lumen Virtus
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
