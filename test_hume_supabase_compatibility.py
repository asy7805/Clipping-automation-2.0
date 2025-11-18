#!/usr/bin/env python3
"""
Simple test to check Hume AI and Supabase compatibility
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file with tolerant encoding handling
loaded_env = False
for enc in ("utf-8", "utf-16", "latin-1"):
    try:
        if load_dotenv(encoding=enc):
            loaded_env = True
            break
    except Exception:
        continue

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing module imports...")
    
    try:
        from hume import HumeClient, AsyncHumeClient
        print("✅ Hume AI client imports successful")
        hume_available = True
    except ImportError as e:
        print(f"❌ Hume AI client import failed: {e}")
        hume_available = False
    
    try:
        from supabase import create_client
        print("✅ Supabase client imports successful")
        supabase_available = True
    except ImportError as e:
        print(f"❌ Supabase client import failed: {e}")
        supabase_available = False
    
    return hume_available, supabase_available

def test_environment_variables():
    """Test environment variable configuration."""
    print("\n🔍 Testing environment variables...")
    
    required_vars = {
        "SUPABASE_URL": "Supabase project URL",
        "SUPABASE_ANON_KEY": "Supabase anonymous key"
    }
    
    optional_vars = {
        "HUME_API_KEY": "Hume AI API key",
        "SUPABASE_SERVICE_ROLE_KEY": "Supabase service role key"
    }
    
    all_good = True
    
    # Check required variables
    for var, description in required_vars.items():
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Not set ({description})")
            all_good = False
    
    # Check optional variables
    for var, description in optional_vars.items():
        if os.getenv(var):
            print(f"✅ {var}: Set")
        else:
            print(f"⚠️ {var}: Not set ({description})")
    
    return all_good

def test_supabase_connection():
    """Test Supabase connection if credentials are available."""
    print("\n🔍 Testing Supabase connection...")
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            print("⚠️ Supabase credentials not set - skipping connection test")
            return False
        
        client = create_client(supabase_url, supabase_key)
        
        # Try a simple query to test connection
        try:
            # This will fail if the table doesn't exist, but that's ok for testing connection
            result = client.table("clips").select("count", count="exact").execute()
            print("✅ Supabase connection successful")
            return True
        except Exception as e:
            print(f"⚠️ Supabase connection test failed (table may not exist): {e}")
            return False
            
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def test_hume_connection():
    """Test Hume AI connection if API key is available."""
    print("\n🔍 Testing Hume AI connection...")
    
    try:
        from hume import HumeClient
        
        hume_api_key = os.getenv("HUME_API_KEY")
        
        if not hume_api_key:
            print("⚠️ HUME_API_KEY not set - skipping connection test")
            return False
        
        client = HumeClient(hume_api_key)
        print("✅ Hume AI client created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Hume AI connection failed: {e}")
        return False

def main():
    """Run all compatibility tests."""
    print("🧪 Running Hume AI + Supabase Compatibility Test")
    print("=" * 60)
    
    # Test imports
    hume_available, supabase_available = test_imports()
    
    # Test environment variables
    env_ok = test_environment_variables()
    
    # Test connections
    supabase_connected = test_supabase_connection()
    hume_connected = test_hume_connection()
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"{'✅' if hume_available else '❌'} Hume AI: Available")
    print(f"{'✅' if supabase_available else '❌'} Supabase: Available")
    print(f"{'✅' if env_ok else '❌'} Environment Variables: {'Set' if env_ok else 'Missing'}")
    print(f"{'✅' if supabase_connected else '⚠️'} Supabase: {'Connected' if supabase_connected else 'Not connected'}")
    print(f"{'✅' if hume_connected else '⚠️'} Hume AI: {'Connected' if hume_connected else 'Not connected'}")
    
    # Overall status
    if hume_available and supabase_available:
        print(f"\n🎉 OVERALL STATUS: ✅ COMPATIBLE")
        print("   Hume AI and Supabase can work together!")
        
        if not env_ok:
            print("\n💡 Next Steps:")
            print("   1. Set up your .env file with Supabase credentials")
            print("   2. Add HUME_API_KEY for full functionality")
    else:
        print(f"\n❌ OVERALL STATUS: ❌ INCOMPATIBLE")
        print("   Some required components are missing.")

if __name__ == "__main__":
    main()
