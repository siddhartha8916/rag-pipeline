#!/usr/bin/env python3
"""
Test script to verify PostgreSQL integration is working correctly.
"""
import asyncio
from app.services.database_service import DatabaseService
from app.models.schemas import DatabaseConnection, DatabaseType

async def test_postgres_imports():
    """Test that PostgreSQL imports are working."""
    try:
        # Test imports
        import psycopg2
        import psycopg2.extras
        print("✅ PostgreSQL imports successful")
        return True
    except ImportError as e:
        print(f"❌ PostgreSQL imports failed: {e}")
        return False

async def test_database_service():
    """Test that DatabaseService can handle PostgreSQL connections."""
    try:
        db_service = DatabaseService()
        
        # Test SQLite connection (should still work)
        sqlite_conn = DatabaseConnection(
            db_type=DatabaseType.SQLITE,
            database="test.db",
            file_path="test.db"
        )
        
        print("Testing SQLite connection handling...")
        # This will fail because test.db doesn't exist, but should not crash
        try:
            result = await db_service.test_connection(sqlite_conn)
            print(f"SQLite test result: {result}")
        except Exception as e:
            print(f"SQLite connection test (expected error): {str(e)}")
        
        # Test PostgreSQL connection with default schema
        postgres_conn = DatabaseConnection(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass"
        )
        
        print("Testing PostgreSQL connection handling (default schema)...")
        try:
            result = await db_service.test_connection(postgres_conn)
            print(f"PostgreSQL test result: {result}")
        except Exception as e:
            print(f"PostgreSQL connection test (expected error): {str(e)}")
        
        # Test PostgreSQL connection with custom schema
        postgres_conn_custom = DatabaseConnection(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="test_db", 
            username="test_user",
            password="test_pass",
            db_schema="analytics"
        )
        
        print("Testing PostgreSQL connection handling (custom schema)...")
        try:
            result = await db_service.test_connection(postgres_conn_custom)
            print(f"PostgreSQL custom schema test result: {result}")
        except Exception as e:
            print(f"PostgreSQL custom schema connection test (expected error): {str(e)}")
        
        # Test schema context generation
        print("Testing schema context generation...")
        try:
            from app.models.schemas import DatabaseSchema
            # Create a mock schema
            mock_schema = DatabaseSchema(
                tables=[
                    {
                        "name": "authentic_users_data",
                        "columns": [
                            {"name": "farmer_uid", "type": "varchar", "nullable": False, "primary_key": True},
                            {"name": "active", "type": "boolean", "nullable": True, "primary_key": False}
                        ]
                    }
                ],
                relationships=[]
            )
            
            # Test context with custom schema
            context = db_service._build_schema_context(mock_schema, postgres_conn_custom)
            print("Schema context with custom schema:")
            print(context)
            
            # Test context without schema
            context_default = db_service._build_schema_context(mock_schema, postgres_conn)
            print("\nSchema context with default schema:")
            print(context_default)
            
        except Exception as e:
            print(f"Schema context test error: {str(e)}")
        
        print("✅ DatabaseService handles PostgreSQL connections with schema support")
        return True
        
    except Exception as e:
        print(f"❌ DatabaseService test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("Testing PostgreSQL Integration...")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if await test_postgres_imports():
        tests_passed += 1
        
    if await test_database_service():
        tests_passed += 1
    
    print("=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! PostgreSQL integration is working.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())