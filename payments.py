import os
from square.client import Client
from flask import Flask, request, jsonify
import uuid

# Initialize Square client
SQUARE_ACCESS_TOKEN = os.getenv('SQUARE_ACCESS_TOKEN')  # Set in environment
SQUARE_ENVIRONMENT = 'sandbox'  # Change to 'production' when live

client = Client(
    access_token=SQUARE_ACCESS_TOKEN,
    environment=SQUARE_ENVIRONMENT
)

# Subscription plan IDs (create these in Square Dashboard first)
PLANS = {
    'hobbyist': 'PLAN_HOBBYIST_ID',
    'trader': 'PLAN_TRADER_ID',
    'business': 'PLAN_BUSINESS_ID'
}

def create_subscription(customer_id, plan_name, card_id):
    """
    Create a recurring subscription for a customer
    
    Args:
        customer_id: Square customer ID
        plan_name: 'hobbyist', 'trader', or 'business'
        card_id: Customer's payment card on file
    """
    try:
        result = client.subscriptions.create_subscription(
            body={
                "idempotency_key": str(uuid.uuid4()),
                "location_id": os.getenv('SQUARE_LOCATION_ID'),
                "plan_id": PLANS[plan_name],
                "customer_id": customer_id,
                "card_id": card_id,
                "start_date": "immediate",
                "tax_percentage": "0"
            }
        )
        
        if result.is_success():
            subscription = result.body['subscription']
            return {
                'success': True,
                'subscription_id': subscription['id'],
                'status': subscription['status'],
                'plan': plan_name
            }
        else:
            return {
                'success': False,
                'errors': result.errors
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def create_customer(email, first_name, last_name):
    """Create a new Square customer"""
    try:
        result = client.customers.create_customer(
            body={
                "idempotency_key": str(uuid.uuid4()),
                "email_address": email,
                "given_name": first_name,
                "family_name": last_name
            }
        )
        
        if result.is_success():
            customer = result.body['customer']
            return {
                'success': True,
                'customer_id': customer['id']
            }
        else:
            return {
                'success': False,
                'errors': result.errors
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def cancel_subscription(subscription_id):
    """Cancel a subscription"""
    try:
        result = client.subscriptions.cancel_subscription(
            subscription_id=subscription_id
        )
        
        if result.is_success():
            return {'success': True}
        else:
            return {
                'success': False,
                'errors': result.errors
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# Flask routes for payment handling
app_payments = Flask(__name__)

@app_payments.route('/subscribe', methods=['POST'])
def handle_subscription():
    """
    Handle subscription signup
    Expects: {email, first_name, last_name, plan, payment_token}
    """
    data = request.json
    
    # Create customer
    customer_result = create_customer(
        data['email'],
        data['first_name'],
        data['last_name']
    )
    
    if not customer_result['success']:
        return jsonify(customer_result), 400
    
    # Store payment card
    # ... (Square card storage logic)
    
    # Create subscription
    subscription_result = create_subscription(
        customer_result['customer_id'],
        data['plan'],
        data['payment_token']
    )
    
    return jsonify(subscription_result)

@app_payments.route('/cancel', methods=['POST'])
def handle_cancellation():
    """Cancel subscription"""
    data = request.json
    result = cancel_subscription(data['subscription_id'])
    return jsonify(result)