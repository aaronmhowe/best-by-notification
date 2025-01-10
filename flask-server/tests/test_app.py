import unittest
from datetime import datetime, timedelta
from flask_testing import TestCase
import sys
import os
# Add the project root (flask-server) to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server import app, db
from models.product import Product
from models.user import User
from models.forgot_password import ForgotPassword

# Install the Ctr-C handler to exit the test running
unittest.installHandler()

class ProductTestCase(TestCase):
  def create_app(self):
    # Set up the Flask test app and use a different database for testing.
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_products.db'
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    return app
  
  def setUp(self):
    # This runs before each test. It creates a new database for testing.
    db.create_all()
    # Adding sample data for testing
    sample_product = Product(name='Sample', expiration_date=datetime(2024, 10, 25))
    db.session.add(sample_product)
    db.session.commit()
    
  def tearDown(self):
    # This runs after each test. It removes the test database.
    db.session.remove()
    db.drop_all()
  
  # Test for adding a product
  def test_add_product(self):
    response = self.client.post('/add_product', json={
        'name': 'Milk',
        'expiration_date': '2024-12-01'
    })
    self.assertEqual(response.status_code, 200)
    self.assertIn('Product added successfully', response.json['message'])

  # Test for fetching all products
  def test_get_product(self):
    response = self.client.get('/get_products')
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.json), 1) # One product was added from setUp()
  
  # Test for getting a product by id
  def test_get_product_by_id(self):
    product = Product.query.filter_by(name="Sample").first()
    response = self.client.get(f'/get_product/{product.id}')

    # Check result
    self.assertEqual(response.status_code, 200)
    self.assertIn(product.name, response.json['name'])
    self.assertIn(product.expiration_date.strftime('%Y-%m-%d'), response.json['expiration_date'])

  # Test for deleting a product
  def test_delete_product_by_id(self):
    # Retrieve product from db
    product = Product.query.filter_by(name='Sample').first() # Product "Sample" initialized in setUp()

    # Test for deletion on existing item
    response = self.client.delete(f'/delete_product/{product.id}')
    self.assertEqual(response.status_code, 200)
    self.assertIn(f'Product {product.name} with id {product.id} has been deleted successfully', response.json['message'])

    # Test for deletion on non-existent item
    response = self.client.delete(f'/delete_product/{product.id}') # Uses same id as "Sample"
    self.assertEqual(response.status_code, 404)

  # Test for get product by name
  def test_get_product_by_name(self):
    # Get for the Sample
    response = self.client.get('/get_product/Sample')
    
    # Assert success code
    self.assertEqual(response.status_code, 200)
    
    # Assert the product name matches sample
    self.assertEqual(response.json['name'], 'Sample')
    
    # Assert the expiration date matches sample
    expected_date = '2024-10-25'  # Expected expiration date
    self.assertEqual(response.json['expiration date'], expected_date)

class ForgotPasswordTests(TestCase):
  """
  Test cases for the Forgot Password feature.
  """

  def create_app(self):
    """
    Create an instance of the flask application with a database for testing purposes.
    """
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_users.db'
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    app.config['MAIL_SUPPRESS_SEND'] = True
    return app
  
  def setUp(self):
    """
    Set up the testing environment.
    """
    db.create_all()
    self.test_user = User(email='user@email.com', password='password')
    db.session.add(self.test_user)
    db.session.commit()

  def test_user_requests_reset(self):
    """
    Tests that a reset code is sent to a user's email address upon reset request.
    """
    response = self.client.post('/reset_request', json={
      'email': 'user@email.com'
    })
    self.assertEqual(response.status_code, 200)
    self.assertIn('Code sent for password reset', response.json['message'])
    request = ForgotPassword.query.filter_by(user_id=self.test_user.id).first()
    self.assertIsNotNone(request)
    self.assertIsNotNone(request.code)
    self.assertIsNotNone(request.expiration_window)

  def test_invalid_email(self):
    """
    Tests that the server responds with a proper error message when the user provides an invalid email.
    """
    response = self.client.post('/reset_request', json={
      'email': 'fake@email.com'
    })
    self.assertEqual(response.status_code, 404)
    self.assertIn('Invalid Email', response.json['error'])

  def test_invalid_code(self):
    """
    Tests that the server responds with a proper error message when the user provides an invalid reset code.
    """
    response = self.client.post('/validate_code', json={
      'email': 'user@email.com',
      'code': '000000'
    })
    self.assertEqual(response.status_code, 400)
    self.assertIn('Code is invalid or expired', response.json['error'])

  def test_expired_code(self):
    """
    Tests that the server responds with a proper error message when the user provides an expired code.
    """
    expired_code = ForgotPassword(
      user_id=self.test_user.id,
      code='000000',
      expiration_window=datetime.now(datetime.timezone.utc) - timedelta(hours=1)
    )
    db.session.add(expired_code)
    db.session.commit()
    response = self.client.post('/validate_code', json={
      'email': 'user@email.com',
      'code': '000000'
    })
    self.assertEqual(response.status_code, 400)
    self.assertIn('Code is invalid or expired', response.json['error'])

  def test_valid_code(self):
    """
    Tests that the server accepts a valid reset code from the user
    """
    self.client.post('/reset_request', json={
      'email': 'user@email.com',
    })
    reset_request = ForgotPassword.query.filter_by(user_id=self.test_user.id).first()
    response = self.client.post('/validate_code', json={
      'email': 'user@email.com',
      'code': reset_request.code
    })
    self.assertEqual(response.status_code, 200)
    self.assertIn('Code Validation Successful', response.json['message'])

  def test_reset_password(self):
    """
    Tests that the user can successfully reset their password after inputting a valid code.
    """
    self.client.post('/reset_request', json={
      'email': 'user@email.com'
    })
    reset_request = ForgotPassword.query.filter_by(user_id=self.test_user.id).first()
    response = self.client.post('/password_reset', json={
      'email': 'user@email.com',
      'code': reset_request.code,
      'new_password': 'newpassword'
    })
    self.assertEqual(response.status_code, 200)
    self.assertIn('Password Reset Successful', response.json['message'])
    self.assertTrue(self.test_user.check_password('newpassword'))

  def tearDown(self):
    """
    Clear the testing environment.
    """
    db.session.remove()
    db.drop_all()

if __name__ == '__main__':
  unittest.main()