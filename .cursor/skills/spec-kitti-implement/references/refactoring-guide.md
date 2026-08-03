# Refactoring Guide

## Purpose
Systematic approach to improve code structure while maintaining behavior. Use when code needs improvement without changing functionality.

> **Note:** Examples below use Python syntax. Apply the same patterns using your project's language (TypeScript, Java, Go, Ruby, etc.). The principles are universal — only the syntax changes.

---

## Refactoring Process

### 1. Understand Current Code
- Read and understand the existing behavior
- Identify what the code does (inputs → outputs)
- Document any unclear behavior

### 2. Ensure Test Coverage
- **CRITICAL**: Tests must exist BEFORE refactoring
- If no tests exist, write them first
- Tests are your safety net
- All tests must pass before starting

### 3. Identify Code Smells
Look for these common issues:
- Long functions (>50 lines)
- Duplicated code
- Unclear names
- Deep nesting (>3 levels)
- Large classes (>300 lines)
- Long parameter lists (>4 params)
- Complex conditionals
- Magic numbers/strings

### 4. Refactor in Small Steps
- One refactoring at a time
- Run tests after each step
- Commit after each successful refactor
- If tests fail, revert and try smaller step

### 5. Verify Behavior
- All tests still pass
- No new bugs introduced
- Performance not degraded
- External behavior unchanged

---

## Common Refactorings

### Extract Method
**When**: Function is too long or has distinct sections

**Before:**
```python
def process_order(order):
    # Validate order (10 lines)
    if not order.items:
        raise ValueError("Order has no items")
    if order.total < 0:
        raise ValueError("Invalid total")
    # ... more validation
    
    # Calculate totals (15 lines)
    subtotal = 0
    for item in order.items:
        subtotal += item.price * item.quantity
    tax = subtotal * 0.1
    total = subtotal + tax
    
    # Save to database (8 lines)
    db.session.add(order)
    db.session.commit()
    
    # Send notifications (12 lines)
    send_email(order.customer.email, "Order confirmed")
    send_sms(order.customer.phone, "Order confirmed")
```

**After:**
```python
def process_order(order):
    validate_order(order)
    total = calculate_order_total(order)
    save_order(order, total)
    notify_customer(order)

def validate_order(order):
    if not order.items:
        raise ValueError("Order has no items")
    if order.total < 0:
        raise ValueError("Invalid total")

def calculate_order_total(order):
    subtotal = sum(item.price * item.quantity for item in order.items)
    tax = subtotal * 0.1
    return subtotal + tax

def save_order(order, total):
    order.total = total
    db.session.add(order)
    db.session.commit()

def notify_customer(order):
    send_email(order.customer.email, "Order confirmed")
    send_sms(order.customer.phone, "Order confirmed")
```

---

### Extract Variable
**When**: Complex expression or repeated calculation

**Before:**
```python
if (user.age >= 18 and user.has_license and not user.is_suspended):
    allow_driving()

price = quantity * unit_price * (1 - discount_rate) * (1 + tax_rate)
```

**After:**
```python
can_drive = user.age >= 18 and user.has_license and not user.is_suspended
if can_drive:
    allow_driving()

discount_multiplier = 1 - discount_rate
tax_multiplier = 1 + tax_rate
price = quantity * unit_price * discount_multiplier * tax_multiplier
```

---

### Rename Variable/Function
**When**: Name is unclear or misleading

**Before:**
```python
def calc(x, y):
    return x * y * 0.1

result = calc(100, 5)
```

**After:**
```python
def calculate_tax(subtotal, tax_rate_percent):
    return subtotal * (tax_rate_percent / 100)

tax_amount = calculate_tax(subtotal=100, tax_rate_percent=5)
```

---

### Replace Magic Numbers
**When**: Unexplained numbers in code

**Before:**
```python
if user.age >= 18:
    allow_access()

if len(password) < 8:
    raise ValueError("Password too short")

discount = price * 0.15
```

**After:**
```python
LEGAL_AGE = 18
MIN_PASSWORD_LENGTH = 8
STANDARD_DISCOUNT_RATE = 0.15

if user.age >= LEGAL_AGE:
    allow_access()

if len(password) < MIN_PASSWORD_LENGTH:
    raise ValueError("Password too short")

discount = price * STANDARD_DISCOUNT_RATE
```

---

### Simplify Conditional
**When**: Complex nested conditionals

**Before:**
```python
def get_shipping_cost(order):
    if order.total > 100:
        if order.is_premium:
            return 0
        else:
            return 5
    else:
        if order.is_premium:
            return 5
        else:
            return 10
```

**After:**
```python
def get_shipping_cost(order):
    if order.total > 100 and order.is_premium:
        return 0
    if order.total > 100:
        return 5
    if order.is_premium:
        return 5
    return 10

# Or even better with early returns
def get_shipping_cost(order):
    FREE_SHIPPING_THRESHOLD = 100
    PREMIUM_DISCOUNT = 5
    STANDARD_SHIPPING = 10
    
    if order.total > FREE_SHIPPING_THRESHOLD:
        return 0 if order.is_premium else PREMIUM_DISCOUNT
    
    return PREMIUM_DISCOUNT if order.is_premium else STANDARD_SHIPPING
```

---

### Replace Conditional with Polymorphism
**When**: Type checking with if/else chains

**Before:**
```python
def calculate_area(shape):
    if shape.type == "circle":
        return 3.14 * shape.radius ** 2
    elif shape.type == "rectangle":
        return shape.width * shape.height
    elif shape.type == "triangle":
        return 0.5 * shape.base * shape.height
```

**After:**
```python
class Shape:
    def calculate_area(self):
        raise NotImplementedError

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius
    
    def calculate_area(self):
        return 3.14 * self.radius ** 2

class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height
    
    def calculate_area(self):
        return self.width * self.height

class Triangle(Shape):
    def __init__(self, base, height):
        self.base = base
        self.height = height
    
    def calculate_area(self):
        return 0.5 * self.base * self.height

# Usage
area = shape.calculate_area()  # polymorphic call
```

---

### Extract Class
**When**: Class has too many responsibilities

**Before:**
```python
class Order:
    def __init__(self):
        self.items = []
        self.customer_email = ""
        self.customer_phone = ""
    
    def add_item(self, item):
        self.items.append(item)
    
    def calculate_total(self):
        return sum(item.price for item in self.items)
    
    def send_confirmation_email(self):
        send_email(self.customer_email, "Order confirmed")
    
    def send_confirmation_sms(self):
        send_sms(self.customer_phone, "Order confirmed")
    
    def generate_invoice_pdf(self):
        # ... PDF generation logic
        pass
```

**After:**
```python
class Order:
    def __init__(self, customer):
        self.items = []
        self.customer = customer
    
    def add_item(self, item):
        self.items.append(item)
    
    def calculate_total(self):
        return sum(item.price for item in self.items)

class Customer:
    def __init__(self, email, phone):
        self.email = email
        self.phone = phone

class OrderNotifier:
    def send_confirmation(self, order):
        self._send_email(order.customer.email)
        self._send_sms(order.customer.phone)
    
    def _send_email(self, email):
        send_email(email, "Order confirmed")
    
    def _send_sms(self, phone):
        send_sms(phone, "Order confirmed")

class InvoiceGenerator:
    def generate_pdf(self, order):
        # ... PDF generation logic
        pass
```

---

### Introduce Parameter Object
**When**: Functions have long parameter lists

**Before:**
```python
def create_user(first_name, last_name, email, phone, street, city, state, zip_code):
    # ... implementation
    pass

create_user("John", "Doe", "john@example.com", "555-1234", 
            "123 Main St", "Springfield", "IL", "62701")
```

**After:**
```python
from dataclasses import dataclass

@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str

@dataclass
class UserInfo:
    first_name: str
    last_name: str
    email: str
    phone: str
    address: Address

def create_user(user_info: UserInfo):
    # ... implementation
    pass

address = Address("123 Main St", "Springfield", "IL", "62701")
user_info = UserInfo("John", "Doe", "john@example.com", "555-1234", address)
create_user(user_info)
```

---

### Remove Dead Code
**When**: Code is never executed or used

**Before:**
```python
def process_payment(amount):
    # Old payment gateway (deprecated)
    # gateway = OldPaymentGateway()
    # gateway.charge(amount)
    
    # New payment gateway
    gateway = NewPaymentGateway()
    return gateway.charge(amount)

def old_function_never_called():
    # This was used in v1.0
    pass
```

**After:**
```python
def process_payment(amount):
    gateway = NewPaymentGateway()
    return gateway.charge(amount)

# old_function_never_called removed entirely
```

---

## Refactoring Anti-Patterns

### Don't Change Behavior
```python
# Bad: Refactoring + behavior change
def calculate_discount(price):
    # Before: returned discount amount
    # After: returns final price (BEHAVIOR CHANGE!)
    return price * 0.9

# Good: Separate refactoring from behavior change
# Step 1: Refactor (keep behavior)
# Step 2: Change behavior in separate commit
```

### Don't Refactor Without Tests
```python
# Bad: Refactoring complex code without tests
def complex_business_logic():
    # 200 lines of complex logic
    # No tests exist
    # Refactoring is dangerous!
    pass

# Good: Write tests first
def test_complex_business_logic():
    result = complex_business_logic(input_data)
    assert result == expected_output

# Now safe to refactor
```

### Don't Make Big Changes
```python
# Bad: Massive refactoring in one step
# - Rename 50 functions
# - Extract 20 classes
# - Change architecture
# All in one commit

# Good: Small incremental changes
# Commit 1: Extract one method
# Commit 2: Rename one function
# Commit 3: Extract one class
# Each commit: tests pass
```

---

## When to Refactor

### Good Times
- Before adding new feature (clean up first)
- During code review (small improvements)
- When you touch code (boy scout rule: leave it better)
- When tests are green and stable

### Bad Times
- When tests are failing
- During production incident
- When deadline is tomorrow
- When you don't understand the code

---

## Refactoring Checklist

Before refactoring:
- [ ] Tests exist and pass
- [ ] You understand the current behavior
- [ ] You have time to do it properly
- [ ] Code is in version control

During refactoring:
- [ ] One refactoring at a time
- [ ] Run tests after each change
- [ ] Commit after each successful step
- [ ] Keep external behavior unchanged

After refactoring:
- [ ] All tests still pass
- [ ] Code is more readable
- [ ] Code is more maintainable
- [ ] No new bugs introduced
- [ ] Performance not degraded

---

## Tools

### Automated Refactoring
- IDE refactoring tools (rename, extract method, etc.)
- Linters (identify code smells)
- Code formatters (consistent style)

### Manual Review
- Code review with team
- Pair programming
- Rubber duck debugging

---

## Remember

> "Refactoring is a disciplined technique for restructuring an existing body of code, altering its internal structure without changing its external behavior."
> — Martin Fowler

- Refactoring ≠ Rewriting
- Small steps are safer than big leaps
- Tests are your safety net
- When in doubt, don't refactor
