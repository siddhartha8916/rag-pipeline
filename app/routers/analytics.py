from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from app.services.analytics_pipeline import AnalyticsPipeline
from app.models.schemas import (
    DatabaseConnectionTest, DatabaseConnectionTestResponse,
    AnalyticsQueryRequest, AnalyticsResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
analytics_pipeline = AnalyticsPipeline()

@router.post("/test-connection", response_model=DatabaseConnectionTestResponse)
async def test_database_connection(request: DatabaseConnectionTest):
    """
    Test database connection and return available tables.
    
    Supports SQLite databases for now. More database types coming soon.
    """
    try:
        result = await analytics_pipeline.test_database_connection(request.connection)
        return result
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate", response_model=AnalyticsResponse)
async def generate_analytics(request: AnalyticsQueryRequest):
    """
    Generate analytics from natural language query.
    
    Process:
    1. Connect to the database
    2. Analyze schema and structure
    3. Convert natural language to SQL
    4. Execute query safely (SELECT only)
    5. Analyze results
    6. Generate HTML analytics page with charts
    
    Example queries:
    - "Show me all users by age group"
    - "What are the top 10 selling products?"
    - "List farmers earning less than $40 per month"
    - "Compare sales by region over time"
    """
    try:
        if not request.user_query or not request.user_query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        result = await analytics_pipeline.generate_analytics(request)
        return result
    except Exception as e:
        logger.error(f"Analytics generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-html")
async def generate_analytics_html(request: AnalyticsQueryRequest):
    """
    Generate analytics and return HTML content directly.
    
    This endpoint returns the HTML content as a response that can be 
    displayed directly in an iframe or new window.
    """
    try:
        if not request.user_query or not request.user_query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        result = await analytics_pipeline.generate_analytics(request)
        
        return HTMLResponse(
            content=result.html_content,
            headers={
                "Cache-Control": "no-cache",
                "Content-Type": "text/html; charset=utf-8"
            }
        )
    except Exception as e:
        logger.error(f"HTML analytics generation failed: {str(e)}")
        
        # Return error HTML
        error_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics Error</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-red-900 text-white flex items-center justify-center min-h-screen">
    <div class="text-center">
        <h1 class="text-2xl font-bold mb-4">Analytics Generation Failed</h1>
        <p class="text-red-200">{str(e)}</p>
        <button onclick="window.history.back()" class="mt-4 bg-red-700 hover:bg-red-600 px-4 py-2 rounded">
            Go Back
        </button>
    </div>
</body>
</html>"""
        
        return HTMLResponse(
            content=error_html,
            status_code=500,
            headers={"Content-Type": "text/html; charset=utf-8"}
        )

@router.post("/generate-multi-query", response_model=AnalyticsResponse)
async def generate_multi_query_analytics(request: AnalyticsQueryRequest):
    """
    Generate analytics using multi-query strategy to avoid complex JOINs.
    
    Process:
    1. Connect to the database
    2. Analyze schema and structure
    3. Generate 3-5 focused SQL queries instead of complex JOINs
    4. Execute each query safely (SELECT only)
    5. Combine results and generate comprehensive HTML analytics
    
    This endpoint is optimized for complex analytics that would otherwise
    require expensive JOIN operations that may run indefinitely.
    
    Example queries:
    - "Compare sales performance across regions with detailed breakdowns"
    - "Analyze customer behavior patterns with demographics and purchase history"
    - "Generate comprehensive business intelligence dashboard"
    """
    try:
        if not request.user_query or not request.user_query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        result = await analytics_pipeline.generate_multi_query_analytics(request)
        return result
    except Exception as e:
        logger.error(f"Multi-query analytics generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-multi-query-html")
async def generate_multi_query_analytics_html(request: AnalyticsQueryRequest):
    """
    Generate multi-query analytics and return HTML content directly.
    
    This endpoint uses focused subqueries instead of complex JOINs
    and returns comprehensive HTML dashboard content.
    """
    try:
        if not request.user_query or not request.user_query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        result = await analytics_pipeline.generate_multi_query_analytics(request)
        
        return HTMLResponse(
            content=result.html_content,
            headers={
                "Cache-Control": "no-cache",
                "Content-Type": "text/html; charset=utf-8"
            }
        )
    except Exception as e:
        logger.error(f"Multi-query HTML analytics generation failed: {str(e)}")
        
        # Return error HTML
        error_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Query Analytics Error</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-red-900 text-white flex items-center justify-center min-h-screen">
    <div class="text-center max-w-2xl mx-auto p-8">
        <h1 class="text-3xl font-bold mb-4">Multi-Query Analytics Generation Failed</h1>
        <p class="text-red-200 mb-4">{str(e)}</p>
        <div class="bg-red-800 p-4 rounded-lg mb-4">
            <p class="text-sm">This error occurred while generating focused subqueries to avoid complex JOINs.</p>
            <p class="text-sm">Try simplifying your request or using the standard analytics endpoint.</p>
        </div>
        <button onclick="window.history.back()" class="mt-4 bg-red-700 hover:bg-red-600 px-6 py-2 rounded-lg">
            Go Back
        </button>
    </div>
</body>
</html>"""
        
        return HTMLResponse(
            content=error_html,
            status_code=500,
            headers={"Content-Type": "text/html; charset=utf-8"}
        )

@router.get("/health")
async def analytics_health():
    """Check if analytics services are available."""
    try:
        # Check if LLM service is configured
        llm_configured = analytics_pipeline.llm_service.is_configured()
        
        return {
            "status": "healthy" if llm_configured else "partial",
            "llm_configured": llm_configured,
            "database_types_supported": ["sqlite"],
            "message": "Analytics service is operational" if llm_configured else "LLM service not configured"
        }
    except Exception as e:
        logger.error(f"Analytics health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "llm_configured": False,
            "error": str(e)
        }