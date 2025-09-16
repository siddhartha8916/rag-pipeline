import uuid
import logging
from typing import Dict, Any
from app.services.database_service import DatabaseService
from app.services.llm_service import PerplexityLLM
from app.models.schemas import (
    DatabaseConnection, AnalyticsQueryRequest, AnalyticsResponse,
    DatabaseConnectionTestResponse, QueryResult
)

logger = logging.getLogger(__name__)

class AnalyticsPipeline:
    """Service that orchestrates database analytics workflow."""
    
    def __init__(self):
        self.database_service = DatabaseService()
        self.llm_service = PerplexityLLM()
    
    async def test_database_connection(self, connection: DatabaseConnection) -> DatabaseConnectionTestResponse:
        """Test database connection and return connection details."""
        try:
            result = await self.database_service.test_connection(connection)
            
            return DatabaseConnectionTestResponse(
                success=result["success"],
                message=result["message"],
                tables=result.get("tables"),
                error=result.get("error")
            )
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return DatabaseConnectionTestResponse(
                success=False,
                message="Connection test failed",
                error=str(e)
            )
    
    async def generate_analytics(self, request: AnalyticsQueryRequest) -> AnalyticsResponse:
        """
        Complete analytics pipeline:
        1. Get database schema
        2. Generate SQL from natural language
        3. Execute query
        4. Analyze data
        5. Generate HTML analytics page
        """
        try:
            session_id = request.session_id or str(uuid.uuid4())
            
            logger.info(f"Starting analytics pipeline for query: {request.user_query}")
            
            # Step 1: Get database schema
            logger.info("Getting database schema...")
            schema = await self.database_service.get_database_schema(request.connection)
            
            if not schema.tables:
                raise Exception("No tables found in the database")
            
            # Step 2: Generate SQL query from natural language
            logger.info("Generating SQL query from natural language...")
            schema_context = self.database_service._build_schema_context(schema, request.connection)
            
            try:
                sql_query = await self.llm_service.generate_sql_query(
                    request.user_query, 
                    schema_context
                )
                logger.info(f"Generated SQL: {sql_query}")
            except Exception as e:
                logger.warning(f"LLM SQL generation failed: {str(e)}, using fallback")
                # Fallback: simple query on first table (search_path handles schema)
                first_table = schema.tables[0]["name"]
                sql_query = f"SELECT * FROM {first_table} LIMIT 100"
            
            # Step 3: Execute the SQL query
            logger.info("Executing SQL query...")
            query_result = await self.database_service.execute_query(
                request.connection, 
                sql_query
            )
            
            if query_result.row_count == 0:
                logger.warning("Query returned no results")
                html_content = self._generate_no_data_html(request.user_query, sql_query)
                
                return AnalyticsResponse(
                    html_content=html_content,
                    session_id=session_id,
                    query_executed=sql_query,
                    data_summary={"row_count": 0, "message": "No data found"},
                    charts_generated=[]
                )
            
            # Step 4: Analyze the data
            logger.info("Analyzing query results...")
            data_analysis = self.database_service.analyze_data(query_result)
            
            # Step 5: Generate HTML analytics page
            logger.info("Generating analytics HTML page...")
            try:
                html_content = await self.llm_service.generate_analytics_html(
                    request.user_query,
                    {
                        "columns": query_result.columns,
                        "rows": query_result.rows,
                        "row_count": query_result.row_count
                    },
                    data_analysis,
                    schema_context
                )
            except Exception as e:
                logger.warning(f"LLM HTML generation failed: {str(e)}, using fallback")
                html_content = self._generate_fallback_html(
                    request.user_query, 
                    query_result, 
                    data_analysis, 
                    sql_query
                )
            
            # Determine chart types generated (basic heuristic)
            charts_generated = self._detect_chart_types(query_result, data_analysis)
            
            logger.info(f"Analytics pipeline completed successfully for session {session_id}")
            
            return AnalyticsResponse(
                html_content=html_content,
                session_id=session_id,
                query_executed=sql_query,
                data_summary={
                    "row_count": query_result.row_count,
                    "column_count": len(query_result.columns),
                    "execution_time": query_result.execution_time,
                    "columns": query_result.columns
                },
                charts_generated=charts_generated
            )
            
        except Exception as e:
            logger.error(f"Analytics pipeline failed: {str(e)}")
            
            # Generate error HTML
            error_html = self._generate_error_html(request.user_query, str(e))
            
            return AnalyticsResponse(
                html_content=error_html,
                session_id=request.session_id or str(uuid.uuid4()),
                query_executed="-- Error occurred before query execution",
                data_summary={"error": str(e)},
                charts_generated=[]
            )
    
    async def generate_multi_query_analytics(self, request: AnalyticsQueryRequest) -> AnalyticsResponse:
        """
        Multi-query analytics pipeline:
        1. Get database schema
        2. Generate multiple focused SQL queries (instead of complex JOINs)
        3. Execute all queries
        4. Combine results and generate comprehensive HTML analytics
        """
        try:
            session_id = request.session_id or str(uuid.uuid4())
            
            logger.info(f"Starting multi-query analytics pipeline for query: {request.user_query}")
            
            # Step 1: Get database schema
            logger.info("Getting database schema...")
            schema = await self.database_service.get_database_schema(request.connection)
            
            if not schema.tables:
                raise Exception("No tables found in the database")
            
            # Step 2: Generate multiple focused SQL queries
            logger.info("Generating multiple focused SQL queries...")
            schema_context = self.database_service._build_schema_context(schema, request.connection)
            
            try:
                queries = await self.llm_service.generate_multiple_sql_queries(
                    request.user_query, 
                    schema_context
                )
                logger.info(f"Generated {len(queries)} focused queries")
            except Exception as e:
                logger.warning(f"LLM multi-query generation failed: {str(e)}, using fallback")
                # Fallback: create simple queries from available tables
                queries = self._generate_fallback_queries(schema)
            
            # Step 3: Execute all queries
            logger.info("Executing multiple SQL queries...")
            query_results = await self.database_service.execute_multiple_queries(
                request.connection,
                queries
            )
            
            # Check if we have any successful results
            successful_results = [r for r in query_results if r.get('success', False)]
            if not successful_results:
                logger.warning("No queries executed successfully")
                html_content = self._generate_multi_query_no_data_html(request.user_query, query_results)
                
                return AnalyticsResponse(
                    html_content=html_content,
                    session_id=session_id,
                    query_executed="; ".join([q.get('sql', '') for q in queries]),
                    data_summary={
                        "total_queries": len(queries),
                        "successful_queries": 0,
                        "message": "No queries returned data"
                    },
                    charts_generated=[]
                )
            
            # Step 4: Generate comprehensive HTML analytics from multiple query results
            logger.info("Generating multi-query analytics HTML page...")
            try:
                html_content = await self.llm_service.generate_multi_query_analytics_html(
                    request.user_query,
                    query_results,
                    schema_context
                )
            except Exception as e:
                logger.warning(f"LLM multi-query HTML generation failed: {str(e)}, using fallback")
                html_content = self._generate_multi_query_fallback_html(
                    request.user_query, 
                    query_results, 
                    queries
                )
            
            # Determine chart types and data summary
            total_rows = sum(r.get('result', {}).get('row_count', 0) for r in successful_results)
            all_queries_sql = "; ".join([q.get('sql', '') for q in queries])
            
            logger.info(f"Multi-query analytics pipeline completed successfully for session {session_id}")
            
            return AnalyticsResponse(
                html_content=html_content,
                session_id=session_id,
                query_executed=all_queries_sql,
                data_summary={
                    "total_queries": len(queries),
                    "successful_queries": len(successful_results),
                    "total_rows": total_rows,
                    "queries_info": [
                        {
                            "name": q.get('name', 'Unknown'),
                            "success": q.get('success', False),
                            "rows": q.get('result', {}).get('row_count', 0)
                        } for q in query_results
                    ]
                },
                charts_generated=["multi_query_dashboard", "combined_analytics"]
            )
            
        except Exception as e:
            logger.error(f"Multi-query analytics pipeline failed: {str(e)}")
            
            # Generate error HTML
            error_html = self._generate_multi_query_error_html(request.user_query, str(e))
            
            return AnalyticsResponse(
                html_content=error_html,
                session_id=request.session_id or str(uuid.uuid4()),
                query_executed="-- Error occurred before query execution",
                data_summary={"error": str(e), "pipeline_type": "multi_query"},
                charts_generated=[]
            )
    
    def _generate_fallback_queries(self, schema) -> list:
        """Generate smart fallback queries when LLM fails."""
        queries = []
        
        # Analyze table names and create meaningful queries
        table_priorities = []
        
        for table in schema.tables:
            table_name = table["name"]
            columns = table.get("columns", [])
            
            # Prioritize tables with common analytics patterns
            priority = 0
            if any(word in table_name.lower() for word in ['activity', 'record', 'log', 'summary', 'metrics']):
                priority += 3
            if any(word in table_name.lower() for word in ['user', 'customer', 'account', 'profile']):
                priority += 2
            if any(word in table_name.lower() for word in ['transaction', 'payment', 'order', 'sale']):
                priority += 3
            if any(word in table_name.lower() for word in ['harvest', 'farm', 'produce', 'crop']):
                priority += 2
            
            # Check for date columns
            has_date_col = any('date' in col.get('name', '').lower() or 'time' in col.get('name', '').lower() 
                             for col in columns)
            if has_date_col:
                priority += 1
                
            table_priorities.append((table_name, priority, columns))
        
        # Sort by priority and take top 3-4 tables
        table_priorities.sort(key=lambda x: x[1], reverse=True)
        
        for i, (table_name, priority, columns) in enumerate(table_priorities[:4]):
            # Create more intelligent queries based on table structure
            date_columns = [col['name'] for col in columns if 'date' in col['name'].lower() or 'time' in col['name'].lower()]
            
            if date_columns and len(date_columns) > 0:
                date_col = date_columns[0]
                queries.append({
                    "name": f"Recent {table_name} Activity",
                    "description": f"Recent records from {table_name} ordered by {date_col}",
                    "sql": f"SELECT * FROM {table_name} WHERE {date_col} >= '2023-01-01' ORDER BY {date_col} DESC LIMIT 50"
                })
            else:
                queries.append({
                    "name": f"Sample {table_name} Data",
                    "description": f"Sample records from {table_name} table",
                    "sql": f"SELECT * FROM {table_name} LIMIT 50"
                })
        
        # Ensure we have at least 3 queries
        if len(queries) < 3:
            for table in schema.tables[len(queries):3]:
                queries.append({
                    "name": f"Basic {table['name']} Sample",
                    "description": f"Basic data sample from {table['name']}",
                    "sql": f"SELECT * FROM {table['name']} LIMIT 30"
                })
        
        return queries
    
    def _generate_multi_query_no_data_html(self, user_query: str, query_results: list) -> str:
        """Generate HTML for when multi-query returns no data."""
        failed_queries = [q for q in query_results if not q.get('success', False)]
        
        error_details = ""
        for i, failed in enumerate(failed_queries):
            error_details += f"""
            <div class="bg-red-800 p-3 rounded mb-2">
                <p><strong>Query {i+1}: {failed.get('name', 'Unknown')}</strong></p>
                <p class="text-sm text-red-200">Error: {failed.get('error', 'Unknown error')}</p>
            </div>
            """
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Query Analytics - No Data Found</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-6xl mx-auto">
            <h1 class="text-3xl font-bold mb-6 text-center">Multi-Query Analytics Dashboard</h1>
            
            <div class="bg-slate-800 rounded-lg p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Query Analysis</h2>
                <p class="text-slate-300 mb-4"><strong>Your Query:</strong> {user_query}</p>
                <p class="text-red-300 mb-4"><strong>Result:</strong> No data found from any queries</p>
                
                <h3 class="text-lg font-semibold mb-3 text-red-300">Query Errors:</h3>
                {error_details}
            </div>
            
            <div class="bg-blue-800 rounded-lg p-6">
                <h2 class="text-xl font-semibold mb-4">Multi-Query Strategy</h2>
                <p class="text-blue-200 mb-4">
                    The multi-query approach generates focused subqueries instead of complex JOINs
                    to avoid performance issues and infinite-running queries.
                </p>
                <p class="text-blue-200">
                    Try rephrasing your request or ensure the database contains relevant data.
                </p>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    def _generate_multi_query_fallback_html(self, user_query: str, query_results: list, queries: list) -> str:
        """Generate fallback HTML when LLM HTML generation fails."""
        
        # Build results summary
        results_html = ""
        for i, result in enumerate(query_results):
            if result.get('success', False):
                query_result = result.get('result', {})
                rows = query_result.get('rows', [])
                columns = query_result.get('columns', [])
                
                # Show first 5 rows as example
                sample_rows = ""
                for row in rows[:5]:
                    row_html = "".join([f"<td class='px-3 py-2 text-sm'>{cell}</td>" for cell in row])
                    sample_rows += f"<tr class='border-b border-slate-600'>{row_html}</tr>"
                
                column_headers = "".join([f"<th class='px-3 py-2 text-left text-sm font-medium'>{col}</th>" for col in columns])
                
                results_html += f"""
                <div class="bg-slate-800 rounded-lg p-6 mb-6">
                    <h3 class="text-lg font-semibold mb-3">{result.get('name', f'Query {i+1}')}</h3>
                    <p class="text-slate-400 mb-4">{result.get('description', '')}</p>
                    <p class="text-sm text-slate-300 mb-4">Rows: {query_result.get('row_count', 0)} | Execution Time: {query_result.get('execution_time', 0):.2f}s</p>
                    
                    <div class="overflow-x-auto">
                        <table class="w-full border-collapse">
                            <thead class="bg-slate-700">
                                <tr>{column_headers}</tr>
                            </thead>
                            <tbody>
                                {sample_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
                """
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Query Analytics Results</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-7xl mx-auto">
            <h1 class="text-3xl font-bold mb-6 text-center">Multi-Query Analytics Results</h1>
            
            <div class="bg-slate-800 rounded-lg p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Query Overview</h2>
                <p class="text-slate-300 mb-2"><strong>Your Query:</strong> {user_query}</p>
                <p class="text-slate-300"><strong>Strategy:</strong> Executed {len(queries)} focused queries to avoid complex JOINs</p>
            </div>
            
            {results_html}
            
            <div class="bg-blue-800 rounded-lg p-6 mt-6">
                <h2 class="text-xl font-semibold mb-4">About Multi-Query Analytics</h2>
                <p class="text-blue-200">
                    This approach uses multiple focused queries instead of complex JOIN operations 
                    to provide better performance and avoid infinite-running queries.
                </p>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    def _generate_multi_query_error_html(self, user_query: str, error_message: str) -> str:
        """Generate error HTML for multi-query analytics."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Query Analytics Error</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-red-900 text-white">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold mb-6 text-center">Multi-Query Analytics Error</h1>
            
            <div class="bg-red-800 rounded-lg p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Error Details</h2>
                <p class="text-red-200 mb-2"><strong>Your Query:</strong> {user_query}</p>
                <p class="text-red-200"><strong>Error:</strong> {error_message}</p>
            </div>
            
            <div class="bg-slate-800 rounded-lg p-6">
                <h2 class="text-xl font-semibold mb-4">Troubleshooting</h2>
                <ul class="list-disc list-inside text-slate-300 space-y-2">
                    <li>Check your database connection settings</li>
                    <li>Verify that your query is clear and specific</li>
                    <li>Try using the standard analytics endpoint instead</li>
                    <li>Ensure your database contains the expected data</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    def _detect_chart_types(self, query_result: QueryResult, data_analysis: Dict[str, Any]) -> list:
        """Detect what types of charts might be appropriate for the data."""
        charts = []
        
        if not query_result.columns or not query_result.rows:
            return charts
        
        column_analysis = data_analysis.get("column_analysis", {})
        numeric_columns = [col for col, analysis in column_analysis.items() 
                          if analysis.get("type") == "numeric"]
        text_columns = [col for col, analysis in column_analysis.items() 
                       if analysis.get("type") == "text"]
        
        # Suggest chart types based on data structure
        if len(numeric_columns) >= 1 and len(text_columns) >= 1:
            charts.extend(["bar_chart", "table"])
        elif len(numeric_columns) >= 2:
            charts.extend(["scatter_plot", "line_chart", "table"])
        elif len(text_columns) >= 1 and len(numeric_columns) >= 1:
            charts.extend(["pie_chart", "bar_chart", "table"])
        else:
            charts.append("table")
        
        return charts
    
    def _generate_no_data_html(self, user_query: str, sql_query: str) -> str:
        """Generate HTML for when no data is found."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics - No Data Found</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold mb-6 text-center">Analytics Dashboard</h1>
            
            <div class="bg-slate-800 rounded-lg p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Query Analysis</h2>
                <p class="text-slate-300 mb-2"><strong>Your Query:</strong> {user_query}</p>
                <p class="text-slate-300"><strong>Generated SQL:</strong></p>
                <pre class="bg-slate-700 p-3 rounded mt-2 overflow-x-auto"><code>{sql_query}</code></pre>
            </div>
            
            <div class="bg-yellow-900 border border-yellow-600 rounded-lg p-6 text-center">
                <h3 class="text-xl font-semibold mb-2 text-yellow-200">No Data Found</h3>
                <p class="text-yellow-100">The query executed successfully but returned no results. This might mean:</p>
                <ul class="list-disc list-inside mt-3 text-yellow-100 text-left">
                    <li>The table is empty</li>
                    <li>The filter conditions didn't match any records</li>
                    <li>The query needs to be adjusted</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    def _generate_error_html(self, user_query: str, error_message: str) -> str:
        """Generate HTML for when an error occurs."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics - Error</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold mb-6 text-center">Analytics Dashboard</h1>
            
            <div class="bg-slate-800 rounded-lg p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Query Analysis</h2>
                <p class="text-slate-300"><strong>Your Query:</strong> {user_query}</p>
            </div>
            
            <div class="bg-red-900 border border-red-600 rounded-lg p-6 text-center">
                <h3 class="text-xl font-semibold mb-2 text-red-200">Error Occurred</h3>
                <p class="text-red-100 mb-4">Unable to process your analytics request:</p>
                <div class="bg-red-800 p-3 rounded text-left">
                    <code class="text-red-100">{error_message}</code>
                </div>
                <p class="text-red-100 mt-4 text-sm">Please check your database connection and try again.</p>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    def _generate_fallback_html(
        self, 
        user_query: str, 
        query_result: QueryResult, 
        data_analysis: Dict[str, Any],
        sql_query: str
    ) -> str:
        """Generate a basic HTML page when LLM generation fails."""
        
        # Create basic data table
        table_rows = ""
        for row in query_result.rows[:50]:  # Limit to first 50 rows
            row_html = "<tr class='border-t border-slate-700'>"
            for cell in row:
                row_html += f"<td class='px-3 py-2 text-sm'>{cell if cell is not None else 'NULL'}</td>"
            row_html += "</tr>"
            table_rows += row_html
        
        header_html = "<tr class='bg-slate-700'>"
        for column in query_result.columns:
            header_html += f"<th class='px-3 py-2 text-left font-semibold'>{column}</th>"
        header_html += "</tr>"
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white">
    <div class="container mx-auto px-4 py-8">
        <div class="max-w-6xl mx-auto">
            <h1 class="text-3xl font-bold mb-6 text-center">Analytics Dashboard</h1>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="bg-slate-800 rounded-lg p-6 text-center">
                    <h3 class="text-lg font-semibold text-blue-400">Total Rows</h3>
                    <p class="text-2xl font-bold">{query_result.row_count}</p>
                </div>
                <div class="bg-slate-800 rounded-lg p-6 text-center">
                    <h3 class="text-lg font-semibold text-green-400">Columns</h3>
                    <p class="text-2xl font-bold">{len(query_result.columns)}</p>
                </div>
                <div class="bg-slate-800 rounded-lg p-6 text-center">
                    <h3 class="text-lg font-semibold text-purple-400">Execution Time</h3>
                    <p class="text-2xl font-bold">{query_result.execution_time:.2f}s</p>
                </div>
            </div>
            
            <div class="bg-slate-800 rounded-lg p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Query Details</h2>
                <p class="text-slate-300 mb-2"><strong>Your Request:</strong> {user_query}</p>
                <p class="text-slate-300 mb-2"><strong>Generated SQL:</strong></p>
                <pre class="bg-slate-700 p-3 rounded overflow-x-auto"><code>{sql_query}</code></pre>
            </div>
            
            <div class="bg-slate-800 rounded-lg p-6">
                <h2 class="text-xl font-semibold mb-4">Query Results</h2>
                <div class="overflow-x-auto">
                    <table class="min-w-full">
                        <thead>
                            {header_html}
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
                {f"<p class='text-sm text-slate-400 mt-4'>Showing first 50 rows of {query_result.row_count} total rows</p>" if query_result.row_count > 50 else ""}
            </div>
        </div>
    </div>
</body>
</html>"""