#!/usr/bin/env python3
"""
Test script for multi-query analytics functionality.
"""
import asyncio
import json
from app.services.llm_service import PerplexityLLM
from app.services.database_service import DatabaseService
from app.services.analytics_pipeline import AnalyticsPipeline
from app.models.schemas import DatabaseConnection, DatabaseType, AnalyticsQueryRequest

async def test_multi_query_generation():
    """Test the new multi-query generation functionality."""
    print("🧪 Testing Multi-Query Analytics Generation")
    print("=" * 50)
    
    # Initialize services
    llm_service = PerplexityLLM()
    
    # Check if API key is available
    if not llm_service.is_configured():
        print("❌ Perplexity API key not configured")
        print("Set PERPLEXITY_API_KEY environment variable to test LLM functionality")
        return
    
    # Test schema context (simplified for testing)
    schema_context = """
    Available Tables:
    1. sales_data (columns: id, product_name, category, sale_amount, sale_date, region, customer_id)
    2. customers (columns: customer_id, name, age, location, registration_date)
    3. products (columns: product_id, name, category, price, stock_quantity)
    """
    
    # Test user queries
    test_queries = [
        "Generate a comprehensive business analytics dashboard showing sales performance, customer demographics, and product popularity",
        "Analyze customer behavior patterns with purchase history and regional sales comparison",
        "Create detailed sales reports with top products and customer segments"
    ]
    
    for i, user_query in enumerate(test_queries, 1):
        print(f"\n📊 Test Query {i}:")
        print(f"Query: {user_query}")
        print("-" * 40)
        
        try:
            # Test multi-query generation
            queries = await llm_service.generate_multiple_sql_queries(user_query, schema_context)
            
            print(f"✅ Generated {len(queries)} focused queries:")
            for j, query in enumerate(queries, 1):
                print(f"\n  Query {j}: {query.get('name', 'Unknown')}")
                print(f"  Description: {query.get('description', 'No description')}")
                print(f"  SQL: {query.get('sql', 'No SQL')}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Multi-query generation test completed!")

async def test_html_generation():
    """Test multi-query HTML generation."""
    print("\n🎨 Testing Multi-Query HTML Generation")
    print("=" * 50)
    
    llm_service = PerplexityLLM()
    
    if not llm_service.is_configured():
        print("❌ Perplexity API key not configured - skipping HTML test")
        return
    
    # Mock query results
    mock_query_results = [
        {
            'name': 'Sales Performance by Region',
            'description': 'Total sales amount grouped by geographical region',
            'result': {
                'columns': ['region', 'total_sales', 'avg_sale_amount'],
                'rows': [
                    ['North', 125000, 450],
                    ['South', 98000, 380],
                    ['East', 110000, 420],
                    ['West', 87000, 360]
                ],
                'row_count': 4
            },
            'success': True
        },
        {
            'name': 'Top Products by Category',
            'description': 'Best selling products in each category',
            'result': {
                'columns': ['category', 'product_name', 'total_sold'],
                'rows': [
                    ['Electronics', 'Smartphone Pro', 2500],
                    ['Clothing', 'Winter Jacket', 1800],
                    ['Books', 'Data Science Guide', 950],
                    ['Home', 'Smart Speaker', 1200]
                ],
                'row_count': 4
            },
            'success': True
        }
    ]
    
    user_query = "Create a comprehensive business dashboard"
    
    try:
        html_content = await llm_service.generate_multi_query_analytics_html(
            user_query,
            mock_query_results,
            "Sample schema context"
        )
        
        print("✅ Multi-query HTML generated successfully!")
        print(f"HTML length: {len(html_content)} characters")
        
        # Save to file for inspection
        with open("test_multi_query_dashboard.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print("💾 HTML saved to: test_multi_query_dashboard.html")
        
    except Exception as e:
        print(f"❌ HTML generation error: {str(e)}")

async def main():
    """Run all tests."""
    try:
        await test_multi_query_generation()
        await test_html_generation()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Multi-Query Analytics Test Suite")
    asyncio.run(main())