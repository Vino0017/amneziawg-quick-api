from flask import Flask, request, jsonify
from functools import wraps
from awg_manager import AmneziaWGManager
from config import Config
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
config = Config()
manager = AmneziaWGManager()

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if config.API_KEY:
            api_key = request.headers.get('X-API-Key')
            if not api_key or api_key != config.API_KEY:
                return jsonify({'error': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

@app.route('/api/users', methods=['POST'])
@require_api_key
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400
        
        user_id = data['user_id']
        name = data.get('name')
        
        logger.info(f"Creating user: {user_id}")
        user = manager.create_user(user_id, name)
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'ip': user['ip'],
                'public_key': user['public_key'],
                'client_config': user['client_config']
            }
        }), 201
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
@require_api_key
def get_user(user_id):
    """Get user information"""
    try:
        user = manager.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'ip': user['ip'],
                'public_key': user['public_key'],
                'client_config': user['client_config']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
@require_api_key
def delete_user(user_id):
    """Delete a user"""
    try:
        logger.info(f"Deleting user: {user_id}")
        manager.delete_user(user_id)
        
        return jsonify({
            'success': True,
            'message': f'User {user_id} deleted successfully'
        }), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/users', methods=['GET'])
@require_api_key
def list_users():
    """List all users"""
    try:
        users = manager.list_users()
        return jsonify({
            'success': True,
            'users': users,
            'total': len(users)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/server/status', methods=['GET'])
@require_api_key
def server_status():
    """Get server status"""
    try:
        status = manager.get_server_status()
        return jsonify({
            'success': True,
            'status': status
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info(f"Starting AmneziaWG API on {config.API_HOST}:{config.API_PORT}")
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=False
    )
