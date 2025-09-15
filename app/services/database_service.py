import asyncio
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import quote_plus
import logging
import time
import re
import json

try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
from app.models.schemas import DatabaseConnection, DatabaseType, QueryResult, DatabaseSchema
from app.config import settings

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for handling database connections and executing queries safely."""
    
    def __init__(self):
        self.connection_cache = {}
        
    async def test_connection(self, connection: DatabaseConnection) -> Dict[str, Any]:
        """Test database connection and return basic info."""
        try:
            if connection.db_type == DatabaseType.SQLITE:
                return await self._test_sqlite_connection(connection)
            elif connection.db_type == DatabaseType.POSTGRESQL:
                return await self._test_postgresql_connection(connection)
            else:
                return {
                    "success": False,
                    "message": f"Database type {connection.db_type} not yet supported",
                    "error": f"Currently supported: SQLite, PostgreSQL"
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Database connection failed: {error_msg}")
            return {
                "success": False,
                "message": "Failed to connect to database",
                "error": error_msg
            }
    
    async def _test_sqlite_connection(self, connection: DatabaseConnection) -> Dict[str, Any]:
        """Test SQLite database connection."""
        try:
            db_path = connection.file_path or connection.database
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Test basic connection
            cursor.execute("SELECT 1")
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            logger.info(f"Successfully connected to SQLite database: {db_path}")
            return {
                "success": True,
                "message": f"Successfully connected to SQLite database",
                "tables": tables[:20],  # Limit to first 20 tables
                "table_count": len(tables)
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"SQLite connection failed: {error_msg}")
            raise Exception(f"SQLite connection failed: {error_msg}")
    
    async def _test_postgresql_connection(self, connection: DatabaseConnection) -> Dict[str, Any]:
        """Test PostgreSQL database connection."""
        try:
            if not POSTGRES_AVAILABLE:
                raise Exception("PostgreSQL support not available. Install psycopg2-binary package.")
            
            # Build connection string
            conn_params = {
                'host': connection.host,
                'port': connection.port or 5432,
                'database': connection.database,
                'user': connection.username,
                'password': connection.password
            }
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            # Set search_path to include the specified schema
            schema_name = connection.db_schema or 'public'
            cursor.execute("SET search_path TO %s, public", (schema_name,))
            
            # Test basic connection
            cursor.execute("SELECT 1")
            
            # Get table names from specified schema (default to 'public')
            schema_name = connection.db_schema or 'public'
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_type = 'BASE TABLE'
            """, (schema_name,))
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            logger.info(f"Successfully connected to PostgreSQL database: {connection.host}:{connection.port}/{connection.database}")
            return {
                "success": True,
                "message": f"Successfully connected to PostgreSQL database",
                "tables": tables[:20],  # Limit to first 20 tables
                "table_count": len(tables)
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"PostgreSQL connection failed: {error_msg}")
            raise Exception(f"PostgreSQL connection failed: {error_msg}")
    
    async def get_database_schema(self, connection: DatabaseConnection) -> DatabaseSchema:
        """Get comprehensive database schema information."""
        try:
            if connection.db_type == DatabaseType.SQLITE:
                return await self._get_sqlite_schema(connection)
            elif connection.db_type == DatabaseType.POSTGRESQL:
                return await self._get_postgresql_schema(connection)
            else:
                raise Exception(f"Database type {connection.db_type} not yet supported")
                
        except Exception as e:
            logger.error(f"Failed to get database schema: {str(e)}")
            raise Exception(f"Failed to retrieve database schema: {str(e)}")
    
    async def _get_sqlite_schema(self, connection: DatabaseConnection) -> DatabaseSchema:
        """Get SQLite database schema."""
        try:
            db_path = connection.file_path or connection.database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            tables = []
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            for table_name in table_names:
                # Get column information
                cursor.execute(f"PRAGMA table_info({table_name})")
                column_info = cursor.fetchall()
                
                columns = []
                for col in column_info:
                    columns.append({
                        "name": col[1],  # column name
                        "type": col[2],  # column type
                        "nullable": not col[3],  # not null flag (inverted)
                        "primary_key": bool(col[5])  # primary key flag
                    })
                
                tables.append({
                    "name": table_name,
                    "columns": columns
                })
            
            # Get foreign key relationships
            relationships = []
            for table_name in table_names:
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fk_info = cursor.fetchall()
                
                for fk in fk_info:
                    relationships.append({
                        "from_table": table_name,
                        "from_column": fk[3],  # from column
                        "to_table": fk[2],     # to table
                        "to_column": fk[4]     # to column
                    })
            
            conn.close()
            
            return DatabaseSchema(tables=tables, relationships=relationships)
            
        except Exception as e:
            logger.error(f"Failed to get SQLite schema: {str(e)}")
            raise Exception(f"Failed to get SQLite schema: {str(e)}")
    
    async def _get_postgresql_schema(self, connection: DatabaseConnection) -> DatabaseSchema:
        """Get PostgreSQL database schema."""
        try:
            if not POSTGRES_AVAILABLE:
                raise Exception("PostgreSQL support not available. Install psycopg2-binary package.")
            
            # Build connection string
            conn_params = {
                'host': connection.host,
                'port': connection.port or 5432,
                'database': connection.database,
                'user': connection.username,
                'password': connection.password
            }
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            # Set search_path to include the specified schema
            schema_name = connection.db_schema or 'public'
            cursor.execute("SET search_path TO %s, public", (schema_name,))
            
            tables = []
            
            # Get all table names from specified schema (default to 'public')
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_type = 'BASE TABLE'
            """, (schema_name,))
            table_names = [row[0] for row in cursor.fetchall()]
            
            for table_name in table_names:
                # Get column information
                cursor.execute("""
                    SELECT 
                        column_name, 
                        data_type, 
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    AND table_schema = %s
                    ORDER BY ordinal_position
                """, (table_name, schema_name))
                
                column_info = cursor.fetchall()
                
                # Get primary key information
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND tc.table_name = %s
                        AND tc.table_schema = %s
                """, (table_name, schema_name))
                
                primary_keys = [row[0] for row in cursor.fetchall()]
                
                columns = []
                for col in column_info:
                    columns.append({
                        "name": col[0],  # column name
                        "type": col[1],  # data type
                        "nullable": col[2] == 'YES',  # is_nullable
                        "primary_key": col[0] in primary_keys,
                        "default": col[3]  # column_default
                    })
                
                tables.append({
                    "name": table_name,
                    "columns": columns
                })
            
            # Get foreign key relationships
            relationships = []
            cursor.execute("""
                SELECT
                    tc.table_name as from_table,
                    kcu.column_name as from_column,
                    ccu.table_name AS to_table,
                    ccu.column_name AS to_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = %s
            """, (schema_name,))
            
            fk_info = cursor.fetchall()
            for fk in fk_info:
                relationships.append({
                    "from_table": fk[0],
                    "from_column": fk[1],
                    "to_table": fk[2],
                    "to_column": fk[3]
                })
            
            conn.close()
            
            return DatabaseSchema(tables=tables, relationships=relationships)
            
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL schema: {str(e)}")
            raise Exception(f"Failed to get PostgreSQL schema: {str(e)}")
    
    def _sanitize_query(self, query: str) -> str:
        """Basic query sanitization to prevent harmful operations."""
        # Remove comments
        query = re.sub(r'--.*?\n', '\n', query)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        
        # Convert to uppercase for checking
        query_upper = query.upper().strip()
        
        # Check for dangerous operations
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 
            'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'EXEC', 
            'EXECUTE', 'SHUTDOWN', 'RESTORE', 'BACKUP'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise ValueError(f"Query contains potentially dangerous keyword: {keyword}")
        
        # Ensure query starts with SELECT
        if not query_upper.startswith('SELECT') and not query_upper.startswith('WITH'):
            raise ValueError("Only SELECT and WITH queries are allowed")
        
        return query.strip()
    
    async def execute_query(self, connection: DatabaseConnection, query: str, limit: int = 1000) -> QueryResult:
        """Execute a SELECT query safely and return results."""
        try:
            if connection.db_type == DatabaseType.SQLITE:
                return await self._execute_sqlite_query(connection, query, limit)
            elif connection.db_type == DatabaseType.POSTGRESQL:
                return await self._execute_postgresql_query(connection, query, limit)
            else:
                raise Exception(f"Database type {connection.db_type} not yet supported")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query execution failed: {error_msg}")
            raise Exception(f"Query execution failed: {error_msg}")
    
    async def _execute_sqlite_query(self, connection: DatabaseConnection, query: str, limit: int) -> QueryResult:
        """Execute SQLite query."""
        try:
            # Sanitize the query
            safe_query = self._sanitize_query(query)
            
            # Add LIMIT if not present
            if 'LIMIT' not in safe_query.upper() and limit > 0:
                # Remove trailing semicolon if present
                if safe_query.rstrip().endswith(';'):
                    safe_query = safe_query.rstrip()[:-1].rstrip()
                safe_query += f" LIMIT {limit}"
            
            db_path = connection.file_path or connection.database
            start_time = time.time()
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute(safe_query)
            results = cursor.fetchall()
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            conn.close()
            
            execution_time = time.time() - start_time
            
            logger.info(f"SQLite query executed successfully, returned {len(results)} rows in {execution_time:.2f}s")
            
            return QueryResult(
                columns=columns,
                rows=[list(row) for row in results],
                row_count=len(results),
                execution_time=execution_time
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"SQLite query execution failed: {error_msg}")
            raise Exception(f"SQLite query execution failed: {error_msg}")
    
    async def _execute_postgresql_query(self, connection: DatabaseConnection, query: str, limit: int) -> QueryResult:
        """Execute PostgreSQL query."""
        try:
            if not POSTGRES_AVAILABLE:
                raise Exception("PostgreSQL support not available. Install psycopg2-binary package.")
            
            # Sanitize the query
            safe_query = self._sanitize_query(query)
            
            # Add LIMIT if not present
            if 'LIMIT' not in safe_query.upper() and limit > 0:
                # Remove trailing semicolon if present
                if safe_query.rstrip().endswith(';'):
                    safe_query = safe_query.rstrip()[:-1].rstrip()
                safe_query += f" LIMIT {limit}"
            
            # Build connection string
            conn_params = {
                'host': connection.host,
                'port': connection.port or 5432,
                'database': connection.database,
                'user': connection.username,
                'password': connection.password
            }
            
            start_time = time.time()
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Set search_path to include the specified schema
            schema_name = connection.db_schema or 'public'
            cursor.execute("SET search_path TO %s, public", (schema_name,))
            
            cursor.execute(safe_query)
            results = cursor.fetchall()
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            conn.close()
            
            execution_time = time.time() - start_time
            
            logger.info(f"PostgreSQL query executed successfully, returned {len(results)} rows in {execution_time:.2f}s")
            
            return QueryResult(
                columns=columns,
                rows=[list(row) for row in results],
                row_count=len(results),
                execution_time=execution_time
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"PostgreSQL query execution failed: {error_msg}")
            raise Exception(f"PostgreSQL query execution failed: {error_msg}")

    async def execute_multiple_queries(
        self, 
        connection: DatabaseConnection, 
        queries: List[Dict[str, str]], 
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Execute multiple queries and return combined results."""
        try:
            results = []
            total_start_time = time.time()
            
            logger.info(f"Executing {len(queries)} queries")
            
            for i, query_info in enumerate(queries):
                query_name = query_info.get('name', f'Query {i+1}')
                query_description = query_info.get('description', '')
                sql_query = query_info.get('sql', '')
                
                if not sql_query:
                    logger.warning(f"Skipping empty query: {query_name}")
                    continue
                
                try:
                    logger.info(f"Executing query {i+1}/{len(queries)}: {query_name}")
                    
                    # Execute the query
                    query_result = await self.execute_query(connection, sql_query, limit)
                    
                    # Package the result
                    result_package = {
                        'name': query_name,
                        'description': query_description,
                        'sql': sql_query,
                        'result': {
                            'columns': query_result.columns,
                            'rows': query_result.rows,
                            'row_count': query_result.row_count,
                            'execution_time': query_result.execution_time
                        },
                        'success': True
                    }
                    
                    results.append(result_package)
                    logger.info(f"Query '{query_name}' completed: {query_result.row_count} rows in {query_result.execution_time:.2f}s")
                    
                except Exception as query_error:
                    error_msg = str(query_error)
                    logger.error(f"Query '{query_name}' failed: {error_msg}")
                    
                    # Add failed query info to results
                    result_package = {
                        'name': query_name,
                        'description': query_description,
                        'sql': sql_query,
                        'result': {
                            'columns': [],
                            'rows': [],
                            'row_count': 0,
                            'execution_time': 0
                        },
                        'success': False,
                        'error': error_msg
                    }
                    
                    results.append(result_package)
            
            total_execution_time = time.time() - total_start_time
            successful_queries = sum(1 for r in results if r['success'])
            
            logger.info(f"Multi-query execution completed: {successful_queries}/{len(queries)} successful in {total_execution_time:.2f}s")
            
            return results
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Multi-query execution failed: {error_msg}")
            raise Exception(f"Multi-query execution failed: {error_msg}")
    
    def _build_schema_context(self, schema: DatabaseSchema, connection: Optional[DatabaseConnection] = None) -> str:
        """Build a comprehensive text representation of the database schema for LLM context."""
        context_parts = ["=== COMPREHENSIVE DATABASE SCHEMA INFORMATION ==="]
        
        # Database type and schema info
        if connection:
            context_parts.append(f"Database Type: {connection.db_type.value.upper()}")
            if connection.db_type == DatabaseType.POSTGRESQL and connection.db_schema:
                schema_name = connection.db_schema
                context_parts.append(f"Schema: {schema_name}")
                if schema_name != 'public':
                    context_parts.append(f"Note: All tables are in the '{schema_name}' schema. The search_path is set to include this schema, so you can reference tables directly by name without schema qualification.")
        
        # Overview statistics
        total_tables = len(schema.tables)
        total_columns = sum(len(table['columns']) for table in schema.tables)
        total_relationships = len(schema.relationships) if schema.relationships else 0
        
        context_parts.append(f"\nDATABASE OVERVIEW:")
        context_parts.append(f"- Total Tables: {total_tables}")
        context_parts.append(f"- Total Columns: {total_columns}")
        context_parts.append(f"- Total Relationships: {total_relationships}")
        
        # Detailed table information
        context_parts.append(f"\n=== DETAILED TABLE INFORMATION ===")
        
        for i, table in enumerate(schema.tables, 1):
            table_name = table['name']
            columns = table['columns']
            
            context_parts.append(f"\n[{i}] TABLE: {table_name}")
            context_parts.append(f"    Description: Contains {len(columns)} columns")
            
            # Categorize columns by type
            pk_columns = [col for col in columns if col.get('primary_key')]
            numeric_columns = [col for col in columns if any(t in col['type'].lower() for t in ['int', 'float', 'decimal', 'numeric', 'double', 'real', 'bigint', 'smallint'])]
            text_columns = [col for col in columns if any(t in col['type'].lower() for t in ['char', 'text', 'varchar', 'string'])]
            date_columns = [col for col in columns if any(t in col['type'].lower() for t in ['date', 'time', 'timestamp'])]
            boolean_columns = [col for col in columns if 'bool' in col['type'].lower()]
            
            context_parts.append(f"    Primary Keys: {len(pk_columns)} | Numeric: {len(numeric_columns)} | Text: {len(text_columns)} | Date/Time: {len(date_columns)} | Boolean: {len(boolean_columns)}")
            
            context_parts.append("    COLUMNS:")
            for col in columns:
                pk_indicator = " 🔑 PRIMARY KEY" if col.get('primary_key') else ""
                null_indicator = " ❌ NOT NULL" if not col.get('nullable') else " ✅ NULLABLE"
                default_indicator = f" (default: {col.get('default')})" if col.get('default') else ""
                
                # Add column type category emoji
                col_type = col['type'].lower()
                if col.get('primary_key'):
                    type_emoji = "🔑"
                elif any(t in col_type for t in ['int', 'float', 'decimal', 'numeric']):
                    type_emoji = "🔢"
                elif any(t in col_type for t in ['char', 'text', 'varchar']):
                    type_emoji = "📝"
                elif any(t in col_type for t in ['date', 'time', 'timestamp']):
                    type_emoji = "📅"
                elif 'bool' in col_type:
                    type_emoji = "☑️"
                else:
                    type_emoji = "📊"
                
                context_parts.append(f"      {type_emoji} {col['name']}: {col['type']}{pk_indicator}{null_indicator}{default_indicator}")
        
        # Relationships and foreign keys
        if schema.relationships:
            context_parts.append(f"\n=== TABLE RELATIONSHIPS & FOREIGN KEYS ===")
            context_parts.append("These relationships show how tables are connected:")
            
            # Group relationships by from_table
            relationships_by_table = {}
            for rel in schema.relationships:
                from_table = rel['from_table']
                if from_table not in relationships_by_table:
                    relationships_by_table[from_table] = []
                relationships_by_table[from_table].append(rel)
            
            for table, rels in relationships_by_table.items():
                context_parts.append(f"\n  📋 {table}:")
                for rel in rels:
                    context_parts.append(f"    🔗 {rel['from_column']} → {rel['to_table']}.{rel['to_column']} (Foreign Key Relationship)")
        else:
            context_parts.append(f"\n=== TABLE RELATIONSHIPS ===")
            context_parts.append("ℹ️  No foreign key relationships found in this schema.")
        
        # Query guidelines
        context_parts.append(f"\n=== QUERY GUIDELINES FOR LLM ===")
        context_parts.append("When generating SQL queries:")
        context_parts.append("1. 📊 Use appropriate JOINs when relationships exist between tables")
        context_parts.append("2. 🔢 Prefer aggregate functions (COUNT, SUM, AVG) for numeric analysis")
        context_parts.append("3. 📅 Use date functions for time-based analysis when date columns are available")
        context_parts.append("4. 🔍 Consider WHERE clauses to filter data meaningfully")
        context_parts.append("5. 📈 Use GROUP BY for categorical analysis and ORDER BY for sorting")
        context_parts.append("6. 🚫 Remember: Only SELECT and WITH queries are allowed for security")
        
        # Available tables summary for easy reference
        context_parts.append(f"\n=== QUICK REFERENCE: AVAILABLE TABLES ===")
        for table in schema.tables:
            pk_cols = [col['name'] for col in table['columns'] if col.get('primary_key')]
            pk_info = f" (PK: {', '.join(pk_cols)})" if pk_cols else ""
            context_parts.append(f"• {table['name']}: {len(table['columns'])} columns{pk_info}")
        
        return "\n".join(context_parts)
    
    def analyze_data(self, query_result: QueryResult) -> Dict[str, Any]:
        """Analyze query result data for basic statistics."""
        try:
            if not query_result.rows:
                return {"message": "No data to analyze"}
            
            analysis = {
                "row_count": query_result.row_count,
                "column_count": len(query_result.columns),
                "columns": query_result.columns,
                "execution_time": query_result.execution_time
            }
            
            # Basic column analysis
            column_analysis = {}
            for i, column in enumerate(query_result.columns):
                values = [row[i] for row in query_result.rows if row[i] is not None]
                
                if values:
                    # Check if numeric
                    try:
                        numeric_values = [float(v) for v in values]
                        column_analysis[column] = {
                            "type": "numeric",
                            "count": len(values),
                            "null_count": query_result.row_count - len(values),
                            "min": min(numeric_values),
                            "max": max(numeric_values),
                            "avg": sum(numeric_values) / len(numeric_values)
                        }
                    except (ValueError, TypeError):
                        # Text column
                        unique_values = list(set(values))
                        column_analysis[column] = {
                            "type": "text",
                            "count": len(values),
                            "null_count": query_result.row_count - len(values),
                            "unique_count": len(unique_values),
                            "sample_values": unique_values[:5]  # First 5 unique values
                        }
            
            analysis["column_analysis"] = column_analysis
            return analysis
            
        except Exception as e:
            logger.error(f"Data analysis failed: {str(e)}")
            return {"error": f"Data analysis failed: {str(e)}"}