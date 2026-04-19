from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class PredictionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    input_features = db.Column(db.Text)  # JSON string of input dict
    prediction = db.Column(db.String(50))
    confidence = db.Column(db.Float)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'input_features': json.loads(self.input_features),
            'prediction': self.prediction,
            'confidence': round(self.confidence, 2)
        }

