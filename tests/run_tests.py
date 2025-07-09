#!/usr/bin/env python3
"""Professional test runner for Greg AI Playground

This runner supports:
- Parallel test execution
- Different test suites (unit, integration, ui)
- CI/CD environments
- Performance benchmarking
- Test result reporting
"""
import argparse
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple
import multiprocessing


class TestRunner:
    """Professional test runner with parallel execution support"""
    
    def __init__(self, args):
        self.args = args
        self.results = {}
        self.start_time = time.time()
        
    def run_test_suite(self, suite_name: str, pytest_args: List[str]) -> Tuple[bool, float]:
        """Run a specific test suite"""
        print(f"\n{'='*60}")
        print(f"Running {suite_name} Tests")
        print(f"{'='*60}")
        
        start = time.time()
        
        cmd = [sys.executable, "-m", "pytest"] + pytest_args
        
        if self.args.verbose:
            print(f"Command: {' '.join(cmd)}")
        
        # Always show output in real-time
        result = subprocess.run(cmd)
        
        duration = time.time() - start
        success = result.returncode == 0
        
        if success:
            print(f"✅ {suite_name} tests PASSED in {duration:.1f}s")
        else:
            print(f"❌ {suite_name} tests FAILED in {duration:.1f}s")
        
        return success, duration
    
    def run_parallel(self) -> Dict[str, Tuple[bool, float]]:
        """Run test suites in parallel where possible"""
        test_suites = self.get_test_suites()
        
        if self.args.parallel and len(test_suites) > 1:
            print(f"Running {len(test_suites)} test suites in parallel...")
            with multiprocessing.Pool(processes=self.args.workers) as pool:
                results = pool.starmap(self.run_test_suite, test_suites.items())
                return dict(zip(test_suites.keys(), results))
        else:
            # Run sequentially
            results = {}
            for suite_name, pytest_args in test_suites.items():
                results[suite_name] = self.run_test_suite(suite_name, pytest_args)
            return results
    
    def get_test_suites(self) -> Dict[str, List[str]]:
        """Get test suites to run based on arguments"""
        base_args = []
        
        if self.args.verbose:
            base_args.extend(["-v"])
        else:
            # Show test names but not full verbose output
            base_args.extend(["-v", "--tb=short"])
            
        if self.args.exitfirst:
            base_args.extend(["-x"])
            
        if self.args.capture == "no":
            base_args.extend(["-s"])
            
        suites = {}
        
        if self.args.suite == "all":
            # Unit tests (can run in parallel)
            suites["Unit"] = base_args + [
                "tests/unit/"
            ]
            
            # Integration tests (run sequentially)
            if not self.args.unit_only:
                suites["Integration"] = base_args + [
                    "tests/integration/"
                ]
                
                
                # Performance tests
                suites["Performance"] = base_args + [
                    "tests/performance/"
                ]
                
                
                # API tests
                suites["API"] = base_args + [
                    "tests/api/"
                ]
                
                # Streamlit tests
                suites["Streamlit"] = base_args + [
                    "tests/streamlit/"
                ]
        
        elif self.args.suite == "unit":
            suites["Unit"] = base_args + ["tests/unit/"]
            
        elif self.args.suite == "integration":
            suites["Integration"] = base_args + ["tests/integration/"]
            
            
        elif self.args.suite == "performance":
            suites["Performance"] = base_args + ["tests/performance/"]
            
            
        elif self.args.suite == "api":
            suites["API"] = base_args + ["tests/api/"]
            
        elif self.args.suite == "streamlit":
            suites["Streamlit"] = base_args + ["tests/streamlit/"]
        
        # Add coverage if requested
        if self.args.coverage:
            for suite in suites.values():
                suite.extend(["--cov=src", "--cov-report=term-missing"])
        
        # Add specific test pattern if provided
        if self.args.pattern:
            for suite in suites.values():
                suite.extend(["-k", self.args.pattern])
        
        return suites
    
    def run(self) -> int:
        """Main test execution"""
        # Check services first
        if not self.args.skip_service_check:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q"],
                capture_output=True  # Keep this quiet since it's just a check
            )
            if result.returncode != 0:
                print("❌ Failed to collect tests. Check your environment.")
                return 1
        
        # Run tests
        results = self.run_parallel()
        
        # Generate report
        self.generate_report(results)
        
        # Return appropriate exit code
        all_passed = all(success for success, _ in results.values())
        return 0 if all_passed else 1
    
    def generate_report(self, results: Dict[str, Tuple[bool, float]]):
        """Generate test execution report"""
        total_duration = time.time() - self.start_time
        
        print(f"\n{'='*60}")
        print("📊 TEST EXECUTION REPORT")
        print(f"{'='*60}")
        
        passed = sum(1 for success, _ in results.values() if success)
        total = len(results)
        
        for suite_name, (success, duration) in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{suite_name:15} {status} ({duration:.1f}s)")
        
        print(f"\nTotal: {passed}/{total} suites passed")
        print(f"Duration: {total_duration:.1f}s")
        
        if self.args.json_report:
            report = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_duration": total_duration,
                "suites": {
                    name: {"passed": success, "duration": duration}
                    for name, (success, duration) in results.items()
                },
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "success_rate": f"{(passed/total)*100:.1f}%" if total > 0 else "0.0%"
                }
            }
            
            report_file = Path("tests/results/test_report.json")
            report_file.parent.mkdir(exist_ok=True)
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nJSON report saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Run Greg AI Playground tests")
    
    parser.add_argument(
        "--suite",
        choices=["all", "unit", "integration", "performance", "api", "streamlit"],
        default="all",
        help="Test suite to run"
    )
    
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests (image processing, etc.)"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run test suites in parallel"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=multiprocessing.cpu_count(),
        help="Number of parallel workers"
    )
    
    parser.add_argument(
        "--pattern",
        "-k",
        help="Only run tests matching this pattern"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--exitfirst",
        "-x",
        action="store_true",
        help="Exit on first failure"
    )
    
    parser.add_argument(
        "--capture",
        choices=["yes", "no"],
        default="yes",
        help="Capture stdout/stderr"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="Only run unit tests (no integration/UI)"
    )
    
    parser.add_argument(
        "--json-report",
        action="store_true",
        help="Generate JSON test report"
    )
    
    parser.add_argument(
        "--skip-service-check",
        action="store_true",
        help="Skip checking if services are running"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner(args)
    sys.exit(runner.run())


if __name__ == "__main__":
    main()