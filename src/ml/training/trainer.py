"""
Trainer para el modelo de predicción de riesgo de VitalSync.

Entrena el modelo VitalRiskNetwork con datos sintéticos o reales.
"""
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Dict, Optional, Tuple, List
from pathlib import Path
import json
from datetime import datetime

from src.ml.models.vital_risk_network import VitalRiskNetwork, MultiTaskRiskLoss
from src.ml.training.data_generator import create_dataloaders


class VitalRiskTrainer:
    """
    Entrenador para el modelo de riesgo de salud.

    Maneja el ciclo completo de entrenamiento:
    - Training loop con early stopping
    - Validación
    - Guardado de checkpoints
    - Logging de métricas
    """

    def __init__(
        self,
        model: Optional[VitalRiskNetwork] = None,
        device: Optional[str] = None,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = model or VitalRiskNetwork()
        self.model = self.model.to(self.device)

        self.criterion = MultiTaskRiskLoss()
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )

        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5
        )

        self.history: Dict[str, List[float]] = {
            "train_loss": [],
            "val_loss": [],
            "val_risk_mae": [],
            "val_cardio_mae": [],
            "val_resp_mae": [],
            "val_metab_mae": [],
            "val_activity_mae": [],
        }

        self.best_val_loss = float('inf')
        self.epochs_without_improvement = 0

    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = 100,
        early_stopping_patience: int = 15,
        checkpoint_dir: str = "models",
        model_name: str = "vital_risk"
    ) -> Dict[str, List[float]]:
        """
        Entrena el modelo.

        Args:
            train_loader: DataLoader de entrenamiento
            val_loader: DataLoader de validación
            epochs: Número máximo de epochs
            early_stopping_patience: Epochs sin mejora antes de parar
            checkpoint_dir: Directorio para guardar checkpoints
            model_name: Nombre base del modelo

        Returns:
            Historial de métricas
        """
        checkpoint_path = Path(checkpoint_dir)
        checkpoint_path.mkdir(parents=True, exist_ok=True)

        print(f"Training on {self.device}")
        print(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        print("-" * 60)

        for epoch in range(epochs):
            # Training
            train_loss = self._train_epoch(train_loader)
            self.history["train_loss"].append(train_loss)

            # Validation
            val_metrics = self._validate(val_loader)
            val_loss = val_metrics["loss"]
            self.history["val_loss"].append(val_loss)
            self.history["val_risk_mae"].append(val_metrics["risk_mae"])
            self.history["val_cardio_mae"].append(val_metrics["cardio_mae"])
            self.history["val_resp_mae"].append(val_metrics["resp_mae"])
            self.history["val_metab_mae"].append(val_metrics["metab_mae"])
            self.history["val_activity_mae"].append(val_metrics["activity_mae"])

            # Learning rate scheduling
            self.scheduler.step(val_loss)

            # Logging
            print(
                f"Epoch {epoch+1:3d}/{epochs} | "
                f"Train Loss: {train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f} | "
                f"Risk MAE: {val_metrics['risk_mae']:.4f}"
            )

            # Early stopping check
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.epochs_without_improvement = 0

                # Save best model
                self._save_checkpoint(
                    checkpoint_path / f"{model_name}_best.pt",
                    epoch,
                    val_loss
                )
            else:
                self.epochs_without_improvement += 1

            if self.epochs_without_improvement >= early_stopping_patience:
                print(f"\nEarly stopping after {epoch+1} epochs")
                break

        # Save final model
        self._save_checkpoint(
            checkpoint_path / f"{model_name}_final.pt",
            epoch,
            val_loss
        )

        # Save training history
        self._save_history(checkpoint_path / f"{model_name}_history.json")

        print("-" * 60)
        print(f"Training complete. Best val loss: {self.best_val_loss:.4f}")

        return self.history

    def _train_epoch(self, train_loader: DataLoader) -> float:
        """Ejecuta un epoch de entrenamiento"""
        self.model.train()
        total_loss = 0.0

        for batch_features, batch_labels in train_loader:
            batch_features = batch_features.to(self.device)
            batch_labels = {k: v.to(self.device) for k, v in batch_labels.items()}

            self.optimizer.zero_grad()

            outputs = self.model(batch_features)
            loss = self.criterion(outputs, batch_labels)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            total_loss += loss.item()

        return total_loss / len(train_loader)

    def _validate(self, val_loader: DataLoader) -> Dict[str, float]:
        """Evalúa el modelo en el conjunto de validación"""
        self.model.eval()
        total_loss = 0.0

        all_preds = {
            "risk_score": [],
            "cardiovascular": [],
            "respiratory": [],
            "metabolic": [],
            "activity": []
        }
        all_targets = {key: [] for key in all_preds}

        with torch.no_grad():
            for batch_features, batch_labels in val_loader:
                batch_features = batch_features.to(self.device)
                batch_labels = {k: v.to(self.device) for k, v in batch_labels.items()}

                outputs = self.model(batch_features)
                loss = self.criterion(outputs, batch_labels)
                total_loss += loss.item()

                for key in all_preds:
                    all_preds[key].append(outputs[key].cpu())
                    all_targets[key].append(batch_labels[key].cpu())

        # Concatenar predicciones
        for key in all_preds:
            all_preds[key] = torch.cat(all_preds[key])
            all_targets[key] = torch.cat(all_targets[key])

        # Calcular MAE para cada métrica
        metrics = {
            "loss": total_loss / len(val_loader),
            "risk_mae": torch.abs(all_preds["risk_score"] - all_targets["risk_score"]).mean().item(),
            "cardio_mae": torch.abs(all_preds["cardiovascular"] - all_targets["cardiovascular"]).mean().item(),
            "resp_mae": torch.abs(all_preds["respiratory"] - all_targets["respiratory"]).mean().item(),
            "metab_mae": torch.abs(all_preds["metabolic"] - all_targets["metabolic"]).mean().item(),
            "activity_mae": torch.abs(all_preds["activity"] - all_targets["activity"]).mean().item(),
        }

        return metrics

    def _save_checkpoint(self, path: Path, epoch: int, val_loss: float) -> None:
        """Guarda un checkpoint del modelo"""
        torch.save({
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "val_loss": val_loss,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }, path)

    def _save_history(self, path: Path) -> None:
        """Guarda el historial de entrenamiento"""
        with open(path, 'w') as f:
            json.dump(self.history, f, indent=2)


def train_model(
    n_samples: int = 10000,
    epochs: int = 50,
    batch_size: int = 64,
    learning_rate: float = 1e-3,
    checkpoint_dir: str = "models",
    model_name: str = "vital_risk"
) -> Tuple[VitalRiskNetwork, Dict]:
    """
    Función de conveniencia para entrenar el modelo.

    Args:
        n_samples: Número de muestras sintéticas a generar
        epochs: Número de epochs
        batch_size: Tamaño del batch
        learning_rate: Tasa de aprendizaje
        checkpoint_dir: Directorio para checkpoints
        model_name: Nombre del modelo

    Returns:
        Tuple de (modelo entrenado, historial)
    """
    print("Generating synthetic dataset...")
    train_loader, val_loader = create_dataloaders(
        n_samples=n_samples,
        batch_size=batch_size
    )
    print(f"Dataset: {n_samples} samples, {len(train_loader)} train batches, {len(val_loader)} val batches")

    trainer = VitalRiskTrainer(learning_rate=learning_rate)

    history = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=epochs,
        checkpoint_dir=checkpoint_dir,
        model_name=model_name
    )

    return trainer.model, history


if __name__ == "__main__":
    # Entrenar modelo con configuración por defecto
    model, history = train_model(
        n_samples=10000,
        epochs=50,
        batch_size=64
    )

    print("\nFinal metrics:")
    print(f"  Risk MAE: {history['val_risk_mae'][-1]:.4f}")
    print(f"  Cardio MAE: {history['val_cardio_mae'][-1]:.4f}")
    print(f"  Resp MAE: {history['val_resp_mae'][-1]:.4f}")
    print(f"  Metab MAE: {history['val_metab_mae'][-1]:.4f}")
    print(f"  Activity MAE: {history['val_activity_mae'][-1]:.4f}")
