#!/usr/bin/env python3
import requests
import json
import sys

def test_basic_chat(question: str, base_url: str = "http://localhost:5000"):
    """Test basic agentic chat."""
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={"question": question},
            timeout=30
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def test_enhanced_chat(question: str, base_url: str = "http://localhost:5000"):
    """Test enhanced agentic chat."""
    try:
        response = requests.post(
            f"{base_url}/enhanced-chat",
            json={"question": question},
            timeout=30
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_status(base_url: str = "http://localhost:5000"):
    """Get system status."""
    try:
        response = requests.get(f"{base_url}/status", timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_agentic.py <command> [args]")
        print("Commands:")
        print("  status - Get system status")
        print("  basic 'question' - Test basic chat")
        print("  enhanced 'question' - Test enhanced chat")
        print("  interactive - Interactive mode")
        return
    
    command = sys.argv[1]
    
    if command == "status":
        result = get_status()
        print(json.dumps(result, indent=2))
        
    elif command == "basic" and len(sys.argv) > 2:
        question = sys.argv[2]
        result = test_basic_chat(question)
        print(f"Question: {question}")
        print(f"Answer: {result.get('answer', result.get('error'))}")
        
    elif command == "enhanced" and len(sys.argv) > 2:
        question = sys.argv[2]
        result = test_enhanced_chat(question)
        print(f"Question: {question}")
        print(f"Answer: {result.get('answer', result.get('error'))}")
        
    elif command == "interactive":
        print("🤖 Interactive Agentic S3 Chat Tester")
        print("Commands: 'basic <question>', 'enhanced <question>', 'status', 'quit'")
        
        while True:
            try:
                cmd = input("\n> ").strip()
                if cmd.lower() in ['quit', 'exit', 'q']:
                    break
                    
                if cmd == "status":
                    result = get_status()
                    print(json.dumps(result, indent=2))
                    
                elif cmd.startswith("basic "):
                    question = cmd[6:]
                    result = test_basic_chat(question)
                    print(f"Answer: {result.get('answer', result.get('error'))}")
                    
                elif cmd.startswith("enhanced "):
                    question = cmd[9:]
                    result = test_enhanced_chat(question)
                    print(f"Answer: {result.get('answer', result.get('error'))}")
                    
                else:
                    print("Invalid command. Use 'basic <question>', 'enhanced <question>', 'status', or 'quit'")
                    
            except KeyboardInterrupt:
                break
                
        print("\n👋 Goodbye!")
    else:
        print("Invalid command or missing arguments")

if __name__ == "__main__":
    main()
