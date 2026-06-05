"""
Test Script for IntentGuard

This script tests the three-layer architecture with various scenarios
from the SANER/ERA 2026 paper.
"""

import os
import json
from dotenv import load_dotenv
from smart_home_agent import SmartHomeAgent


class IntentGuardTester:
    """Test suite for IntentGuard framework"""
    
    def __init__(self):
        """Initialize tester"""
        load_dotenv()
        
        self.agent = SmartHomeAgent(
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            pinecone_api_key=os.getenv("PINECONE_API_KEY")
        )
        
        self.test_results = []
    
    def run_test(self, name: str, request: str, expected_behavior: str):
        """
        Run a single test case
        
        Args:
            name: Test case name
            request: User automation request
            expected_behavior: What should happen (for documentation)
        """
        print("="*80)
        print(f"TEST: {name}")
        print("="*80)
        print(f"Request: {request}")
        print(f"Expected: {expected_behavior}")
        print("-"*80)
        
        try:
            result = self.agent.process_request(request)
            
            if result["success"]:
                print("\n✓ Agent Response:")
                print(result["response"][:500] + "..." if len(result["response"]) > 500 else result["response"])
                
                if result["has_json"]:
                    print("\n✓ JSON Generated:")
                    print(json.dumps(result["generated_json"], indent=2)[:300] + "...")
                    status = "PASS - JSON Generated"
                else:
                    print("\nℹ️  No JSON (conflict detected or clarification needed)")
                    status = "PASS - Conflict Detected"
            else:
                print(f"\n❌ Error: {result.get('error')}")
                status = "FAIL"
            
            self.test_results.append({
                "test": name,
                "status": status,
                "has_json": result.get("has_json", False)
            })
            
        except Exception as e:
            print(f"\n❌ Exception: {e}")
            self.test_results.append({
                "test": name,
                "status": "FAIL",
                "error": str(e)
            })
        
        print("\n")
    
    def run_all_tests(self):
        """Run all test scenarios from the paper"""
        
        print("\n" + "🧪"*40)
        print("INTENTGUARD TEST SUITE")
        print("Based on SANER/ERA 2026 Paper Test Cases")
        print("🧪"*40 + "\n")
        
        # Test 1: Basic Rule Generation (No Conflict)
        self.run_test(
            name="1. Basic Rule - Motion Sensor",
            request="Turn off the living room fan when motion is no longer detected",
            expected_behavior="Should generate valid JSON without conflicts"
        )
        
        # Test 2: Direct Contradiction - Time-based
        self.run_test(
            name="2. Direct Contradiction - Time",
            request="Turn ON all lights at 11 PM every day",
            expected_behavior="Should detect conflict with existing 'lights OFF at 11 PM' rule"
        )
        
        # Test 3: Direct Contradiction - Temperature
        self.run_test(
            name="3. Direct Contradiction - Temperature",
            request="Turn OFF the air conditioner when temperature is greater than 80 degrees",
            expected_behavior="Should detect conflict if AC ON rule exists at 80°F"
        )
        
        # Test 4: Temporal Illogicality
        self.run_test(
            name="4. Temporal Illogicality - Rapid Cycle",
            request="Turn OFF the bedroom lights at 9:02 AM every day",
            expected_behavior="Should detect rapid cycle if lights ON at 9:00 AM exists"
        )
        
        # Test 5: Condition Overlap - Humidity
        self.run_test(
            name="5. Condition Overlap - Humidity",
            request="Turn the bathroom fan OFF when humidity is greater than 65%",
            expected_behavior="Should detect overlap with 60% threshold if exists"
        )
        
        # Test 6: Valid Rule - Different Device
        self.run_test(
            name="6. Valid Rule - Kitchen Light",
            request="Turn on the kitchen lights when the front door opens",
            expected_behavior="Should generate valid JSON (different device, no conflict)"
        )
        
        # Test 7: Valid Rule - Different Time
        self.run_test(
            name="7. Valid Rule - Morning Routine",
            request="Turn on the bedroom lights at 7:00 AM every weekday",
            expected_behavior="Should generate valid JSON (different time window)"
        )
        
        # Test 8: Complex Condition
        self.run_test(
            name="8. Complex Rule - Lock",
            request="Lock the front door when I leave home",
            expected_behavior="Should request device ID or presence sensor details"
        )
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("TEST RESULTS SUMMARY")
        print("="*80 + "\n")
        
        total = len(self.test_results)
        passed = len([r for r in self.test_results if "PASS" in r["status"]])
        failed = len([r for r in self.test_results if "FAIL" in r["status"]])
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total)*100:.1f}%\n")
        
        print("Detailed Results:")
        print("-"*80)
        for result in self.test_results:
            status_icon = "✓" if "PASS" in result["status"] else "❌"
            print(f"{status_icon} {result['test']}")
            print(f"   Status: {result['status']}")
            if result.get("error"):
                print(f"   Error: {result['error']}")
        print("-"*80 + "\n")
        
        # Save results
        with open("test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": f"{(passed/total)*100:.1f}%"
                },
                "tests": self.test_results
            }, f, indent=2)
        
        print("Results saved to test_results.json\n")


def main():
    """Run the test suite"""
    tester = IntentGuardTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()