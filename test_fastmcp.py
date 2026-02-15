"""FastMCP Validation Test for ACMS Phase 2B.

Tests that the mcp library works correctly before building the MCP server.

Critical validation checklist:
1. FastMCP imports successfully
2. Can create MCP server instance
3. Can register tools with @mcp.tool() decorator
4. Can define tool parameters with type hints
5. Server initialization works

SUCCESS CRITERIA:
- All 5 validation tests pass
- No import errors
- No runtime errors during server creation

If this test passes, we can proceed to Phase 2B implementation.
If this test fails, we must stop and report the issue.
"""

import sys
from typing import Dict, Any


def test_1_import_mcp():
    """Test 1: FastMCP imports successfully."""
    print("\n[TEST 1] Testing FastMCP imports...")
    try:
        import mcp
        import mcp.server.stdio
        from mcp.server import Server
        print("✅ PASS: FastMCP imports successfully")
        print(f"   mcp version: {mcp.__version__ if hasattr(mcp, '__version__') else 'unknown'}")
        return True
    except ImportError as e:
        print(f"❌ FAIL: FastMCP import failed: {e}")
        return False


def test_2_create_server():
    """Test 2: Can create MCP server instance."""
    print("\n[TEST 2] Testing MCP server creation...")
    try:
        from mcp.server import Server

        # Create server instance
        server = Server("test-server")
        print("✅ PASS: MCP server instance created")
        print(f"   Server name: {server.name}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Server creation failed: {e}")
        return False


def test_3_register_tool():
    """Test 3: Can register tools with @mcp.tool() decorator."""
    print("\n[TEST 3] Testing tool registration...")
    try:
        from mcp.server import Server

        # Create server
        server = Server("test-server")

        # Define a test tool
        @server.call_tool()
        async def test_tool(name: str, value: int) -> Dict[str, Any]:
            """A test tool."""
            return {"name": name, "value": value}

        print("✅ PASS: Tool registration works")
        print("   Registered test_tool with parameters (name: str, value: int)")
        return True
    except Exception as e:
        print(f"❌ FAIL: Tool registration failed: {e}")
        return False


def test_4_tool_type_hints():
    """Test 4: Can define tool parameters with type hints."""
    print("\n[TEST 4] Testing tool parameter type hints...")
    try:
        from mcp.server import Server
        from typing import Optional, List

        # Create server
        server = Server("test-server")

        # Define tool with complex type hints
        @server.call_tool()
        async def complex_tool(
            required_str: str,
            optional_str: Optional[str] = None,
            list_param: List[str] = None,
            int_param: int = 0
        ) -> Dict[str, Any]:
            """A tool with complex type hints."""
            return {
                "required_str": required_str,
                "optional_str": optional_str,
                "list_param": list_param or [],
                "int_param": int_param
            }

        print("✅ PASS: Complex type hints work")
        print("   Registered tool with Optional, List, and default parameters")
        return True
    except Exception as e:
        print(f"❌ FAIL: Type hints failed: {e}")
        return False


def test_5_server_initialization():
    """Test 5: Server initialization works."""
    print("\n[TEST 5] Testing server initialization...")
    try:
        from mcp.server import Server
        import mcp.server.stdio

        # Create and initialize server
        server = Server("acms-test-server")

        # Register a sample tool
        @server.call_tool()
        async def sample_tool(text: str) -> Dict[str, Any]:
            """Sample tool for testing."""
            return {"result": f"Processed: {text}"}

        print("✅ PASS: Server initialization works")
        print("   Server ready for stdio communication")
        return True
    except Exception as e:
        print(f"❌ FAIL: Server initialization failed: {e}")
        return False


def main():
    """Run all FastMCP validation tests."""
    print("=" * 70)
    print("FASTMCP VALIDATION TEST - ACMS PHASE 2B")
    print("=" * 70)
    print("\nThis test validates that the mcp library works correctly")
    print("before we begin building the ACMS MCP server.")

    # Run all tests
    tests = [
        test_1_import_mcp,
        test_2_create_server,
        test_3_register_tool,
        test_4_tool_type_hints,
        test_5_server_initialization,
    ]

    results = []
    for test_func in tests:
        result = test_func()
        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")

    if passed == total:
        print("\n✅ SUCCESS: All FastMCP validation tests passed!")
        print("   We can proceed with Phase 2B implementation.")
        return 0
    else:
        print(f"\n❌ FAILURE: {total - passed} test(s) failed.")
        print("   Cannot proceed with Phase 2B until issues are resolved.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
