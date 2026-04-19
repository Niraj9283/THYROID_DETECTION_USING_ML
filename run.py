
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def start_server():
    print("\n" + "=" * 50)
    print("🚀 Starting ThyroScan Server")
    print("   URL: http://localhost:5000")
    print("   Press Ctrl+C to stop")
    print("=" * 50 + "\n")
    from backend.app import app
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)


if __name__ == '__main__':
    os.chdir(BASE_DIR)
    start_server()
