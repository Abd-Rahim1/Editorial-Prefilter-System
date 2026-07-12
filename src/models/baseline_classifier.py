"""
Baseline Classifier (M1) - TF-IDF + Logistic Regression
For Week 1-2 deliverable
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report, 
    confusion_matrix, 
    f1_score, 
    roc_auc_score,
    accuracy_score,
    precision_score,
    recall_score
)
import matplotlib.pyplot as plt
import seaborn as sns


class BaselineClassifier:
    """Simple non-LLM baseline using TF-IDF + Logistic Regression"""
    
    def __init__(self, data_path: str = "./data/processed/"):
        self.data_path = Path(data_path)
        self.vectorizer = None
        self.classifier = None
    
    def load_data(self, use_full_text: bool = True):
        """Load the ICLR 2017 dataset"""
        df = pd.read_csv(self.data_path / 'iclr_2017_full.csv')
        
        # Filter to only train split for training
        train_df = df[df['split'] == 'train'].copy()
        test_df = df[df['split'] == 'test'].copy()
        
        # Use dev as validation
        dev_df = df[df['split'] == 'dev'].copy()
        
        print("=" * 60)
        print("DATA LOADED")
        print("=" * 60)
        print(f"Train: {len(train_df)} papers")
        print(f"Dev: {len(dev_df)} papers")
        print(f"Test: {len(test_df)} papers")
        print(f"Accept rate: {train_df['label'].mean()*100:.1f}%")
        
        # Choose which text to use
        if use_full_text:
            text_col = 'full_text'
            print(f"\nUsing FULL TEXT for features")
        else:
            text_col = 'abstract'
            print(f"\nUsing ABSTRACT only for features")
        
        # Prepare features and labels
        X_train = train_df[text_col].fillna('').values
        y_train = train_df['label'].values
        
        X_dev = dev_df[text_col].fillna('').values
        y_dev = dev_df['label'].values
        
        X_test = test_df[text_col].fillna('').values
        y_test = test_df['label'].values
        
        return X_train, y_train, X_dev, y_dev, X_test, y_test
    
    def train(self, X_train, y_train, X_dev, y_dev):
        """Train the baseline model"""
        print("\n" + "=" * 60)
        print("TRAINING BASELINE CLASSIFIER")
        print("=" * 60)
        
        # Create TF-IDF features
        print("\n1. Creating TF-IDF features...")
        self.vectorizer = TfidfVectorizer(
            max_features=5000,  # Limit vocabulary size
            stop_words='english',
            ngram_range=(1, 2),  # Unigrams and bigrams
            min_df=2,  # Ignore terms that appear in less than 2 docs
            max_df=0.95,  # Ignore terms that appear in >95% of docs
            sublinear_tf=True  # Use 1+log(tf)
        )
        
        X_train_tfidf = self.vectorizer.fit_transform(X_train)
        X_dev_tfidf = self.vectorizer.transform(X_dev)
        
        print(f"   Feature matrix shape: {X_train_tfidf.shape}")
        print(f"   Vocabulary size: {len(self.vectorizer.get_feature_names_out())}")
        
        # Train classifier
        print("\n2. Training Logistic Regression...")
        self.classifier = LogisticRegression(
            C=1.0,
            class_weight='balanced',  # Handle class imbalance
            max_iter=1000,
            random_state=42
        )
        self.classifier.fit(X_train_tfidf, y_train)
        
        # Cross-validation
        print("\n3. Cross-validation (5-fold on train):")
        cv_scores = cross_val_score(
            self.classifier, X_train_tfidf, y_train, 
            cv=5, scoring='f1'
        )
        print(f"   CV F1 scores: {cv_scores}")
        print(f"   Mean CV F1: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
        
        # Evaluate on dev set
        print("\n4. Evaluation on Dev set:")
        y_dev_pred = self.classifier.predict(X_dev_tfidf)
        y_dev_proba = self.classifier.predict_proba(X_dev_tfidf)[:, 1]
        
        dev_f1 = f1_score(y_dev, y_dev_pred)
        dev_auc = roc_auc_score(y_dev, y_dev_proba)
        
        print(f"   F1-score: {dev_f1:.4f}")
        print(f"   AUROC: {dev_auc:.4f}")
        
        return dev_f1, dev_auc
    
    def evaluate(self, X_test, y_test):
        """Evaluate on test set"""
        print("\n" + "=" * 60)
        print("TEST SET EVALUATION")
        print("=" * 60)
        
        X_test_tfidf = self.vectorizer.transform(X_test)
        y_pred = self.classifier.predict(X_test_tfidf)
        y_proba = self.classifier.predict_proba(X_test_tfidf)[:, 1]
        
        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)
        
        print(f"\nMetrics:")
        print(f"   Accuracy:  {accuracy:.4f}")
        print(f"   Precision: {precision:.4f}")
        print(f"   Recall:    {recall:.4f}")
        print(f"   F1-score:  {f1:.4f}")
        print(f"   AUROC:     {auc:.4f}")
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"\nConfusion Matrix:")
        print(f"              Predicted")
        print(f"              Reject  Accept")
        print(f"   Actual Reject  {cm[0,0]:4d}    {cm[0,1]:4d}")
        print(f"          Accept   {cm[1,0]:4d}    {cm[1,1]:4d}")
        
        # Reject recall (important for desk rejection)
        reject_recall = cm[0,0] / (cm[0,0] + cm[0,1]) if (cm[0,0] + cm[0,1]) > 0 else 0
        print(f"\n   Reject Recall (true desk reject rate): {reject_recall:.4f}")
        
        # Classification Report
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Reject', 'Accept']))
        
        return {
            'accuracy': float(accuracy),  # Convert to float
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'auc': float(auc),
            'reject_recall': float(reject_recall),
            'confusion_matrix': cm.tolist()  # Convert to list
        }
    
    def plot_results(self, X_test, y_test):
        """Plot confusion matrix and ROC curve"""
        X_test_tfidf = self.vectorizer.transform(X_test)
        y_pred = self.classifier.predict(X_test_tfidf)
        y_proba = self.classifier.predict_proba(X_test_tfidf)[:, 1]
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0],
                    xticklabels=['Reject', 'Accept'],
                    yticklabels=['Reject', 'Accept'])
        axes[0].set_title('Confusion Matrix')
        axes[0].set_ylabel('Actual')
        axes[0].set_xlabel('Predicted')
        
        # ROC Curve
        from sklearn.metrics import roc_curve
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        axes[1].plot(fpr, tpr, 'b-', label=f'ROC (AUC = {roc_auc_score(y_test, y_proba):.3f})')
        axes[1].plot([0, 1], [0, 1], 'r--', label='Random')
        axes[1].set_xlabel('False Positive Rate')
        axes[1].set_ylabel('True Positive Rate')
        axes[1].set_title('ROC Curve')
        axes[1].legend()
        
        plt.tight_layout()
        
        # Save plot
        output_path = self.data_path / 'baseline_results.png'
        plt.savefig(output_path, dpi=150)
        print(f"\nPlot saved to {output_path}")
        plt.show()
    
    def get_top_features(self, n: int = 20):
        """Get top features for accept/reject classes"""
        feature_names = self.vectorizer.get_feature_names_out()
        coefficients = self.classifier.coef_[0]
        
        # Top features for Accept (positive coefficients)
        top_accept_idx = np.argsort(coefficients)[-n:][::-1]
        top_accept = [(feature_names[i], coefficients[i]) for i in top_accept_idx]
        
        # Top features for Reject (negative coefficients)
        top_reject_idx = np.argsort(coefficients)[:n]
        top_reject = [(feature_names[i], coefficients[i]) for i in top_reject_idx]
        
        print("\n" + "=" * 60)
        print("TOP FEATURES")
        print("=" * 60)
        
        print("\nTop features associated with ACCEPT:")
        for feature, coef in top_accept[:10]:
            print(f"   {feature}: {coef:.4f}")
        
        print("\nTop features associated with REJECT:")
        for feature, coef in top_reject[:10]:
            print(f"   {feature}: {coef:.4f}")
        
        return top_accept, top_reject


def main():
    """Run the baseline classifier"""
    print("=" * 60)
    print("BASELINE CLASSIFIER (M1)")
    print("TF-IDF + Logistic Regression")
    print("=" * 60)
    
    classifier = BaselineClassifier()
    
    # Load data
    X_train, y_train, X_dev, y_dev, X_test, y_test = classifier.load_data(use_full_text=True)
    
    # Train
    dev_f1, dev_auc = classifier.train(X_train, y_train, X_dev, y_dev)
    
    # Evaluate on test
    results = classifier.evaluate(X_test, y_test)
    
    # Plot results
    classifier.plot_results(X_test, y_test)
    
    # Show top features
    classifier.get_top_features(15)
    
    # Save results summary
    output_path = Path("./data/processed/baseline_results.json")
    import json
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    
    print("\n" + "=" * 60)
    print(" BASELINE COMPLETE!")
    print("=" * 60)
    print(f"\n Final Test Results:")
    print(f"   F1-score: {results['f1']:.4f}")
    print(f"   AUROC: {results['auc']:.4f}")
    print(f"   Reject Recall: {results['reject_recall']:.4f}")


if __name__ == "__main__":
    main()