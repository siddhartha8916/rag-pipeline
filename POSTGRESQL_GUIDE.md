# PostgreSQL Support Documentation

## Overview

The RAG Pipeline now supports PostgreSQL databases in addition to SQLite. You can connect to PostgreSQL databases and perform analytics using natural language queries.

## Requirements

- PostgreSQL database (local or cloud)
- Python package: `psycopg2-binary` (already included in requirements.txt)

## Connection Examples

### Local PostgreSQL
```json
{
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "myapp_db",
  "username": "postgres",
  "password": "your_password",
  "db_schema": "public"
}
```

### Cloud PostgreSQL (Azure)
```json
{
  "db_type": "postgresql",
  "host": "myserver.postgres.database.azure.com",
  "port": 5432,
  "database": "mydatabase",
  "username": "admin@myserver",
  "password": "your_password",
  "db_schema": "public"
}
```

### Cloud PostgreSQL (AWS RDS)
```json
{
  "db_type": "postgresql", 
  "host": "mydb.123456789012.us-west-2.rds.amazonaws.com",
  "port": 5432,
  "database": "myapp",
  "username": "admin",
  "password": "your_password",
  "db_schema": "public"
}
```

### Custom Schema Example
```json
{
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "company_db",
  "username": "app_user", 
  "password": "secure_password",
  "db_schema": "sales_data"
}
```

## How to Use

### Via Web Interface

1. Navigate to the Analytics tab
2. Select "PostgreSQL" from the Database Type dropdown
3. Fill in your connection details:
   - **Host**: Your PostgreSQL server hostname/IP
   - **Port**: Usually 5432 (default)
   - **Database Name**: The specific database to connect to
   - **Username**: Your PostgreSQL username
   - **Schema**: Schema name (defaults to 'public' if left empty)
   - **Password**: Your PostgreSQL password
4. Click "Test Connection" to verify the connection
5. Once connected, ask natural language questions like:
   - "Show me all users created in the last month"
   - "What are the top 10 products by sales?"
   - "List customers with orders over $1000"

### Via API

```python
import httpx
import asyncio

async def test_postgres_connection():
    connection_data = {
        "connection": {
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "myapp_db", 
            "username": "postgres",
            "password": "password123",
            "db_schema": "public"
        }
    }
    
    # Test connection
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/analytics/test-connection",
            json=connection_data
        )
        print(f"Connection test: {response.json()}")

async def run_analytics_query():
    query_data = {
        "connection": {
            "db_type": "postgresql",
            "host": "localhost", 
            "port": 5432,
            "database": "myapp_db",
            "username": "postgres",
            "password": "password123",
            "db_schema": "analytics"
        },
        "user_query": "Show me the top 5 customers by total order value"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/analytics/query",
            json=query_data
        )
        result = response.json()
        print(f"Analytics HTML generated: {len(result['html_content'])} characters")

# Run examples
# asyncio.run(test_postgres_connection())
# asyncio.run(run_analytics_query())
```

## PostgreSQL Schemas

PostgreSQL organizes database objects into schemas, which are like namespaces. The system now supports specifying which schema to analyze.

### Schema Usage

- **Default Schema**: If no schema is specified, the system uses `public` (PostgreSQL's default schema)
- **Custom Schemas**: You can specify any schema you have access to (e.g., `sales`, `inventory`, `reporting`)
- **Schema Permissions**: Your PostgreSQL user must have SELECT permissions on the target schema
- **Automatic Resolution**: The system automatically sets PostgreSQL's `search_path` to include your specified schema, so table names in queries don't need schema qualification

### Common Schema Examples

```sql
-- List all schemas you have access to
SELECT schema_name FROM information_schema.schemata;

-- List tables in a specific schema
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'your_schema_name';
```

### Use Cases for Different Schemas

- **`public`**: Default PostgreSQL schema, commonly used for main application tables
- **`reporting`**: Often used for denormalized reporting tables and views
- **`staging`**: Used for ETL processes and temporary data
- **`analytics`**: Purpose-built for analytics workloads
- **Custom schemas**: Department-specific or feature-specific schemas

## Supported Features

### ✅ Fully Supported
- Connection testing
- Schema introspection (tables, columns, relationships)
- SELECT query execution with safety checks
- Data analysis and statistics
- HTML analytics dashboard generation
- Natural language to SQL conversion

### 🔒 Security Features
- Query sanitization (prevents DROP, DELETE, etc.)
- Read-only queries (only SELECT and WITH allowed)
- Automatic query limits to prevent large result sets
- Connection parameter validation

### 📊 Analytics Capabilities
- Automatic chart generation based on data types
- Table statistics and column analysis
- Interactive dashboards with Tailwind CSS
- Export-ready HTML reports

## Error Handling

The system gracefully handles common PostgreSQL errors:

- **Connection refused**: Check host, port, and network connectivity
- **Authentication failed**: Verify username and password
- **Database does not exist**: Ensure database name is correct
- **Permission denied**: User needs SELECT permissions on target tables
- **SSL required**: Some cloud providers require SSL connections

## Performance Considerations

- Query results are automatically limited to 1000 rows by default
- Large tables are sampled for schema analysis
- Connection pooling is not implemented (each query creates new connection)
- For production use, consider implementing connection pooling

## Migration from SQLite

If you have existing SQLite analytics, the interface remains the same. Simply:

1. Switch database type to "PostgreSQL"
2. Enter PostgreSQL connection details
3. All existing natural language queries will work with PostgreSQL

The system automatically adapts to PostgreSQL-specific SQL syntax and features.

## Troubleshooting

### Common Issues

1. **"PostgreSQL support not available"**
   - Solution: Run `pip install psycopg2-binary`

2. **"Connection refused"**  
   - Check if PostgreSQL server is running
   - Verify host and port are correct
   - Check firewall settings

3. **"Password authentication failed"**
   - Verify username and password
   - Check PostgreSQL user permissions

4. **"Database does not exist"**
   - Create the database first in PostgreSQL
   - Verify database name spelling

5. **"No tables found"**
   - Ensure user has SELECT permissions
   - Check if tables exist in 'public' schema
   - Verify connection to correct database

For additional help, check the application logs or contact support.