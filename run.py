

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
MODEL_PATH = os.path.join(MODELS_DIR, 'best_model.pkl')


def train_if_needed():
    if not os.path.exists(MODEL_PATH):
        print("=" * 50)
        print("No trained model found. Training now...")
        print("This may take a few minutes.")
        print("=" * 50)
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, 'backend', 'train.py')],
            cwd=BASE_DIR
        )
        if result.returncode != 0:
            print("Training failed! Please run: python backend/train.py")
            sys.exit(1)
        print("\nTraining complete!")
    else:
        print("[OK] Trained model found.")


def start_server():
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "=" * 50)
    print("Starting ThyroScan Server")
    print(f"   URL: http://0.0.0.0:{port}")
    print("   Press Ctrl+C to stop")
    print("=" * 50 + "\n")
    from backend.app import app
    app.run(debug=False, host='0.0.0.0', port=port)


if __name__ == '__main__':
    os.chdir(BASE_DIR)
    train_if_needed()
    start_server()
