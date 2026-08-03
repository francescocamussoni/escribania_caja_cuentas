# Documentation Guide

## Purpose
Guide for writing clear, comprehensive documentation for code, APIs, and systems.

> **Note:** Examples below use Python syntax. Apply the same patterns using your project's language (TypeScript, Java, Go, Ruby, etc.). The principles are universal — only the syntax changes.

---

## Documentation Principles

### Write for Your Audience
- **Developers**: Technical details, API references, architecture
- **Users**: How-to guides, tutorials, examples
- **Maintainers**: Design decisions, gotchas, troubleshooting

### Keep It Current
- Update docs when code changes
- Mark deprecated features
- Remove outdated information
- Version your documentation

### Show, Don't Just Tell
- Include code examples
- Provide real-world use cases
- Add diagrams when helpful
- Link to related resources

---

## Code Comments

### When to Comment

**DO comment:**
- WHY something is done (not WHAT)
- Non-obvious decisions
- Workarounds and hacks
- Business rules (BR###)
- Complex algorithms
- Performance optimizations

**DON'T comment:**
- Obvious code (the code itself is clear)
- What the code does (use better names instead)
- Redundant information

### Good vs Bad Comments

```python
# Bad: States the obvious
# Increment counter by 1
counter += 1

# Good: Explains why
# Increment counter to track retry attempts for rate limiting
counter += 1

# Bad: Redundant
# Get user by ID
user = get_user_by_id(user_id)

# Good: Explains non-obvious behavior
# get_user_by_id returns None if user is soft-deleted
# We need to check is_active separately
user = get_user_by_id(user_id)

# Bad: Commented-out code
# old_function()
# another_old_function()
new_function()

# Good: Explanation for workaround
# HACK: Using sleep because the API doesn't support webhooks yet
# TODO: Remove when webhook support is added (ticket #123)
time.sleep(5)
check_status()
```

---

## Function/Method Documentation

### Docstring Format

```python
def calculate_shipping_cost(
    weight: float,
    distance: int,
    express: bool = False,
    insurance: bool = False
) -> float:
    """
    Calculate shipping cost based on package weight and delivery distance.
    
    The cost is calculated using a base rate plus distance and weight
    multipliers. Express shipping doubles the cost, and insurance adds
    a fixed fee.
    
    Args:
        weight: Package weight in kilograms. Must be positive.
        distance: Delivery distance in kilometers. Must be positive.
        express: Whether to use express shipping. Defaults to False.
        insurance: Whether to add insurance. Defaults to False.
    
    Returns:
        Total shipping cost in USD.
    
    Raises:
        ValueError: If weight or distance is negative or zero.
    
    Examples:
        >>> calculate_shipping_cost(2.5, 100)
        15.50
        
        >>> calculate_shipping_cost(2.5, 100, express=True)
        31.00
        
        >>> calculate_shipping_cost(2.5, 100, insurance=True)
        20.50
    
    Note:
        Express shipping is not available for packages over 30kg.
        Insurance is recommended for shipments over $500.
    """
    if weight <= 0 or distance <= 0:
        raise ValueError("Weight and distance must be positive")
    
    base_cost = 5.0
    cost = base_cost + (weight * 2) + (distance * 0.1)
    
    if express:
        cost *= 2
    
    if insurance:
        cost += 5.0
    
    return cost
```

### TypeScript/JavaScript

```typescript
/**
 * Calculate shipping cost based on package weight and delivery distance.
 * 
 * The cost is calculated using a base rate plus distance and weight
 * multipliers. Express shipping doubles the cost.
 * 
 * @param weight - Package weight in kilograms (must be positive)
 * @param distance - Delivery distance in kilometers (must be positive)
 * @param options - Optional shipping options
 * @param options.express - Use express shipping (default: false)
 * @param options.insurance - Add insurance (default: false)
 * @returns Total shipping cost in USD
 * @throws {Error} If weight or distance is negative or zero
 * 
 * @example
 * ```typescript
 * calculateShippingCost(2.5, 100);
 * // Returns: 15.50
 * 
 * calculateShippingCost(2.5, 100, { express: true });
 * // Returns: 31.00
 * ```
 */
function calculateShippingCost(
  weight: number,
  distance: number,
  options: { express?: boolean; insurance?: boolean } = {}
): number {
  // Implementation
}
```

---

## Class Documentation

```python
class OrderProcessor:
    """
    Process customer orders through validation, payment, and fulfillment.
    
    This class handles the complete order lifecycle from initial validation
    through payment processing and fulfillment. It integrates with the
    payment gateway and inventory system.
    
    Attributes:
        payment_gateway: Payment gateway instance for processing payments
        inventory: Inventory system instance for stock management
        max_retries: Maximum number of retry attempts for failed operations
    
    Example:
        >>> processor = OrderProcessor(payment_gateway, inventory)
        >>> result = processor.process_order(order)
        >>> if result.success:
        ...     print(f"Order {order.id} processed successfully")
    
    Note:
        This class is thread-safe for concurrent order processing.
        All operations are idempotent and can be safely retried.
    """
    
    def __init__(
        self,
        payment_gateway: PaymentGateway,
        inventory: InventorySystem,
        max_retries: int = 3
    ):
        """
        Initialize the order processor.
        
        Args:
            payment_gateway: Configured payment gateway instance
            inventory: Configured inventory system instance
            max_retries: Maximum retry attempts (default: 3)
        """
        self.payment_gateway = payment_gateway
        self.inventory = inventory
        self.max_retries = max_retries
```

---

## API Documentation

### REST API Endpoint

```markdown
### POST /api/v1/orders

Create a new order.

**Authentication:** Bearer token required

**Request Body:**
```json
{
  "customer_id": "cust_123",
  "items": [
    {
      "product_id": "prod_456",
      "quantity": 2,
      "price": 29.99
    }
  ],
  "shipping_address": {
    "street": "123 Main St",
    "city": "Springfield",
    "state": "IL",
    "zip": "62701"
  },
  "payment_method": "card_789"
}
```

**Response (201 Created):**
```json
{
  "order_id": "ord_abc123",
  "status": "pending",
  "total": 59.98,
  "created_at": "2024-03-10T14:30:00Z",
  "estimated_delivery": "2024-03-15T00:00:00Z"
}
```

**Error Responses:**

- **400 Bad Request**: Invalid request body
  ```json
  {
    "error": "validation_error",
    "message": "Invalid product_id",
    "field": "items[0].product_id"
  }
  ```

- **401 Unauthorized**: Missing or invalid authentication token
  ```json
  {
    "error": "unauthorized",
    "message": "Invalid or expired token"
  }
  ```

- **404 Not Found**: Customer or product not found
  ```json
  {
    "error": "not_found",
    "message": "Customer not found",
    "resource": "customer",
    "id": "cust_123"
  }
  ```

- **409 Conflict**: Insufficient inventory
  ```json
  {
    "error": "insufficient_inventory",
    "message": "Not enough stock for product",
    "product_id": "prod_456",
    "available": 1,
    "requested": 2
  }
  ```

**Rate Limiting:**
- 100 requests per minute per API key
- Returns `429 Too Many Requests` when exceeded

**Idempotency:**
- Include `Idempotency-Key` header to safely retry requests
- Same key within 24 hours returns cached response

**Example:**
```bash
curl -X POST https://api.example.com/api/v1/orders \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{
    "customer_id": "cust_123",
    "items": [{"product_id": "prod_456", "quantity": 2, "price": 29.99}],
    "shipping_address": {...},
    "payment_method": "card_789"
  }'
```
```

---

## README Structure

```markdown
# Project Name

Brief description of what the project does (1-2 sentences).

## Features

- Feature 1: Brief description
- Feature 2: Brief description
- Feature 3: Brief description

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis 6+

### Setup

```bash
# Clone the repository
git clone https://github.com/username/project.git
cd project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Start the server
python manage.py runserver
```

## Quick Start

```python
from myproject import Client

# Initialize client
client = Client(api_key="your-api-key")

# Create an order
order = client.orders.create(
    customer_id="cust_123",
    items=[{"product_id": "prod_456", "quantity": 2}]
)

print(f"Order created: {order.id}")
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` | No |
| `API_KEY` | External API key | - | Yes |
| `DEBUG` | Enable debug mode | `false` | No |

### Configuration File

Create `config.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

database:
  pool_size: 10
  max_overflow: 20

logging:
  level: INFO
  format: json
```

## Usage

### Basic Usage

[Common use cases with examples]

### Advanced Usage

[Complex scenarios, edge cases]

## API Reference

See [API Documentation](docs/api.md) for detailed API reference.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=myproject

# Run specific test file
pytest tests/test_orders.py
```

### Code Style

```bash
# Format code
black .

# Lint code
flake8 .

# Type check
mypy .
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Architecture

[High-level architecture overview, link to detailed docs]

## Troubleshooting

### Common Issues

**Issue: Database connection fails**
```
Error: could not connect to server
```
Solution: Check that PostgreSQL is running and DATABASE_URL is correct.

**Issue: Import errors**
```
ModuleNotFoundError: No module named 'myproject'
```
Solution: Ensure virtual environment is activated and dependencies are installed.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Documentation: https://docs.example.com
- Issues: https://github.com/username/project/issues
- Email: support@example.com
```

---

## Architecture Documentation

### Architecture Decision Record (ADR)

```markdown
# ADR 001: Use PostgreSQL for Primary Database

## Status
Accepted

## Context
We need to choose a database for storing order and customer data.
Requirements:
- ACID transactions
- Complex queries with joins
- JSON support for flexible schemas
- Mature ecosystem

## Decision
We will use PostgreSQL as our primary database.

## Consequences

### Positive
- Strong ACID guarantees for financial transactions
- Excellent JSON support (JSONB)
- Rich query capabilities
- Large community and tooling
- Good performance for our scale

### Negative
- More complex to scale horizontally than NoSQL
- Requires more careful schema design
- Higher operational overhead than managed NoSQL

### Neutral
- Team has PostgreSQL experience
- Hosting costs similar to alternatives

## Alternatives Considered

### MongoDB
- Pros: Flexible schema, easy horizontal scaling
- Cons: Weaker consistency guarantees, less mature for transactions

### MySQL
- Pros: Similar to PostgreSQL, slightly faster for simple queries
- Cons: Weaker JSON support, less feature-rich

## References
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Comparison of SQL Databases](https://example.com/comparison)
```

---

## Inline Documentation

### Business Rules

```python
def calculate_discount(order):
    # BR001: Premium customers get 10% discount on orders over $100
    if order.customer.is_premium and order.total > 100:
        return order.total * 0.10
    
    # BR002: First-time customers get $5 off
    if order.customer.order_count == 0:
        return 5.0
    
    return 0.0
```

### Parity Anchors

```python
def create_user_endpoint(request):
    # EP001: Legacy API returns user_id as string, we maintain compatibility
    user = create_user(request.data)
    return {
        "user_id": str(user.id),  # EP001: string for compatibility
        "email": user.email
    }
```

### TODOs

```python
# TODO(john): Refactor this to use async/await (ticket #456)
def fetch_user_data(user_id):
    return requests.get(f"/api/users/{user_id}").json()

# FIXME: This breaks with Unicode characters (bug #789)
def sanitize_input(text):
    return text.encode('ascii', 'ignore').decode()

# HACK: Temporary workaround until API v2 is released
# Remove after 2024-06-01
def get_user_preferences(user_id):
    time.sleep(1)  # Rate limiting workaround
    return api.get_preferences(user_id)
```

---

## Documentation Best Practices

### Keep It DRY
- Don't repeat information
- Link to canonical sources
- Use includes/references

### Use Examples
- Show real-world usage
- Include expected output
- Cover common scenarios

### Be Specific
- Use concrete examples, not abstract descriptions
- Include actual values, not placeholders
- Show complete, runnable code

### Update Regularly
- Review docs with code changes
- Mark deprecated features
- Remove outdated information
- Version your docs

### Make It Searchable
- Use clear headings
- Include keywords
- Add table of contents
- Cross-reference related topics

---

## Tools

### Documentation Generators
- **Python**: Sphinx, MkDocs, pdoc
- **JavaScript**: JSDoc, TypeDoc, Docusaurus
- **API**: Swagger/OpenAPI, Postman

### Diagramming
- **Architecture**: draw.io, Lucidchart, Mermaid
- **Sequence**: PlantUML, Mermaid
- **ER Diagrams**: dbdiagram.io, ERD tools

### Hosting
- **Static sites**: GitHub Pages, Netlify, Vercel
- **Documentation platforms**: ReadTheDocs, GitBook
- **API docs**: Swagger UI, Redoc, Stoplight

---

## Remember

- Documentation is code
- Write for your future self
- Examples are worth a thousand words
- Keep it current or remove it
- Good docs save time and reduce bugs
