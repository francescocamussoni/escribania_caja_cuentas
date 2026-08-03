# Debugging Guide

## Purpose
Systematic approach to diagnose and fix bugs. Use when investigating issues or unexpected behavior.

> **Note:** Examples below use Python syntax. Apply the same patterns using your project's language (TypeScript, Java, Go, Ruby, etc.). The principles are universal — only the syntax changes.

---

## Debugging Process

### 1. Understand the Problem

**Ask these questions:**
- What is the expected behavior?
- What is the actual behavior?
- When did it start happening?
- Can you reproduce it consistently?
- What are the exact steps to reproduce?
- Does it happen in all environments or just some?

**Document:**
```
Expected: User should receive confirmation email after registration
Actual: No email is sent
Started: After deployment on 2024-03-10
Reproducible: Yes, 100% of the time
Steps:
  1. Go to /register
  2. Fill form with valid data
  3. Click "Register"
  4. Check email inbox
Environment: Production only (works in staging)
```

---

### 2. Gather Information

#### Stack Trace
```python
# Full stack trace with line numbers
Traceback (most recent call last):
  File "app.py", line 42, in register_user
    send_email(user.email, "Welcome")
  File "email_service.py", line 15, in send_email
    smtp.send(to, subject, body)
  File "smtp.py", line 8, in send
    connection.sendmail(from_addr, to_addr, message)
AttributeError: 'NoneType' object has no attribute 'sendmail'
```

#### Logs
```python
# Look for relevant log entries
2024-03-10 14:23:15 INFO User registration started: user@example.com
2024-03-10 14:23:15 DEBUG Validating user data
2024-03-10 14:23:15 DEBUG Creating user record
2024-03-10 14:23:16 INFO User created: id=123
2024-03-10 14:23:16 DEBUG Attempting to send email
2024-03-10 14:23:16 ERROR SMTP connection is None
```

#### State at Failure
```python
# What were the variable values?
user = User(id=123, email="user@example.com", verified=False)
smtp_connection = None  # <-- Problem!
config = {"SMTP_HOST": "smtp.gmail.com", "SMTP_PORT": 587}
```

#### Environment
```python
# What's different about this environment?
Production:
  - SMTP_HOST: smtp.gmail.com
  - SMTP_PASSWORD: (from env var)
  
Staging:
  - SMTP_HOST: localhost
  - SMTP_PASSWORD: test123
```

---

### 3. Form Hypothesis

Based on the information, what could be causing it?

**Example hypotheses:**
1. SMTP connection is not being initialized in production
2. Environment variable SMTP_PASSWORD is not set
3. Firewall is blocking SMTP port 587
4. SMTP credentials are invalid

**Prioritize by likelihood:**
1. Most likely: Environment variable not set (common in new deployments)
2. Likely: Connection initialization issue
3. Less likely: Firewall (would affect all emails, not just registration)
4. Unlikely: Invalid credentials (would show different error)

---

### 4. Test Hypothesis

#### Add Strategic Logging

```python
def send_email(to, subject, body):
    logger.debug(f"send_email called: to={to}, subject={subject}")
    
    # Test hypothesis: Is connection None?
    logger.debug(f"SMTP connection status: {smtp_connection}")
    
    if smtp_connection is None:
        logger.error("SMTP connection is None! Checking initialization...")
        logger.debug(f"SMTP_HOST: {os.getenv('SMTP_HOST')}")
        logger.debug(f"SMTP_PASSWORD set: {bool(os.getenv('SMTP_PASSWORD'))}")
        raise ValueError("SMTP connection not initialized")
    
    smtp_connection.sendmail(from_addr, to, message)
```

#### Use Debugger

```python
# Set breakpoint
import pdb; pdb.set_trace()

# Or in IDE: click line number to set breakpoint

# Debugger commands:
# n - next line
# s - step into function
# c - continue
# p variable - print variable
# l - list code around current line
```

#### Isolate the Problem

```python
# Minimal reproduction
def test_smtp_connection():
    """Test if SMTP connection can be established"""
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', 587))
    password = os.getenv('SMTP_PASSWORD')
    
    print(f"Connecting to {host}:{port}")
    print(f"Password set: {bool(password)}")
    
    try:
        connection = smtplib.SMTP(host, port)
        connection.starttls()
        connection.login(os.getenv('SMTP_USER'), password)
        print("Connection successful!")
        return connection
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

# Run this in production environment
```

---

### 5. Fix & Verify

#### Implement Fix

```python
# Root cause: SMTP_PASSWORD not set in production
# Fix: Add environment variable

# Before (in code)
smtp_connection = None  # initialized later, but fails

# After (in code)
def get_smtp_connection():
    host = os.getenv('SMTP_HOST')
    password = os.getenv('SMTP_PASSWORD')
    
    if not host or not password:
        raise ValueError(
            "SMTP configuration missing. "
            "Set SMTP_HOST and SMTP_PASSWORD environment variables."
        )
    
    connection = smtplib.SMTP(host, 587)
    connection.starttls()
    connection.login(os.getenv('SMTP_USER'), password)
    return connection

# In deployment config
# Add: SMTP_PASSWORD=<actual-password>
```

#### Verify Fix

```python
# 1. Unit test
def test_smtp_connection_with_missing_password(monkeypatch):
    monkeypatch.delenv('SMTP_PASSWORD', raising=False)
    
    with pytest.raises(ValueError, match="SMTP configuration missing"):
        get_smtp_connection()

# 2. Integration test
def test_send_email_in_production_like_environment():
    # Set up production-like config
    os.environ['SMTP_HOST'] = 'smtp.gmail.com'
    os.environ['SMTP_PASSWORD'] = 'test-password'
    
    # Should not raise
    connection = get_smtp_connection()
    assert connection is not None

# 3. Manual test in production
# - Deploy fix
# - Register new user
# - Verify email received
```

#### Add Regression Test

```python
def test_user_registration_sends_email():
    """
    Regression test for bug #123: Email not sent after registration.
    
    Root cause: SMTP connection was None in production due to
    missing SMTP_PASSWORD environment variable.
    """
    # Arrange
    user_data = {"email": "test@example.com", "password": "secure123"}
    mock_smtp = Mock()
    
    # Act
    with patch('app.get_smtp_connection', return_value=mock_smtp):
        register_user(user_data)
    
    # Assert
    mock_smtp.sendmail.assert_called_once()
```

---

## Common Debugging Techniques

### Print Debugging

```python
# Quick and dirty, but effective
def calculate_total(items):
    print(f"calculate_total called with {len(items)} items")
    
    total = 0
    for item in items:
        print(f"Processing item: {item.name}, price: {item.price}")
        total += item.price
        print(f"Running total: {total}")
    
    print(f"Final total: {total}")
    return total
```

### Binary Search

```python
# Problem: Function returns wrong result
# Strategy: Comment out half the code, see if problem persists

def complex_calculation(data):
    # Step 1: preprocessing
    cleaned = preprocess(data)
    print(f"After preprocess: {cleaned}")  # Check here
    
    # Step 2: transformation
    transformed = transform(cleaned)
    print(f"After transform: {transformed}")  # Check here
    
    # Step 3: aggregation
    result = aggregate(transformed)
    print(f"After aggregate: {result}")  # Check here
    
    return result

# If problem is in transformed, focus on transform() function
```

### Rubber Duck Debugging

Explain the problem out loud (to a rubber duck, colleague, or yourself):

```
"So, the user registers, and we create the user record successfully.
Then we try to send an email. The send_email function is called...
wait, where do we initialize the SMTP connection?
Oh! We initialize it in __init__, but only if SMTP_PASSWORD is set.
In production, is SMTP_PASSWORD set? Let me check..."
```

### Diff Debugging

```bash
# What changed between working and broken version?
git diff v1.2.0 v1.2.1 -- email_service.py

# Output shows:
- smtp_connection = smtplib.SMTP(host, port)
+ smtp_connection = None  # Initialize later
```

---

## Debugging Patterns by Error Type

### NullPointerException / AttributeError

```python
# Error: 'NoneType' object has no attribute 'x'

# Check:
1. Was the object initialized?
2. Did a function return None unexpectedly?
3. Is there a missing null check?

# Fix:
if obj is not None:
    obj.method()

# Or better: ensure obj is never None
obj = get_object() or default_object
```

### Off-by-One Errors

```python
# Error: IndexError: list index out of range

# Check:
1. Are you using < or <=?
2. Is the range correct?
3. Is the list empty?

# Debug:
items = [1, 2, 3]
for i in range(len(items)):  # 0, 1, 2 ✓
    print(items[i])

for i in range(len(items) + 1):  # 0, 1, 2, 3 ✗ (3 is out of range)
    print(items[i])
```

### Race Conditions

```python
# Error: Inconsistent results in concurrent code

# Check:
1. Are multiple threads accessing shared state?
2. Is there proper locking?
3. Are operations atomic?

# Debug:
import threading

lock = threading.Lock()

def increment_counter():
    global counter
    with lock:  # Ensure atomic operation
        counter += 1
```

### Infinite Loops

```python
# Error: Program hangs

# Check:
1. Does the loop condition ever become false?
2. Is the loop variable being updated?
3. Is there an exit condition?

# Debug:
iteration = 0
while condition:
    iteration += 1
    if iteration > 1000:
        print(f"Infinite loop detected! condition={condition}")
        break
    # ... loop body
```

---

## Debugging Tools

### Python

```python
# Built-in debugger
import pdb; pdb.set_trace()

# Better debugger
import ipdb; ipdb.set_trace()

# Logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message")

# Profiling
import cProfile
cProfile.run('my_function()')

# Memory profiling
from memory_profiler import profile
@profile
def my_function():
    pass
```

### JavaScript

```javascript
// Browser debugger
debugger;

// Console logging
console.log('value:', value);
console.table(arrayOfObjects);
console.trace();  // stack trace

// Performance
console.time('operation');
// ... code
console.timeEnd('operation');
```

---

## Prevention

### Defensive Programming

```python
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def process_user(user):
    if user is None:
        raise ValueError("User cannot be None")
    if not user.email:
        raise ValueError("User must have email")
    # ... process user
```

### Assertions

```python
def calculate_discount(price, discount_percent):
    assert price >= 0, "Price cannot be negative"
    assert 0 <= discount_percent <= 100, "Discount must be 0-100%"
    
    return price * (1 - discount_percent / 100)
```

### Comprehensive Logging

```python
logger.info(f"Processing order {order_id}")
logger.debug(f"Order details: {order}")

try:
    result = process_order(order)
    logger.info(f"Order {order_id} processed successfully")
except Exception as e:
    logger.error(f"Failed to process order {order_id}: {e}", exc_info=True)
    raise
```

---

## When to Ask for Help

Ask for help when:
- You've been stuck for >2 hours
- You've tried multiple approaches
- The bug is in unfamiliar code/domain
- It's a production incident

Before asking:
- Document what you've tried
- Provide minimal reproduction
- Share relevant logs/errors
- Explain your hypotheses

---

## Remember

- Bugs are learning opportunities
- Systematic approach beats random changes
- Document your findings
- Add tests to prevent regression
- Don't be afraid to ask for help
