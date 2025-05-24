#!/usr/bin/env python3
"""
Test script for MCP v1.0 compliance
Tests the simple format and proper response structure
"""

import requests
import json
import sys
import urllib3

# Disable SSL warnings for localhost testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_simple_format(base_url):
    """Test the simple {"question": "..."} format"""
    print("\n1. Testing simple format:")
    print('Request: {"question": "ping"}')
    
    response = requests.post(
        f"{base_url}/ask",
        json={"question": "ping"},
        headers={"Content-Type": "application/json"},
        verify=False  # Allow self-signed certificates
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"Response keys: {list(data.keys())}")
        
        # Check required fields
        if "schemaVersion" in data:
            print(f"✅ schemaVersion: {data['schemaVersion']}")
        else:
            print("❌ Missing schemaVersion")
            
        if "capabilities" in data:
            print(f"✅ capabilities found")
        else:
            print("❌ Missing capabilities")
            
        if "answer" in data:
            print(f"✅ answer field found (contains {len(data['answer'])} items)")
        else:
            print("❌ Missing answer field")
            
        return True
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_streaming_simple_format(base_url):
    """Test streaming with simple format"""
    print("\n2. Testing simple format with streaming:")
    print('Request: {"question": "test", "stream": true}')
    
    response = requests.post(
        f"{base_url}/ask",
        json={"question": "test", "stream": True},  # Fixed: use Python True
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        stream=True,
        verify=False  # Allow self-signed certificates
    )
    
    if response.status_code == 200:
        print(f"✅ Status: {response.status_code}")
        print("Response (first 5 lines):")
        lines = []
        for i, line in enumerate(response.iter_lines()):
            if i >= 5:
                break
            if line:
                lines.append(line.decode('utf-8'))
                print(f"  {line.decode('utf-8')}")
        
        # Check if it's SSE format
        if any("data:" in line for line in lines):
            print("✅ SSE format detected")
        else:
            print("❌ Not SSE format")
        return True
    else:
        print(f"❌ Status: {response.status_code}")
        return False

def test_function_call_format(base_url):
    """Test the traditional function_call format"""
    print("\n3. Testing function_call format:")
    payload = {
        "function_call": {
            "name": "ask",
            "arguments": json.dumps({"query": "What is Kismet?", "streaming": False})
        }
    }
    print(f"Request: {json.dumps(payload, indent=2)}")
    
    response = requests.post(
        f"{base_url}/ask",
        json=payload,
        headers={"Content-Type": "application/json"},
        verify=False  # Allow self-signed certificates
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        
        # Check for Schema.org types in answer
        if "answer" in data and isinstance(data["answer"], list):
            for item in data["answer"]:
                if "schema_object" in item and "@type" in item.get("schema_object", {}):
                    print(f"✅ Schema.org type found: {item['schema_object']['@type']}")
                    break
        return True
    else:
        print(f"❌ Status: {response.status_code}")
        return False

def test_unsupported_function(base_url):
    """Test error handling for unsupported function"""
    print("\n4. Testing unsupported function error:")
    payload = {
        "function_call": {
            "name": "unsupported_function"
        }
    }
    
    response = requests.post(
        f"{base_url}/ask",
        json=payload,
        headers={"Content-Type": "application/json"},
        verify=False  # Allow self-signed certificates
    )
    
    if response.status_code == 400:
        data = response.json()
        print(f"✅ Status: {response.status_code} (expected)")
        if "error" in data and "schemaVersion" in data:
            print(f"✅ Proper MCP error format")
            print(f"   Error: {data['error']}")
        return True
    else:
        print(f"❌ Unexpected status: {response.status_code}")
        return False

def main():
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    
    print(f"Testing MCP v1.0 compliance at: {base_url}")
    print("=" * 50)
    
    # Run tests
    tests = [
        test_simple_format,
        test_streaming_simple_format,
        test_function_call_format,
        test_unsupported_function
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test(base_url))
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")

if __name__ == "__main__":
    main() 