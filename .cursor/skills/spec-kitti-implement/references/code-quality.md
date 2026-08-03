# Code Quality Guide

## Purpose
Baseline code quality standards for all generated code. These are minimum requirements that complement developer's custom standards.

> **Note:** Examples below use Python syntax. Apply the same patterns using your project's language (TypeScript, Java, Go, Ruby, etc.). The principles are universal — only the syntax changes.

---

## Quality Checklist

### Readability
- [ ] Variable and function names are descriptive and clear
- [ ] No single-letter variables (except loop counters i, j, k)
- [ ] Boolean variables/functions use is/has/can prefix
- [ ] Constants use UPPER_SNAKE_CASE
- [ ] Classes use PascalCase, functions use snake_case (Python) or camelCase (JS/TS)

### Function Design
- [ ] Functions ≤ 50 lines (extract helpers if needed)
- [ ] Single responsibility — one function does one thing
- [ ] Max 4 parameters (use objects/dicts for more)
- [ ] No nested functions deeper than 2 levels
- [ ] Pure functions when possible (no side effects)

### Type Safety
- [ ] Type annotations on all function signatures
- [ ] Return types explicitly declared
- [ ] No `any` or `unknown` types without justification
- [ ] Nullable types explicitly marked (Optional, | None, ?)

### Error Handling
- [ ] Try/catch on all async operations
- [ ] Try/catch on all external calls (DB, API, file I/O)
- [ ] Specific exception types (not bare `except:`)
- [ ] Error messages are descriptive and actionable
- [ ] No silenced exceptions without logging

### Code Organization
- [ ] Related functions grouped together
- [ ] Public functions before private/helper functions
- [ ] Imports organized (stdlib → third-party → local)
- [ ] No unused imports or variables
- [ ] No commented-out code (use git history)

### DRY (Don't Repeat Yourself)
- [ ] No duplicated logic (extract to shared function)
- [ ] No magic numbers (use named constants)
- [ ] No duplicated strings (use constants or config)

### Comments
- [ ] Complex logic has explanatory comments
- [ ] WHY comments, not WHAT comments
- [ ] Business rules referenced with `# BR###`
- [ ] Parity anchors referenced with `# EP###`
- [ ] TODOs include ticket number or owner

### Testing Considerations
- [ ] Code is testable (dependencies can be mocked)
- [ ] No tight coupling to external services
- [ ] Side effects are isolated and explicit

---

## Language-Specific Standards

### Python
```python
# Good
def calculate_total_price(items: list[Item], discount_percent: float = 0) -> Decimal:
    """Calculate total price with optional discount."""
    if not items:
        raise ValueError("Items list cannot be empty")
    
    subtotal = sum(item.price * item.quantity for item in items)
    discount = subtotal * (discount_percent / 100)
    return subtotal - discount

# Bad
def calc(i, d=0):  # unclear names, no types
    t = 0
    for x in i:
        t += x.price * x.quantity
    return t - (t * d / 100)
```

### TypeScript/JavaScript
```typescript
// Good
function calculateTotalPrice(items: Item[], discountPercent: number = 0): number {
  if (items.length === 0) {
    throw new Error("Items array cannot be empty");
  }
  
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const discount = subtotal * (discountPercent / 100);
  return subtotal - discount;
}

// Bad
function calc(i: any, d: any) {  // any types, unclear names
  let t = 0;
  for (let x of i) {
    t += x.price * x.quantity;
  }
  return t - (t * d / 100);
}
```

---

## Performance Considerations

### Avoid N+1 Queries
```python
# Bad
for user in users:
    orders = db.query(Order).filter(Order.user_id == user.id).all()

# Good
user_ids = [user.id for user in users]
orders = db.query(Order).filter(Order.user_id.in_(user_ids)).all()
orders_by_user = defaultdict(list)
for order in orders:
    orders_by_user[order.user_id].append(order)
```

### Use Appropriate Data Structures
```python
# Bad: O(n) lookup
if item in item_list:  # list

# Good: O(1) lookup
if item in item_set:  # set
```

### Lazy Loading When Appropriate
```python
# Bad: load everything upfront
all_data = fetch_all_records()  # millions of records

# Good: paginate or stream
for batch in fetch_records_in_batches(batch_size=1000):
    process_batch(batch)
```

---

## Security Baseline

### Input Validation
```python
# Good
def create_user(email: str, age: int) -> User:
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise ValueError("Invalid email format")
    if age < 0 or age > 150:
        raise ValueError("Age must be between 0 and 150")
    # ... create user
```

### No Secrets in Code
```python
# Bad
API_KEY = "sk_live_abc123xyz"

# Good
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable not set")
```

### Safe Logging
```python
# Bad
logger.info(f"User login: {username} with password {password}")

# Good
logger.info(f"User login: {username}")
```

---

## When to Deviate

These are guidelines, not absolute rules. Deviate when:
- Developer's custom skills specify different standards
- Project's constitution requires different approach
- Performance requirements demand optimization
- Domain-specific patterns are more appropriate

Always document the reason for deviation in comments.
