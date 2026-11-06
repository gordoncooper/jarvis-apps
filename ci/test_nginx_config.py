"""Test nginx configuration correctness in hello-web.

Validates that $upstream is set before rewrite...break in proxy locations.
"""

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_upstream_set_before_rewrite():
    """Validate that 'set $upstream' comes before 'rewrite...break' in all proxy locations.
    
    nginx's 'rewrite...break' stops processing rewrite module directives,
    so 'set $upstream' must come first or $upstream will be empty, causing 500 errors.
    """
    yaml_path = ROOT / "hello-web" / "deploy" / "hello-web.yaml"
    docs = list(yaml.safe_load_all(yaml_path.read_text(encoding="utf-8")))
    
    config_map = next((doc for doc in docs if doc.get("kind") == "ConfigMap" and 
                      "default.conf.template" in doc.get("data", {})), None)
    assert config_map, "ConfigMap with default.conf.template not found"
    
    template = config_map["data"]["default.conf.template"]
    
    # Find all location blocks that use both 'set $upstream' and 'rewrite...break'
    locations = ["/notes/", "/blocked/", "/internet/"]
    
    for location in locations:
        loc_start = template.find(f"location {location}")
        assert loc_start != -1, f"location {location} not found"
        
        # Find the closing brace
        brace_count = 0
        loc_end = loc_start
        for i, char in enumerate(template[loc_start:], start=loc_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    loc_end = i
                    break
        
        location_block = template[loc_start:loc_end + 1]
        
        set_pos = location_block.find("set $upstream")
        rewrite_pos = location_block.find("rewrite")
        
        assert set_pos != -1, f"{location}: 'set $upstream' not found"
        assert rewrite_pos != -1, f"{location}: 'rewrite' not found"
        
        # CRITICAL: set $upstream must come before rewrite...break
        assert set_pos < rewrite_pos, (
            f"{location}: 'set $upstream' at pos {set_pos} must come before 'rewrite' at {rewrite_pos}"
        )
