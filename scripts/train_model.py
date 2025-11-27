#!/usr/bin/env python3
"""
Script para entrenar el modelo de predicción de riesgo de VitalSync.

Uso:
    python scripts/train_model.py
    python scripts/train_model.py --samples 20000 --epochs 100
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.training.trainer import train_model


def main():
    parser = argparse.ArgumentParser(
        description="Entrena el modelo de predicción de riesgo de VitalSync"
    )
    parser.add_argument("--samples", "-n", type=int, default=10000)
    parser.add_argument("--epochs", "-e", type=int, default=50)
    parser.add_argument("--batch-size", "-b", type=int, default=64)
    parser.add_argument("--learning-rate", "-lr", type=float, default=1e-3)
    parser.add_argument("--output-dir", "-o", type=str, default="models")
    parser.add_argument("--model-name", "-m", type=str, default="vital_risk")

    args = parser.parse_args()

    print("=" * 60)
    print("VitalSync - Entrenamiento del Modelo PyTorch")
    print("=" * 60)
    print(f"  Muestras: {args.samples:,}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print("=" * 60)

    model, history = train_model(
        n_samples=args.samples,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        checkpoint_dir=args.output_dir,
        model_name=args.model_name
    )

    print(f"\nModelo guardado en: {args.output_dir}/{args.model_name}_best.pt")


if __name__ == "__main__":
    main()
