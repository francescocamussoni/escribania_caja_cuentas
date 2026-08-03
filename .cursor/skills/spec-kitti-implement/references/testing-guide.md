# Testing Guide

## Purpose
Guide for generating comprehensive tests. Use when the developer doesn't have custom testing patterns.

> **Note:** Examples below use Python/pytest syntax. Apply the same patterns using your project's language and test framework (Jest/Vitest for TypeScript, JUnit for Java, RSpec for Ruby, Go testing package, etc.). The principles are universal — only the syntax changes.

---

## Testing Principles

### AAA Pattern
Every test follows Arrange-Act-Assert:
```python
def test_calculate_discount():
    # Arrange: setup test data
    price = 100
    discount_percent = 20
    
    # Act: execute the function
    result = calculate_discount(price, discount_percent)
    
    # Assert: verify the result
    assert result == 80
```

### Test Characteristics
- **Independent**: Each test runs in isolation
- **Repeatable**: Same result every time
- **Fast**: Tests run quickly (< 1 second each)
- **Clear**: Test name describes the scenario
- **Focused**: One assertion per test (when possible)

---

## Test Coverage Strategy

### For Each Function/Method

#### 1. Happy Path
Test the normal, expected use case:
```python
def test_create_user_with_valid_data():
    user = create_user(email="user@example.com", age=25)
    assert user.email == "user@example.com"
    assert user.age == 25
```

#### 2. Edge Cases
Test boundary conditions:
```python
def test_create_user_with_minimum_age():
    user = create_user(email="user@example.com", age=0)
    assert user.age == 0

def test_create_user_with_maximum_age():
    user = create_user(email="user@example.com", age=150)
    assert user.age == 150
```

#### 3. Error Cases
Test invalid inputs and error handling:
```python
def test_create_user_with_invalid_email():
    with pytest.raises(ValueError, match="Invalid email"):
        create_user(email="invalid-email", age=25)

def test_create_user_with_negative_age():
    with pytest.raises(ValueError, match="Age must be positive"):
        create_user(email="user@example.com", age=-1)
```

#### 4. Null/Empty Cases
Test with missing or empty data:
```python
def test_create_user_with_empty_email():
    with pytest.raises(ValueError):
        create_user(email="", age=25)

def test_create_user_with_none_email():
    with pytest.raises(ValueError):
        create_user(email=None, age=25)
```

---

## Unit Tests

Test individual functions/methods in isolation.

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

def test_send_welcome_email():
    # Arrange
    mock_email_service = Mock()
    user = User(email="user@example.com")
    
    # Act
    send_welcome_email(user, email_service=mock_email_service)
    
    # Assert
    mock_email_service.send.assert_called_once_with(
        to="user@example.com",
        subject="Welcome!",
        body=ANY
    )

@patch('myapp.services.email.EmailService')
def test_send_welcome_email_with_patch(mock_email_class):
    # Arrange
    mock_service = mock_email_class.return_value
    user = User(email="user@example.com")
    
    # Act
    send_welcome_email(user)
    
    # Assert
    mock_service.send.assert_called_once()
```

### Testing Async Functions

```python
import pytest

@pytest.mark.asyncio
async def test_fetch_user_data():
    # Arrange
    user_id = 123
    
    # Act
    user_data = await fetch_user_data(user_id)
    
    # Assert
    assert user_data['id'] == user_id
    assert 'email' in user_data
```

---

## Integration Tests

Test interaction between components.

### Database Integration

```python
def test_create_and_retrieve_user(db_session):
    # Arrange
    user_data = {"email": "test@example.com", "age": 25}
    
    # Act: create
    user = create_user(db_session, **user_data)
    db_session.commit()
    
    # Act: retrieve
    retrieved = get_user_by_email(db_session, "test@example.com")
    
    # Assert
    assert retrieved.id == user.id
    assert retrieved.email == user_data["email"]
```

### API Integration

```python
def test_create_user_endpoint(client):
    # Arrange
    payload = {"email": "test@example.com", "age": 25}
    
    # Act
    response = client.post("/api/users", json=payload)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert "id" in data
```

---

## Test Fixtures

Reusable test data and setup.

### Pytest Fixtures

```python
import pytest

@pytest.fixture
def sample_user():
    """Provide a sample user for tests."""
    return User(id=1, email="test@example.com", age=25)

@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    session = create_test_session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def client():
    """Provide a test client for API tests."""
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

# Use fixtures in tests
def test_user_email(sample_user):
    assert sample_user.email == "test@example.com"
```

---

## Test Organization

### File Structure

```
tests/
├── unit/
│   ├── test_user_service.py
│   ├── test_order_service.py
│   └── test_payment_service.py
├── integration/
│   ├── test_user_api.py
│   ├── test_order_flow.py
│   └── test_payment_flow.py
└── conftest.py  # shared fixtures
```

### Naming Conventions

```python
# Test files: test_*.py or *_test.py
# test_user_service.py

# Test functions: test_*
def test_create_user_with_valid_data():
    pass

def test_create_user_with_invalid_email():
    pass

# Test classes (optional grouping)
class TestUserCreation:
    def test_with_valid_data(self):
        pass
    
    def test_with_invalid_email(self):
        pass
```

---

## Parameterized Tests

Test multiple scenarios with same logic:

```python
import pytest

@pytest.mark.parametrize("email,expected_valid", [
    ("user@example.com", True),
    ("user.name@example.co.uk", True),
    ("invalid-email", False),
    ("@example.com", False),
    ("user@", False),
    ("", False),
])
def test_email_validation(email, expected_valid):
    result = is_valid_email(email)
    assert result == expected_valid

@pytest.mark.parametrize("age,should_raise", [
    (0, False),
    (25, False),
    (150, False),
    (-1, True),
    (151, True),
])
def test_age_validation(age, should_raise):
    if should_raise:
        with pytest.raises(ValueError):
            validate_age(age)
    else:
        validate_age(age)  # should not raise
```

---

## Testing Best Practices

### Do's
- ✅ Test behavior, not implementation
- ✅ One logical assertion per test
- ✅ Use descriptive test names
- ✅ Keep tests simple and readable
- ✅ Mock external dependencies
- ✅ Test error cases
- ✅ Use fixtures for common setup
- ✅ Run tests frequently during development

### Don'ts
- ❌ Don't test framework/library code
- ❌ Don't test private methods directly
- ❌ Don't make tests depend on each other
- ❌ Don't use real external services (DB, APIs)
- ❌ Don't hardcode dates/times (use freezegun)
- ❌ Don't ignore flaky tests
- ❌ Don't write tests that are harder to understand than the code

---

## Test Data Management

### Use Factories

```python
# Using factory_boy
import factory

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    age = 25
    is_active = True

# In tests
def test_create_user():
    user = UserFactory()
    assert user.email.endswith("@example.com")

def test_inactive_user():
    user = UserFactory(is_active=False)
    assert not user.is_active
```

### Avoid Magic Values

```python
# Bad
def test_discount():
    result = calculate_discount(100, 20)
    assert result == 80

# Good
def test_discount():
    price = 100
    discount_percent = 20
    expected_price = 80
    
    result = calculate_discount(price, discount_percent)
    
    assert result == expected_price
```

---

## Coverage Goals

- **Minimum**: 80% code coverage
- **Target**: 90%+ for critical business logic
- **Focus**: Cover all business rules (BR###) with tests
- **Don't obsess**: 100% coverage doesn't mean bug-free

### Check Coverage

```bash
# Python
pytest --cov=myapp --cov-report=html

# JavaScript
npm test -- --coverage
```

---

## When to Skip Tests

Only skip tests temporarily with clear reason:

```python
@pytest.mark.skip(reason="Waiting for API endpoint to be implemented")
def test_fetch_user_from_api():
    pass

@pytest.mark.skipif(sys.version_info < (3, 10), reason="Requires Python 3.10+")
def test_new_syntax_feature():
    pass
```

---

## Test Documentation

```python
def test_calculate_discount_applies_percentage_correctly():
    """
    Test that calculate_discount applies the discount percentage
    correctly to the base price.
    
    Given: A price of $100 and a 20% discount
    When: calculate_discount is called
    Then: The result should be $80
    """
    # Arrange
    price = 100
    discount_percent = 20
    
    # Act
    result = calculate_discount(price, discount_percent)
    
    # Assert
    assert result == 80
```

---

## Framework-Specific Examples

### FastAPI

```python
from fastapi.testclient import TestClient

def test_create_user_endpoint():
    client = TestClient(app)
    
    response = client.post(
        "/api/users",
        json={"email": "test@example.com", "age": 25}
    )
    
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
```

### Django

```python
from django.test import TestCase

class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create(
            email="test@example.com",
            age=25
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.age, 25)
```

### React (Jest + Testing Library)

```javascript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('user can submit form', async () => {
  // Arrange
  render(<UserForm onSubmit={mockSubmit} />);
  
  // Act
  await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com');
  await userEvent.click(screen.getByRole('button', { name: /submit/i }));
  
  // Assert
  expect(mockSubmit).toHaveBeenCalledWith({
    email: 'test@example.com'
  });
});
```
