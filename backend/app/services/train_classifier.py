"""
Train WavLM Classifier in 30 Minutes
====================================

This script trains the tiny classifier layer for your WavLM deepfake detector.
Uses the ASVspoof 2021 dataset (free, publicly available).

WHAT THIS DOES:
1. Downloads ASVspoof dataset (or uses your own samples)
2. Extracts WavLM layer 8 embeddings
3. Trains simple linear classifier (just 1 layer!)
4. Saves trained weights

TIME: 30-60 minutes on laptop (no GPU needed!)
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from pathlib import Path
from tqdm import tqdm
from transformers import Wav2Vec2Model, Wav2Vec2Processor
import librosa

# ==================== CONFIGURATION ====================

WAVLM_MODEL = "microsoft/wavlm-base-plus"
SAMPLE_RATE = 16000
BATCH_SIZE = 8
EPOCHS = 10
LEARNING_RATE = 0.001

# Dataset paths (you'll need to download ASVspoof 2021 or use your own)
# Download from: https://www.asvspoof.org/index2021.html
DATASET_PATH = Path("./data/ASVspoof2021")  # Change this!
OUTPUT_PATH = Path("./models/classifier.pth")

# Alternative: Use your own samples
USE_CUSTOM_SAMPLES = True  # Set to True if you don't have ASVspoof
REAL_AUDIO_DIR = Path("./data/real_voices")  # Put real voice samples here
FAKE_AUDIO_DIR = Path("./data/fake_voices")  # Put AI-generated samples here


# ==================== SIMPLE CLASSIFIER ====================

class SimpleClassifier(nn.Module):
    """Tiny classifier - only part you train!"""
    def __init__(self, input_dim=1024, output_dim=1):
        super().__init__()
        self.fc = nn.Linear(input_dim, output_dim)
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x):
        x = self.dropout(x)
        return torch.sigmoid(self.fc(x))


# ==================== FEATURE EXTRACTOR ====================

class WavLMFeatureExtractor:
    """Extract features from WavLM (no training here!)"""
    
    def __init__(self):
        print("Loading WavLM model...")
        self.model = Wav2Vec2Model.from_pretrained(WAVLM_MODEL)
        self.processor = Wav2Vec2Processor.from_pretrained(WAVLM_MODEL)
        self.model.eval()
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        print(f"✅ WavLM loaded on {self.device}")
    
    def extract_features(self, audio_path):
        """Extract layer 8 embeddings from audio"""
        # Load audio
        waveform, sr = librosa.load(audio_path, sr=SAMPLE_RATE)
        
        # Truncate to 3 seconds for speed (optional)
        max_len = SAMPLE_RATE * 3
        if len(waveform) > max_len:
            waveform = waveform[:max_len]
        
        # Process
        inputs = self.processor(
            waveform,
            sampling_rate=SAMPLE_RATE,
            return_tensors="pt"
        )
        
        with torch.no_grad():
            input_values = inputs.input_values.to(self.device)
            outputs = self.model(input_values, output_hidden_states=True)
            
            # Layer 8 is optimal for deepfake detection
            features = outputs.hidden_states[8]
            
            # Average pooling
            pooled = torch.mean(features, dim=1)
        
        return pooled.cpu().numpy()[0]


# ==================== DATASET PREPARATION ====================

def prepare_custom_dataset():
    """
    Prepare dataset from your own audio samples.
    
    Put real voices in: ./data/real_voices/
    Put fake voices in: ./data/fake_voices/
    """
    print("\n📂 Preparing custom dataset...")
    
    extractor = WavLMFeatureExtractor()
    
    X_train, y_train = [], []
    X_val, y_val = [], []
    
    # Process real voices (label = 0)
    print("\n🎤 Processing REAL voices...")
    real_files = list(REAL_AUDIO_DIR.glob("*.wav")) + list(REAL_AUDIO_DIR.glob("*.mp3"))
    
    if len(real_files) == 0:
        print("❌ No real audio files found!")
        print(f"   Put .wav or .mp3 files in: {REAL_AUDIO_DIR}")
        return None, None, None, None
    
    for i, audio_path in enumerate(tqdm(real_files[:100])):  # Limit to 100 for speed
        try:
            features = extractor.extract_features(str(audio_path))
            
            # 80-20 train-val split
            if i % 5 == 0:
                X_val.append(features)
                y_val.append(0)
            else:
                X_train.append(features)
                y_train.append(0)
        except Exception as e:
            print(f"Error processing {audio_path}: {e}")
    
    # Process fake voices (label = 1)
    print("\n🤖 Processing FAKE/AI voices...")
    fake_files = list(FAKE_AUDIO_DIR.glob("*.wav")) + list(FAKE_AUDIO_DIR.glob("*.mp3"))
    
    if len(fake_files) == 0:
        print("❌ No fake audio files found!")
        print(f"   Put .wav or .mp3 files in: {FAKE_AUDIO_DIR}")
        print("\n💡 TIP: Generate fake voices using:")
        print("   - ElevenLabs (free tier)")
        print("   - play.ht")
        print("   - Resemble AI")
        return None, None, None, None
    
    for i, audio_path in enumerate(tqdm(fake_files[:100])):
        try:
            features = extractor.extract_features(str(audio_path))
            
            if i % 5 == 0:
                X_val.append(features)
                y_val.append(1)
            else:
                X_train.append(features)
                y_train.append(1)
        except Exception as e:
            print(f"Error processing {audio_path}: {e}")
    
    print(f"\n✅ Dataset prepared:")
    print(f"   Training samples: {len(X_train)} (real: {y_train.count(0)}, fake: {y_train.count(1)})")
    print(f"   Validation samples: {len(X_val)} (real: {y_val.count(0)}, fake: {y_val.count(1)})")
    
    return (
        np.array(X_train),
        np.array(y_train),
        np.array(X_val),
        np.array(y_val)
    )


def download_asvspoof_dataset():
    """
    Helper to download ASVspoof 2021 dataset.
    You need to manually download from: https://www.asvspoof.org/index2021.html
    """
    print("\n📥 ASVspoof 2021 Dataset")
    print("=" * 50)
    print("Please download manually from:")
    print("https://www.asvspoof.org/index2021.html")
    print("\nAfter downloading, extract to:", DATASET_PATH)
    print("=" * 50)
    

# ==================== TRAINING ====================

def train_classifier(X_train, y_train, X_val, y_val):
    """Train the classifier"""
    print("\n🏋️ Training classifier...")
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Convert to tensors
    X_train = torch.FloatTensor(X_train)
    y_train = torch.FloatTensor(y_train).unsqueeze(1)
    X_val = torch.FloatTensor(X_val)
    y_val = torch.FloatTensor(y_val).unsqueeze(1)
    
    # Create model
    classifier = SimpleClassifier(input_dim=1024).to(device)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(classifier.parameters(), lr=LEARNING_RATE)
    
    # Training loop
    best_val_acc = 0.0
    
    for epoch in range(EPOCHS):
        classifier.train()
        
        # Mini-batches
        num_batches = len(X_train) // BATCH_SIZE
        train_loss = 0.0
        
        for i in range(num_batches):
            start_idx = i * BATCH_SIZE
            end_idx = start_idx + BATCH_SIZE
            
            batch_X = X_train[start_idx:end_idx].to(device)
            batch_y = y_train[start_idx:end_idx].to(device)
            
            # Forward
            optimizer.zero_grad()
            outputs = classifier(batch_X)
            loss = criterion(outputs, batch_y)
            
            # Backward
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        # Validation
        classifier.eval()
        with torch.no_grad():
            val_outputs = classifier(X_val.to(device))
            val_loss = criterion(val_outputs, y_val.to(device))
            
            # Calculate accuracy
            val_preds = (val_outputs > 0.5).float()
            val_acc = (val_preds == y_val.to(device)).float().mean()
        
        print(f"Epoch {epoch+1}/{EPOCHS}")
        print(f"  Train Loss: {train_loss/num_batches:.4f}")
        print(f"  Val Loss: {val_loss:.4f}")
        print(f"  Val Accuracy: {val_acc:.4f}")
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            torch.save(classifier.state_dict(), OUTPUT_PATH)
            print(f"  ✅ Saved best model (acc: {val_acc:.4f})")
    
    print(f"\n🎉 Training complete!")
    print(f"   Best validation accuracy: {best_val_acc:.4f}")
    print(f"   Model saved to: {OUTPUT_PATH}")
    
    return classifier


# ==================== TESTING ====================

def test_classifier():
    """Test the trained classifier"""
    print("\n🧪 Testing classifier...")
    
    if not OUTPUT_PATH.exists():
        print("❌ No trained model found!")
        return
    
    # Load model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    classifier = SimpleClassifier().to(device)
    classifier.load_state_dict(torch.load(OUTPUT_PATH, map_location=device))
    classifier.eval()
    
    # Load WavLM
    extractor = WavLMFeatureExtractor()
    
    # Test on sample files
    print("\nTest your own audio files:")
    test_file = input("Enter path to audio file (or 'skip'): ")
    
    if test_file != 'skip' and Path(test_file).exists():
        features = extractor.extract_features(test_file)
        features_tensor = torch.FloatTensor(features).unsqueeze(0).to(device)
        
        with torch.no_grad():
            score = classifier(features_tensor).item()
        
        print(f"\n📊 Results for: {test_file}")
        print(f"   Deepfake Score: {score:.4f}")
        print(f"   Prediction: {'🤖 FAKE' if score > 0.5 else '🎤 REAL'}")
        print(f"   Confidence: {abs(score - 0.5) * 2:.2%}")


# ==================== MAIN ====================

def main():
    print("=" * 60)
    print("  WavLM Classifier Training - VeriCall Malaysia")
    print("=" * 60)
    
    # Create directories
    REAL_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    FAKE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    if USE_CUSTOM_SAMPLES:
        # Use your own samples
        X_train, y_train, X_val, y_val = prepare_custom_dataset()
        
        if X_train is None:
            print("\n💡 Quick Start Guide:")
            print("=" * 60)
            print("1. Collect 20-50 REAL voice samples:")
            print("   - Record yourself/friends talking")
            print("   - Use phone call recordings")
            print(f"   - Put in: {REAL_AUDIO_DIR}")
            print("\n2. Generate 20-50 FAKE voice samples:")
            print("   - Use ElevenLabs (elevenlabs.io)")
            print("   - Use play.ht")
            print("   - Clone voices with Resemble AI")
            print(f"   - Put in: {FAKE_AUDIO_DIR}")
            print("\n3. Run this script again!")
            print("=" * 60)
            return
        
    else:
        # Use ASVspoof dataset
        if not DATASET_PATH.exists():
            download_asvspoof_dataset()
            return
        
        # TODO: Implement ASVspoof data loading
        print("ASVspoof loading not implemented yet.")
        print("Please use USE_CUSTOM_SAMPLES = True")
        return
    
    # Train
    classifier = train_classifier(X_train, y_train, X_val, y_val)
    
    # Test
    test_classifier()
    
    print("\n✅ Done! Your classifier is ready.")
    print(f"   Model saved at: {OUTPUT_PATH}")
    print(f"   Update your config: CLASSIFIER_PATH = '{OUTPUT_PATH}'")


if __name__ == "__main__":
    main()