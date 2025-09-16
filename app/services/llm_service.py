import httpx
from typing import List, Dict, Optional, Any
from app.config import settings
import logging
import json
from datetime import datetime, date
from decimal import Decimal

logger = logging.getLogger(__name__)

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle date, datetime, and decimal objects."""
    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        elif isinstance(o, Decimal):
            return float(o)
        elif hasattr(o, '__dict__'):
            return o.__dict__
        return super().default(o)

class PerplexityLLM:
    def __init__(self):
        self.api_key = settings.PERPLEXITY_API_KEY
        self.api_url = settings.PERPLEXITY_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if not self.api_key:
            logger.warning("Perplexity API key not found in environment variables")
    
    def _create_rag_prompt(self, user_query: str, context_documents: List[Dict]) -> str:
        """Create a RAG prompt with context and user query."""
        
        # Build context from retrieved documents
        context_parts = []
        for i, doc in enumerate(context_documents, 1):
            context_parts.append(f"Document {i}:\n{doc['text']}\n")
        
        context = "\n".join(context_parts)
        
        prompt = f"""You are a helpful AI assistant that answers questions based on the provided context documents. 
Use the information from the context to provide accurate and relevant answers. If the context doesn't contain 
enough information to answer the question completely, please say so.

Context Documents:
{context}

User Question: {user_query}

Please provide a comprehensive answer based on the context above. If you reference specific information, 
try to indicate which document it came from."""

        return prompt
    
    async def generate_response(
        self, 
        user_query: str, 
        context_documents: List[Dict],
        model: str = "sonar",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate a response using Perplexity API with RAG context."""
        
        try:
            if not self.api_key:
                raise Exception("Perplexity API key not configured")
            
            # Create the RAG prompt
            rag_prompt = self._create_rag_prompt(user_query, context_documents)
            
            # Prepare the request payload
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": rag_prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            # Make the API request
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                    raise Exception(f"Perplexity API error: {response.status_code}")
                
                result = response.json()
                
                # Extract the generated text
                if "choices" in result and len(result["choices"]) > 0:
                    generated_text = result["choices"][0]["message"]["content"]
                    logger.info("Successfully generated response from Perplexity")
                    return generated_text
                else:
                    logger.error(f"Unexpected response format: {result}")
                    raise Exception("Unexpected response format from Perplexity API")
                    
        except httpx.TimeoutException:
            logger.error("Timeout when calling Perplexity API")
            raise Exception("Request to Perplexity API timed out")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error when calling Perplexity API: {str(e)}")
            raise Exception(f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def generate_simple_response(
        self, 
        message: str,
        model: str = "sonar",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate a simple response without RAG context."""
        
        try:
            if not self.api_key:
                raise Exception("Perplexity API key not configured")
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                    raise Exception(f"Perplexity API error: {response.status_code}")
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    generated_text = result["choices"][0]["message"]["content"]
                    return generated_text
                else:
                    raise Exception("Unexpected response format from Perplexity API")
                    
        except Exception as e:
            logger.error(f"Error generating simple response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    def is_configured(self) -> bool:
        """Check if the Perplexity API is properly configured."""
        return bool(self.api_key)
    
    async def generate_multiple_sql_queries(self, user_query: str, schema_context: str) -> List[Dict[str, str]]:
        """Generate multiple focused SQL subqueries instead of one complex query with joins."""
        try:
            if not self.api_key:
                raise Exception("Perplexity API key not configured")
            
            prompt = f"""You are a PostgreSQL expert. Instead of creating one complex query with multiple joins, generate 3-5 focused subqueries that together answer the user's request.

=== DATABASE SCHEMA ===
{schema_context}

=== USER REQUEST ===
{user_query}

=== MULTI-QUERY STRATEGY ===

🎯 **APPROACH**: Break down the analysis into focused, independent queries:
1. **Main Analysis**: Primary table with core metrics
2. **Related Analysis 1**: First related aspect (e.g., harvests, equipment)  
3. **Related Analysis 2**: Second related aspect (e.g., inputs, workers)
4. **Trend Analysis**: Time-based patterns
5. **Summary Statistics**: High-level totals and averages

🔧 **QUERY REQUIREMENTS**:
- Each query should focus on ONE main table or simple 1-table join
- Use descriptive names for each query's purpose
- Include date filters (>= '2023-01-01') for performance
- Use reasonable LIMITs (50-200 rows)
- Avoid complex multi-table JOINs
- Each query should be independently executable

📊 **OUTPUT FORMAT**:
Return a JSON array with objects containing:
- "name": Descriptive name for the query purpose
- "description": What insights this query provides
- "sql": The actual SQL query

Example structure:
```json
[
  {{
    "name": "activity_overview",
    "description": "Main activity metrics by type and time period",
    "sql": "SELECT activity_type, COUNT(*) as total_activities FROM activities WHERE activity_date >= '2023-01-01' GROUP BY activity_type ORDER BY total_activities DESC LIMIT 100"
  }},
  {{
    "name": "harvest_analysis", 
    "description": "Harvest amounts and productivity metrics",
    "sql": "SELECT DATE_TRUNC('month', harvest_date) as month, SUM(amount) as total_harvest FROM harvests WHERE harvest_date >= '2023-01-01' GROUP BY month ORDER BY month DESC LIMIT 50"
  }}
]
```

🚨 **CRITICAL RULES**:
- Generate 3-5 complementary queries maximum
- Each query must be performance-optimized
- No complex JOINs across multiple unrelated tables
- Include proper date filters and LIMITs
- Return valid JSON format only
- Each SQL must be syntactically perfect

Generate the multi-query JSON response:"""

            payload = {
                "model": "sonar-reasoning",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.3
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_text = response.text if hasattr(response, 'text') else str(response.status_code)
                    logger.error(f"Perplexity API error {response.status_code}: {error_text}")
                    raise Exception(f"API error {response.status_code}: {error_text}")
                
                # Get response content safely
                response_text = response.text
                
                if not response_text or response_text.strip() == "":
                    logger.error("Empty response from Perplexity API")
                    raise Exception("Empty response from API")
                
                # Parse JSON response
                try:
                    result = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse API response as JSON: {e}")
                    logger.error(f"Response content: {response_text[:500]}")
                    raise Exception("Invalid JSON response from API")
                
                if "choices" in result and len(result["choices"]) > 0:
                    json_response = result["choices"][0]["message"]["content"].strip()
                    
                    if not json_response:
                        logger.error("Empty content from API choices")
                        raise Exception("Empty content from API")
                    
                    logger.info(f"Raw API response: {json_response[:200]}...")
                    
                    # Enhanced cleanup for various response formats
                    original_response = json_response
                    
                    # Remove markdown code blocks
                    if json_response.startswith('```json'):
                        json_response = json_response[7:]
                    elif json_response.startswith('```'):
                        json_response = json_response[3:]
                    
                    if json_response.endswith('```'):
                        json_response = json_response[:-3]
                    
                    # Remove any explanatory text before/after JSON
                    json_response = json_response.strip()
                    
                    # Try to find JSON array in the response
                    start_bracket = json_response.find('[')
                    end_bracket = json_response.rfind(']')
                    
                    if start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
                        json_response = json_response[start_bracket:end_bracket+1]
                    
                    try:
                        queries = json.loads(json_response)
                        
                        # Validate the structure
                        if not isinstance(queries, list):
                            logger.error(f"Response is not a list: {type(queries)}")
                            raise Exception("Response should be a JSON array")
                        
                        if len(queries) == 0:
                            logger.error("Empty query list returned")
                            raise Exception("No queries generated")
                        
                        # Validate and clean up each query
                        valid_queries = []
                        for i, query in enumerate(queries):
                            if not isinstance(query, dict):
                                logger.warning(f"Query {i} is not a dict, skipping")
                                continue
                            
                            if not all(key in query for key in ['name', 'description', 'sql']):
                                logger.warning(f"Query {i} missing required fields: {query.keys()}")
                                continue
                            
                            # Clean up SQL
                            sql = query['sql'].strip()
                            if sql.endswith(';'):
                                sql = sql[:-1]
                            query['sql'] = sql
                            
                            valid_queries.append(query)
                        
                        if not valid_queries:
                            raise Exception("No valid queries found in response")
                        
                        logger.info(f"Successfully generated {len(valid_queries)} focused SQL queries")
                        return valid_queries
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        logger.error(f"Original response: {original_response[:500]}")
                        logger.error(f"Cleaned JSON content: {json_response}")
                        raise Exception(f"Invalid JSON response from API: {e}")
                    
                else:
                    logger.error(f"Unexpected API response structure: {result}")
                    raise Exception("Unexpected response format from API")
                    
        except Exception as e:
            logger.error(f"Error generating multiple SQL queries: {str(e)}")
            raise Exception(f"Failed to generate multiple SQL queries: {str(e)}")

    async def generate_sql_query(self, user_query: str, schema_context: str) -> str:
        """Generate enhanced SQL query from natural language using comprehensive database schema."""
        try:
            if not self.api_key:
                raise Exception("Perplexity API key not configured")
            
            # Enhanced prompt with strict PostgreSQL syntax rules
            prompt = f"""You are a PostgreSQL expert. Generate a syntactically perfect SELECT query based on the user's request.

=== DATABASE SCHEMA ===
{schema_context}

=== USER REQUEST ===
{user_query}

=== POSTGRESQL SYNTAX RULES (CRITICAL) ===

🚨 **MANDATORY SYNTAX REQUIREMENTS**:
1. **Column Names**: Use EXACT column names from schema (case-sensitive)
2. **Table Names**: Use EXACT table names from schema
3. **Parentheses**: Balance ALL opening/closing parentheses
4. **Commas**: No trailing commas in SELECT, GROUP BY, or ORDER BY clauses
5. **Keywords**: Use proper PostgreSQL keywords (SELECT, FROM, WHERE, GROUP BY, ORDER BY, LIMIT)
6. **Aggregations**: COUNT(*), SUM(column), AVG(column), MIN(column), MAX(column)
7. **String Literals**: Use single quotes 'value' not double quotes
8. **Date Literals**: Use 'YYYY-MM-DD' format for dates

🔧 **POSTGRESQL SPECIFIC FEATURES**:
- Use DATE_TRUNC('month', date_column) for date grouping
- Use CASE WHEN for conditional logic
- Use proper JOIN syntax: INNER JOIN, LEFT JOIN
- Use LIMIT without OFFSET for simple limits
- Use proper NULL handling with IS NULL / IS NOT NULL

⚡ **PERFORMANCE & JOIN OPTIMIZATION RULES**:
- **AVOID MULTIPLE INDEPENDENT LEFT JOINs**: Can cause Cartesian products
- **PREFER SINGLE TABLE QUERIES**: When possible, use one main table
- **LIMITED JOINS**: Maximum 2-3 JOINs per query to prevent performance issues
- **PROPER JOIN CONDITIONS**: Always include specific join conditions (ON clause)
- **FILTER EARLY**: Use WHERE clauses to limit data before JOINs
- **AVOID CROSS JOINS**: Never create unfiltered cross products
- **DATE FILTERS**: Always include reasonable date ranges (e.g., last 2 years)
- **LIMIT RESULTS**: Use LIMIT 50-200 to prevent large result sets

� **QUERY STRUCTURE TEMPLATE**:
```
SELECT 
    column1,
    column2,
    COUNT(*) as count_total,
    SUM(numeric_column) as sum_total
FROM table_name
WHERE condition = 'value'
GROUP BY column1, column2
ORDER BY count_total DESC
LIMIT 100
```

⚠️ **COMMON SYNTAX ERRORS TO AVOID**:
- Missing commas between SELECT items
- Trailing commas before FROM clause
- Unbalanced parentheses in CASE statements
- Using columns in SELECT that aren't in GROUP BY (unless aggregated)
- Mixing single and double quotes
- Incorrect date format strings

🎯 **VALIDATION CHECKLIST**:
1. ✅ All parentheses are balanced ( )
2. ✅ All commas are properly placed (no trailing commas)
3. ✅ Column names exist in the provided schema
4. ✅ Table names exist in the provided schema
5. ✅ GROUP BY includes all non-aggregated SELECT columns
6. ✅ String values use single quotes
7. ✅ Query starts with SELECT and ends cleanly

💡 **OPTIMIZED QUERY EXAMPLES**:

-- ✅ GOOD: Simple single-table query
SELECT 
    activity_type,
    DATE_TRUNC('month', activity_date) as month,
    COUNT(*) as total_activities,
    AVG(household_total_hrs_spent) as avg_hours
FROM activities
WHERE activity_date >= '2023-01-01'
GROUP BY activity_type, month
ORDER BY month DESC, total_activities DESC
LIMIT 100

-- ✅ GOOD: Simple join with proper conditions
SELECT 
    a.activity_type,
    COUNT(a.activity_id) as activities,
    COUNT(h.id) as harvest_count,
    AVG(h.amount) as avg_harvest
FROM activities a
LEFT JOIN activity_harvesting_produce h ON a.activity_id = h.activity_id
WHERE a.activity_date >= '2023-01-01'
GROUP BY a.activity_type
ORDER BY activities DESC
LIMIT 50

-- 🚫 AVOID: Multiple independent joins (creates Cartesian product)
-- SELECT ... FROM table1 t1
-- LEFT JOIN table2 t2 ON t1.id = t2.foreign_id1
-- LEFT JOIN table3 t3 ON t1.id = t3.foreign_id2
-- LEFT JOIN table4 t4 ON t1.id = t4.foreign_id3
-- This creates: records1 × records2 × records3 × records4

-- ✅ ALTERNATIVE: Use subqueries or separate analyses
SELECT 
    activity_type,
    COUNT(*) as activities,
    (SELECT COUNT(*) FROM harvests h WHERE h.activity_type = a.activity_type) as harvest_count
FROM activities a
WHERE activity_date >= '2023-01-01'
GROUP BY activity_type
LIMIT 50
```

🚨 **CRITICAL OUTPUT REQUIREMENTS**:
- Return ONLY the SQL query
- NO explanations, comments, or markdown
- NO code block markers (```)
- Ensure perfect PostgreSQL syntax
- AVOID multiple independent LEFT JOINs
- Include reasonable date filters (e.g., >= '2023-01-01')
- Use LIMIT to prevent large result sets
- Test mentally for performance issues before outputting

🛡️ **PERFORMANCE CHECKLIST**:
1. ✅ Query uses maximum 2-3 tables
2. ✅ All JOINs have proper ON conditions
3. ✅ WHERE clause includes date filters
4. ✅ LIMIT is reasonable (50-200 rows)
5. ✅ No Cartesian products possible
6. ✅ No unnecessary complex aggregations across unrelated tables

Generate a syntactically perfect PostgreSQL SELECT query:"""

            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1500,  # Increased for more complex queries
                "temperature": 0.3   # Lower temperature for more precise SQL
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:  # Increased timeout
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_text = response.text if hasattr(response, 'text') else str(response.status_code)
                    logger.error(f"Perplexity API error {response.status_code}: {error_text}")
                    raise Exception(f"API error {response.status_code}: {error_text}")
                
                result = response.json()
                logger.debug(f"API Response: {result}")
                
                if "choices" in result and len(result["choices"]) > 0:
                    sql_query = result["choices"][0]["message"]["content"].strip()
                    
                    if not sql_query:
                        raise Exception("Empty response from API")
                    
                    # Enhanced cleanup of the response
                    original_query = sql_query
                    
                    # Remove code block markers
                    if sql_query.startswith('```sql'):
                        sql_query = sql_query[6:]
                    elif sql_query.startswith('```'):
                        sql_query = sql_query[3:]
                    
                    if sql_query.endswith('```'):
                        sql_query = sql_query[:-3]
                    
                    # Enhanced query extraction and cleanup
                    lines = sql_query.strip().split('\n')
                    query_lines = []
                    in_query = False
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Skip empty lines, comments, and markdown markers
                        if not line or line.startswith('--') or line.startswith('```'):
                            continue
                            
                        # Start capturing when we see SELECT
                        if line.upper().startswith('SELECT'):
                            in_query = True
                        
                        # Add line to query if we're in the query block
                        if in_query:
                            # Stop if we encounter markdown end markers or non-SQL content
                            if line.startswith('```') or (not line.upper().startswith(('SELECT', 'FROM', 'WHERE', 'GROUP', 'ORDER', 'LIMIT', 'HAVING', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'AND', 'OR', 'AS', 'ON', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DATE_TRUNC', 'DISTINCT', 'IS', 'NULL', 'NOT')) and not line.replace(' ', '').replace(',', '').replace('(', '').replace(')', '').replace("'", '').replace('-', '').replace('_', '').replace('.', '').isalnum()):
                                break
                            query_lines.append(line)
                        
                        # Stop at semicolon or when we hit obvious non-SQL content
                        if line.endswith(';') and in_query:
                            break
                    
                    final_query = '\n'.join(query_lines).strip()
                    
                    # Additional cleanup - remove any remaining markdown markers
                    final_query = final_query.replace('```sql', '').replace('```', '').strip()
                    
                    # Remove trailing semicolon if present
                    if final_query.endswith(';'):
                        final_query = final_query[:-1]
                    
                    # Enhanced validation
                    if not final_query or not final_query.upper().startswith('SELECT'):
                        logger.warning(f"Invalid query generated. Original: {original_query}")
                        raise Exception("Generated query is invalid or empty")
                    
                    # Enhanced syntax validation
                    validation_errors = []
                    
                    # Check for markdown markers that might have slipped through
                    if '```' in final_query:
                        validation_errors.append("Contains markdown code block markers (```)")
                    
                    # Check for balanced parentheses
                    open_count = final_query.count('(')
                    close_count = final_query.count(')')
                    if open_count != close_count:
                        validation_errors.append(f"Unbalanced parentheses: {open_count} opening, {close_count} closing")
                    
                    # Check for trailing commas (common SQL error)
                    lines_to_check = final_query.split('\n')
                    for i, line in enumerate(lines_to_check):
                        line = line.strip()
                        if line.endswith(','):
                            next_line = lines_to_check[i + 1].strip().upper() if i + 1 < len(lines_to_check) else ""
                            if next_line.startswith(('FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING')):
                                validation_errors.append(f"Trailing comma before {next_line}")
                    
                    # Check for required clauses
                    upper_query = final_query.upper()
                    if 'SELECT' not in upper_query:
                        validation_errors.append("Missing SELECT clause")
                    if 'FROM' not in upper_query:
                        validation_errors.append("Missing FROM clause")
                    
                    # Check for common non-SQL content that might indicate incomplete extraction
                    problematic_patterns = ['explanation:', 'note:', 'this query', 'the above', 'result:', 'output:']
                    for pattern in problematic_patterns:
                        if pattern.lower() in final_query.lower():
                            validation_errors.append(f"Contains explanatory text: '{pattern}'")
                    
                    # Check for performance-problematic patterns
                    join_count = final_query.upper().count('LEFT JOIN') + final_query.upper().count('INNER JOIN') + final_query.upper().count('RIGHT JOIN')
                    if join_count > 3:
                        validation_errors.append(f"Too many JOINs ({join_count}) - may cause performance issues")
                    
                    # Check for date filters to prevent full table scans
                    if 'WHERE' in upper_query and 'date' in final_query.lower() and not any(year in final_query for year in ['2020', '2021', '2022', '2023', '2024', '2025']):
                        validation_errors.append("Missing recent date filter - may cause slow query performance")
                    
                    # Check for reasonable LIMIT
                    if 'LIMIT' in upper_query:
                        try:
                            limit_match = __import__('re').search(r'LIMIT\s+(\d+)', upper_query)
                            if limit_match and int(limit_match.group(1)) > 1000:
                                validation_errors.append("LIMIT too high (>1000) - may cause performance issues")
                        except:
                            pass
                    
                    if validation_errors:
                        logger.warning(f"SQL validation errors detected: {'; '.join(validation_errors)}")
                        logger.info("Attempting to correct SQL syntax errors...")
                        
                        try:
                            # Try to correct the SQL query
                            error_msg = '; '.join(validation_errors)
                            corrected_query = await self.correct_sql_query(final_query, error_msg, schema_context)
                            
                            # Re-validate the corrected query
                            corrected_validation_errors = []
                            
                            # Check parentheses balance again
                            corrected_open_count = corrected_query.count('(')
                            corrected_close_count = corrected_query.count(')')
                            if corrected_open_count != corrected_close_count:
                                corrected_validation_errors.append(f"Still unbalanced parentheses: {corrected_open_count} opening, {corrected_close_count} closing")
                            
                            # Check for trailing commas again
                            corrected_lines = corrected_query.split('\n')
                            for i, line in enumerate(corrected_lines):
                                line = line.strip()
                                if line.endswith(','):
                                    next_line = corrected_lines[i + 1].strip().upper() if i + 1 < len(corrected_lines) else ""
                                    if next_line.startswith(('FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING')):
                                        corrected_validation_errors.append(f"Still has trailing comma before {next_line}")
                            
                            if corrected_validation_errors:
                                logger.error(f"Correction failed, still has errors: {'; '.join(corrected_validation_errors)}")
                                raise Exception(f"Generated SQL has uncorrectable syntax errors: {'; '.join(validation_errors)}")
                            
                            logger.info("Successfully corrected SQL syntax errors")
                            return corrected_query
                            
                        except Exception as correction_error:
                            logger.error(f"SQL correction failed: {str(correction_error)}")
                            raise Exception(f"Generated SQL has syntax errors and correction failed: {'; '.join(validation_errors)}")
                    
                    logger.info(f"Successfully generated and validated SQL query: {final_query[:100]}...")
                    return final_query
                    
                else:
                    logger.error(f"Unexpected API response format: {result}")
                    raise Exception("Unexpected response format from API")
                    
        except httpx.TimeoutException:
            logger.error("Timeout when calling Perplexity API for SQL generation")
            raise Exception("SQL generation request timed out")
        except httpx.HTTPError as http_err:
            logger.error(f"HTTP error during SQL generation: {str(http_err)}")
            raise Exception(f"HTTP error: {str(http_err)}")
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON decode error in SQL generation: {str(json_err)}")
            raise Exception(f"Invalid JSON response: {str(json_err)}")
        except Exception as e:
            logger.error(f"Error generating SQL query: {str(e)}")
            raise Exception(f"Failed to generate SQL query: {str(e)}")
    
    async def correct_sql_query(self, faulty_sql: str, error_message: str, schema_context: str) -> str:
        """Correct a faulty SQL query by asking LLM to fix syntax errors while preserving table/column names."""
        try:
            if not self.api_key:
                raise Exception("Perplexity API key not configured")
            
            prompt = f"""You are a PostgreSQL syntax expert. The following SQL query has syntax errors. Fix ONLY the syntax errors while keeping ALL table names and column names EXACTLY as they are.

=== ORIGINAL QUERY (WITH SYNTAX ERRORS) ===
{faulty_sql}

=== ERROR MESSAGE ===
{error_message}

=== DATABASE SCHEMA (FOR REFERENCE) ===
{schema_context}

=== CORRECTION RULES ===
🚨 **CRITICAL: DO NOT CHANGE**:
- Table names (keep exactly as written)
- Column names (keep exactly as written)
- The overall query logic and intent

✅ **ONLY FIX THESE SYNTAX ISSUES**:
- Remove markdown code block markers (``` or ```sql)
- Balance parentheses: ensure ( and ) match
- Remove trailing commas before FROM, WHERE, GROUP BY, ORDER BY
- Fix missing commas between SELECT columns
- Correct quote usage (single quotes for strings)
- Fix CASE WHEN syntax
- Repair JOIN syntax
- Fix GROUP BY clause issues
- Correct ORDER BY syntax
- Remove explanatory text or comments

🔧 **COMMON FIXES**:
- Remove markdown: ```sql SELECT... → SELECT...
- Remove comma before FROM: `column1, column2,` → `column1, column2`
- Balance parentheses: `(expression))` → `(expression)`
- Fix CASE syntax: `CASE column WHEN value THEN result END`
- Proper GROUP BY: Include all non-aggregated SELECT columns
- Remove explanations: Remove any text that's not part of SQL

⚡ **OUTPUT REQUIREMENTS**:
- Return ONLY the corrected SQL query
- NO explanations or comments
- NO code block markers
- Keep the same logical structure
- Preserve all original names

Example correction:
```
WRONG: SELECT col1, col2, FROM table WHERE (condition))
RIGHT: SELECT col1, col2 FROM table WHERE (condition)
```

Corrected SQL Query:"""

            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.1  # Very low temperature for precise corrections
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_text = response.text if hasattr(response, 'text') else str(response.status_code)
                    logger.error(f"Perplexity API error during SQL correction {response.status_code}: {error_text}")
                    raise Exception(f"API error {response.status_code}: {error_text}")
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    corrected_sql = result["choices"][0]["message"]["content"].strip()
                    
                    if not corrected_sql:
                        raise Exception("Empty corrected SQL response from API")
                    
                    # Enhanced cleanup of the corrected response
                    if corrected_sql.startswith('```sql'):
                        corrected_sql = corrected_sql[6:]
                    elif corrected_sql.startswith('```'):
                        corrected_sql = corrected_sql[3:]
                    
                    if corrected_sql.endswith('```'):
                        corrected_sql = corrected_sql[:-3]
                    
                    # Remove any remaining markdown markers throughout the query
                    corrected_sql = corrected_sql.replace('```sql', '').replace('```', '').strip()
                    
                    # Split into lines and clean each line
                    lines = corrected_sql.split('\n')
                    clean_lines = []
                    
                    for line in lines:
                        line = line.strip()
                        # Skip empty lines and lines that are just markdown or comments
                        if not line or line.startswith('```') or line.startswith('--'):
                            continue
                        clean_lines.append(line)
                    
                    corrected_sql = '\n'.join(clean_lines)
                    
                    # Remove trailing semicolon if present
                    if corrected_sql.endswith(';'):
                        corrected_sql = corrected_sql[:-1]
                    
                    # Basic validation
                    if not corrected_sql.upper().startswith('SELECT'):
                        logger.warning(f"Corrected query doesn't start with SELECT: {corrected_sql}")
                        raise Exception("Corrected query is not a valid SELECT statement")
                    
                    logger.info(f"Successfully corrected SQL query: {corrected_sql[:100]}...")
                    return corrected_sql
                    
                else:
                    logger.error(f"Unexpected API response format during correction: {result}")
                    raise Exception("Unexpected response format from API")
                    
        except Exception as e:
            logger.error(f"Error correcting SQL query: {str(e)}")
            raise Exception(f"Failed to correct SQL query: {str(e)}")
    
    async def generate_analytics_html(
        self, 
        user_query: str, 
        query_result: Dict[str, Any], 
        data_analysis: Dict[str, Any],
        schema_context: Optional[str] = None
    ) -> str:
        """Generate a comprehensive HTML analytics page with charts and detailed insights."""
        try:
            if not self.api_key:
                raise Exception("Perplexity API key not configured")
            
            # Prepare data context with enhanced error handling
            columns = query_result.get('columns', [])
            rows = query_result.get('rows', [])
            row_count = len(rows)
            
            logger.info(f"Preparing HTML generation for {row_count} rows with columns: {columns}")
            
            # More comprehensive sample data (up to 20 rows for better context)
            sample_data = rows[:20] if rows else []
            
            # Convert any problematic data types in sample_data
            processed_sample_data = []
            for row in sample_data:
                if isinstance(row, (list, tuple)):
                    processed_row = []
                    for item in row:
                        if isinstance(item, (date, datetime)):
                            processed_row.append(item.isoformat())
                        elif isinstance(item, Decimal):
                            processed_row.append(float(item))
                        else:
                            processed_row.append(item)
                    processed_sample_data.append(processed_row)
                else:
                    processed_sample_data.append(row)
            
            # Enhance prompt with schema context
            schema_section = f"\n\nDatabase Schema Context:\n{schema_context}" if schema_context else ""
            
            prompt = f"""CRITICAL: Create a CHART-ONLY dashboard with ZERO TABLES. You are FORBIDDEN from creating any HTML tables (<table>, <tr>, <td> tags). Only generate visual charts, metrics cards, and insights.

=== USER QUERY ===
{user_query}

=== DATASET ANALYSIS ===
Columns: {columns}
Total Records: {row_count}
Sample Data: {processed_sample_data}

Data Analysis: {json.dumps(data_analysis, indent=2, cls=CustomJSONEncoder)}
{schema_section}

=== CRITICAL REQUIREMENTS ===
⚠️ ABSOLUTE PROHIBITION: NO HTML TABLES ALLOWED WHATSOEVER
🚫 BANNED: <table>, <thead>, <tbody>, <tr>, <td>, <th> tags
🚫 BANNED: Any tabular data display or raw data rows  
🚫 BANNED: Showing sample data in table format
✅ REQUIRED: Only visual charts, graphs, and insights
✅ TRANSFORM RAW DATA INTO VISUAL STORIES

📊 MANDATORY CHART TYPES (Choose 2-4 based on data):
1. **Bar/Column Charts**: For categorical comparisons, rankings, distributions
2. **Line Charts**: For trends, time series, performance over periods
3. **Pie/Doughnut Charts**: For proportions, market share, category breakdown
4. **Scatter Plots**: For correlations, relationships between variables
5. **Area Charts**: For cumulative trends, stacked categories over time

📈 VISUALIZATION STRATEGY:
- Analyze the data structure and choose appropriate chart types
- Create meaningful aggregations (COUNT, SUM, AVG, etc.)
- Group data logically for better insights
- Show trends, patterns, and outliers
- Highlight key findings with callout boxes

🎯 MANDATORY STRUCTURE (NO TABLES):
1. **Header**: Dashboard title + key metric summary cards
2. **Charts Grid**: 2-4 Chart.js visualizations (bar, pie, line charts)
3. **Insights Box**: Key findings in colored callout sections
4. **Recommendations**: Action items in highlight boxes

EXAMPLE OUTPUT STRUCTURE:
```html
<!-- Metrics Cards (NOT tables) -->
<div class="grid grid-cols-4 gap-4 mb-8">
  <div class="bg-slate-800 p-4 rounded text-center">
    <h4 class="text-blue-400">Total Activities</h4>
    <p class="text-2xl font-bold">25,402</p>
  </div>
</div>

<!-- Charts (NOT tables) -->
<div class="grid grid-cols-2 gap-6">
  <div class="bg-slate-800 p-6 rounded">
    <h3>Activity Distribution</h3>
    <canvas id="pieChart"></canvas>
  </div>
  <div class="bg-slate-800 p-6 rounded">
    <h3>Labor Hours Comparison</h3>
    <canvas id="barChart"></canvas>
  </div>
</div>

<!-- Insights (NOT raw data) -->
<div class="bg-blue-900/30 border border-blue-500 rounded p-6">
  <h3 class="text-blue-400">🔍 Key Insights</h3>
  <ul>
    <li>• Weeding activities dominate (17% of total)</li>
    <li>• Harvesting requires most labor per activity</li>
  </ul>
</div>
```

💡 DATA PROCESSING EXAMPLES:
- Group by categories and show counts/sums
- Calculate percentages and growth rates
- Find top/bottom performers
- Identify trends and seasonality
- Compare segments or time periods

🎨 TECHNICAL IMPLEMENTATION:
- Use Chart.js v4 with professional color schemes
- Implement responsive design with CSS Grid/Flexbox
- Add hover interactions and tooltips
- Use Tailwind CSS dark theme (bg-gray-900, text-white)
- Include smooth animations and transitions

� RESPONSIVE DESIGN:
- Mobile-first approach
- Charts adapt to screen size
- Readable fonts and spacing
- Touch-friendly interactions

🔧 CHART CONFIGURATION:
```javascript
// Example structure for charts
const chartData = {{
    labels: [...], // Extract from your data
    datasets: [{{
        label: '...',
        data: [...], // Process the sample data
        backgroundColor: [...], // Professional color palette
        borderColor: [...],
        borderWidth: 2
    }}]
}};

const chartOptions = {{
    responsive: true,
    plugins: {{
        legend: {{ display: true }},
        tooltip: {{ enabled: true }}
    }},
    scales: {{
        y: {{ beginAtZero: true }}
    }}
}};
```

🎭 VISUALIZATION EXAMPLES:
- Sales by Region → Bar Chart
- Revenue Trend → Line Chart  
- Category Distribution → Pie Chart
- Performance Correlation → Scatter Plot
- User Growth → Area Chart

FINAL REMINDER: Generate ONLY charts and insights. NO HTML tables allowed. Transform the sample data into Chart.js visualizations with proper JavaScript data processing.

If you include ANY table tags (<table>, <tr>, <td>), you have FAILED the task. Focus purely on visual analytics.

HTML CODE:"""

            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 6000,  # Reduced for faster generation
                "temperature": 0.6   # Slightly lower for more focused output
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:  # Increased to 2 minutes
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"Perplexity API error: {response.status_code}")
                    raise Exception(f"API error: {response.status_code}")
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    html_content = result["choices"][0]["message"]["content"].strip()
                    
                    if not html_content:
                        raise Exception("Empty HTML response from API")
                    
                    # Clean up the response - remove code block markers if present
                    if html_content.startswith('```html'):
                        html_content = html_content[7:]
                    elif html_content.startswith('```'):
                        html_content = html_content[3:]
                    
                    if html_content.endswith('```'):
                        html_content = html_content[:-3]
                    
                    final_html = html_content.strip()
                    
                    # Basic validation
                    if not final_html or 'html' not in final_html.lower():
                        logger.warning("Generated content may not be valid HTML")
                    
                    logger.info(f"Successfully generated HTML analytics ({len(final_html)} characters)")
                    return final_html
                else:
                    logger.error(f"Invalid API response structure: {result}")
                    raise Exception("Unexpected response format from API")
                    
        except httpx.TimeoutException:
            logger.error("Timeout when calling Perplexity API for HTML generation")
            raise Exception("HTML generation request timed out")
        except httpx.HTTPError as http_err:
            logger.error(f"HTTP error during HTML generation: {str(http_err)}")
            raise Exception(f"HTTP error: {str(http_err)}")
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON decode error in HTML generation: {str(json_err)}")
            raise Exception(f"Invalid JSON response: {str(json_err)}")
        except Exception as e:
            logger.error(f"Error generating analytics HTML: {str(e)}")
            raise Exception(f"Failed to generate analytics HTML: {str(e)}")

    async def generate_multi_query_analytics_html(
        self, 
        user_query: str, 
        query_results: List[Dict[str, Any]], 
        schema_context: Optional[str] = None
    ) -> str:
        """Generate comprehensive HTML analytics from multiple query results."""
        try:
            if not self.api_key:
                raise Exception("Perplexity API key not configured")
            
            logger.info(f"Generating HTML from {len(query_results)} query results")
            
            # Process all query results
            processed_results = []
            for result in query_results:
                query_name = result.get('name', 'Unknown')
                description = result.get('description', '')
                columns = result.get('result', {}).get('columns', [])
                rows = result.get('result', {}).get('rows', [])
                
                # Process data types for JSON serialization
                processed_rows = []
                for row in rows[:15]:  # Limit sample data per query
                    if isinstance(row, (list, tuple)):
                        processed_row = []
                        for item in row:
                            if isinstance(item, (date, datetime)):
                                processed_row.append(item.isoformat())
                            elif isinstance(item, Decimal):
                                processed_row.append(float(item))
                            else:
                                processed_row.append(item)
                        processed_rows.append(processed_row)
                    else:
                        processed_rows.append(row)
                
                processed_results.append({
                    'name': query_name,
                    'description': description,
                    'columns': columns,
                    'row_count': len(rows),
                    'sample_data': processed_rows
                })
            
            schema_section = f"\n\nDatabase Schema Context:\n{schema_context}" if schema_context else ""
            
            prompt = f"""Create a comprehensive analytics dashboard from multiple focused database queries. Generate ONLY visual charts and insights, NO HTML tables.

=== USER QUERY ===
{user_query}

=== MULTIPLE QUERY RESULTS ===
{json.dumps(processed_results, indent=2, cls=CustomJSONEncoder)}
{schema_section}

=== DASHBOARD REQUIREMENTS ===
🚫 ABSOLUTELY NO HTML TABLES - Only charts and visual insights
✅ Create a unified story from multiple data sources

📊 **MULTI-QUERY DASHBOARD STRUCTURE**:
1. **Executive Summary**: Key metrics from all queries combined
2. **Primary Analysis**: Main chart from most important query
3. **Supporting Charts**: 2-3 additional visualizations from other queries
4. **Cross-Query Insights**: Patterns and relationships across datasets
5. **Comprehensive Recommendations**: Actions based on all data

🎯 **CHART STRATEGY**:
- **Query 1 Data** → Primary bar/line chart showing main trends
- **Query 2 Data** → Secondary chart (pie/doughnut for distributions)
- **Query 3+ Data** → Supporting metrics cards or smaller charts
- **Combined Insights** → Highlight relationships between different datasets

📈 **TECHNICAL IMPLEMENTATION**:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Query Analytics Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-900 text-white min-h-screen">
    <!-- Executive Summary Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <!-- Key metrics from all queries -->
    </div>
    
    <!-- Main Charts Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Primary analysis chart -->
        <!-- Secondary analysis charts -->
    </div>
    
    <!-- Cross-Query Insights -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Insights from combining multiple datasets -->
        <!-- Recommendations based on all data -->
    </div>
    
    <script>
        // Process data from multiple queries
        // Create multiple Chart.js visualizations
        // Show relationships between different datasets
    </script>
</body>
</html>
```

🔍 **CROSS-QUERY ANALYSIS**:
- Identify patterns across different data sources
- Highlight correlations and trends
- Provide comprehensive business insights
- Show how different metrics relate to each other

💡 **MULTI-DATASET INSIGHTS**:
- Compare trends from different queries
- Identify highest/lowest performers across categories
- Show seasonal or temporal patterns
- Highlight operational efficiency metrics

⚡ **FINAL REQUIREMENTS**:
- NO tables whatsoever - only visual charts
- Process each query result into appropriate chart type
- Create unified insights from multiple data sources
- Generate complete, interactive HTML dashboard
- Focus on business intelligence and actionable insights

Generate the complete multi-query analytics dashboard:"""

            payload = {
                "model": "sonar-reasoning",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 7000,
                "temperature": 0.6
            }
            
            async with httpx.AsyncClient(timeout=150.0) as client:  # Longer timeout for complex generation
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"Perplexity API error: {response.status_code}")
                    raise Exception(f"API error: {response.status_code}")
                
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    html_content = result["choices"][0]["message"]["content"].strip()
                    
                    if not html_content:
                        raise Exception("Empty HTML response from API")
                    
                    # Clean up response
                    if html_content.startswith('```html'):
                        html_content = html_content[7:]
                    elif html_content.startswith('```'):
                        html_content = html_content[3:]
                    
                    if html_content.endswith('```'):
                        html_content = html_content[:-3]
                    
                    final_html = html_content.strip()
                    
                    logger.info(f"Successfully generated multi-query HTML analytics ({len(final_html)} characters)")
                    return final_html
                    
                else:
                    logger.error(f"Invalid API response structure: {result}")
                    raise Exception("Unexpected response format from API")
                    
        except Exception as e:
            logger.error(f"Error generating multi-query analytics HTML: {str(e)}")
            raise Exception(f"Failed to generate multi-query analytics HTML: {str(e)}")