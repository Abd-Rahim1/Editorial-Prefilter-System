"""
Data preprocessing module
Handles cleaning, normalization, and preparation of manuscript data for ML models
"""

"""
Data preprocessing module
Handles cleaning, normalization, and preparation of manuscript data for ML models
"""

import re
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter
import sys

sys.path.append(str(Path(__file__).parent.parent))
from utils.text_cleaning import clean_text


class TextPreprocessor:
    """Preprocess text data for ML models"""
    
    def __init__(self):
        self.stopwords = self._get_stopwords()
    
    def _get_stopwords(self) -> set:
        """Get set of common stopwords"""
        return {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with', 'the', 'this', 'that', 'these',
            'those', 'but', 'or', 'so', 'for', 'nor', 'yet', 'such', 'can',
            'may', 'might', 'must', 'should', 'would', 'could'
        }
    
    def remove_stopwords(self, text: str) -> str:
        """Remove common stopwords from text"""
        if not text:
            return ""
        words = text.lower().split()
        words = [w for w in words if w not in self.stopwords and len(w) > 2]
        return ' '.join(words)
    
    def remove_special_characters(self, text: str) -> str:
        """Remove special characters but keep important punctuation"""
        if not text:
            return ""
        # Keep letters, numbers, spaces, and basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\'\"\-]', ' ', text)
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def normalize_text(self, text: str) -> str:
        """Complete text normalization pipeline"""
        if not text:
            return ""
        text = text.lower()
        text = self.remove_special_characters(text)
        text = self.remove_stopwords(text)
        return text
    
    def extract_ngrams(self, text: str, n: int = 2, top_k: int = 100) -> List[str]:
        """Extract top-k n-grams from text"""
        if not text:
            return []
        
        words = text.split()
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            ngrams.append(ngram)
        
        # Get most common n-grams
        ngram_counts = Counter(ngrams)
        return [ngram for ngram, _ in ngram_counts.most_common(top_k)]
    
    def extract_keywords(self, text: str, top_k: int = 20) -> List[str]:
        """Extract important keywords (excluding stopwords)"""
        if not text:
            return []
        
        words = text.lower().split()
        words = [w for w in words if w not in self.stopwords and len(w) > 3]
        word_counts = Counter(words)
        return [word for word, _ in word_counts.most_common(top_k)]


class FeatureExtractor:
    """Extract features from manuscript data"""
    
    def __init__(self):
        self.text_preprocessor = TextPreprocessor()
    
    def extract_statistical_features(self, text: str) -> Dict[str, Any]:
        """Extract statistical features from text"""
        if not text:
            return {
                'char_count': 0,
                'word_count': 0,
                'sentence_count': 0,
                'avg_word_length': 0,
                'avg_sentence_length': 0,
                'unique_word_ratio': 0,
                'punctuation_count': 0,
                'capital_word_count': 0
            }
        
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        
        # Calculate features
        char_count = len(text)
        word_count = len(words)
        sentence_count = len(sentences)
        avg_word_length = char_count / max(1, word_count)
        avg_sentence_length = word_count / max(1, sentence_count)
        
        unique_words = set(words)
        unique_word_ratio = len(unique_words) / max(1, word_count)
        
        punctuation_count = sum(1 for c in text if c in '.,!?;:')
        capital_word_count = sum(1 for w in words if w and w[0].isupper())
        
        return {
            'char_count': char_count,
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_word_length': round(avg_word_length, 2),
            'avg_sentence_length': round(avg_sentence_length, 2),
            'unique_word_ratio': round(unique_word_ratio, 3),
            'punctuation_count': punctuation_count,
            'capital_word_count': capital_word_count
        }
    
    def extract_structural_features_from_sections(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """Extract features based on section presence and content"""
        features = {}
        
        # Section presence (binary)
        important_sections = ['abstract', 'introduction', 'methodology', 'experiments', 'conclusions', 'references']
        for section in important_sections:
            features[f'has_{section}'] = 1 if sections.get(section) and len(sections[section]) > 50 else 0
        
        # Section lengths
        for section, content in sections.items():
            if content:
                features[f'{section}_length'] = len(content)
                features[f'{section}_words'] = len(content.split())
        
        # Missing sections count
        features['missing_sections_count'] = sum(1 for s in important_sections if not features.get(f'has_{s}', 0))
        
        # Reference count
        if sections.get('references'):
            ref_text = sections['references']
            # Count reference lines (each line starting with number or [)
            ref_lines = [l for l in ref_text.split('\n') if l.strip() and (l.strip()[0].isdigit() or l.strip().startswith('['))]
            features['reference_count'] = len(ref_lines)
        else:
            features['reference_count'] = 0
        
        return features
    
    def extract_quality_indicators(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """Extract quality indicators from sections"""
        indicators = {}
        
        # Abstract quality
        abstract = sections.get('abstract', '')
        if abstract:
            indicators['abstract_too_short'] = len(abstract.split()) < 50
            indicators['abstract_too_long'] = len(abstract.split()) > 500
            # Check if abstract contains key elements
            indicators['abstract_has_problem'] = any(w in abstract.lower() for w in ['problem', 'challenge', 'issue'])
            indicators['abstract_has_approach'] = any(w in abstract.lower() for w in ['propose', 'present', 'introduce', 'method'])
            indicators['abstract_has_results'] = any(w in abstract.lower() for w in ['result', 'achieve', 'improve', 'outperform'])
        else:
            indicators['abstract_too_short'] = True
            indicators['abstract_too_long'] = False
            indicators['abstract_has_problem'] = False
            indicators['abstract_has_approach'] = False
            indicators['abstract_has_results'] = False
        
        # Methodology indicators
        methodology = sections.get('methodology', '')
        if methodology:
            indicators['methodology_has_details'] = len(methodology.split()) > 200
            indicators['methodology_has_evaluation'] = any(w in methodology.lower() for w in ['evaluate', 'validate', 'experiment', 'dataset'])
        else:
            indicators['methodology_has_details'] = False
            indicators['methodology_has_evaluation'] = False
        
        # Results indicators
        experiments = sections.get('experiments', '')
        if experiments:
            indicators['experiments_has_results'] = len(experiments.split()) > 100
            indicators['experiments_has_comparison'] = any(w in experiments.lower() for w in ['compare', 'baseline', 'state-of-the-art', 'sota'])
            indicators['experiments_has_metrics'] = any(w in experiments.lower() for w in ['accuracy', 'f1', 'precision', 'recall', 'auc'])
        else:
            indicators['experiments_has_results'] = False
            indicators['experiments_has_comparison'] = False
            indicators['experiments_has_metrics'] = False
        
        return indicators
    
    def extract_all_features(self, text: str, sections: Dict[str, str]) -> Dict[str, Any]:
        """Extract all features from text and sections"""
        features = {}
        
        # Statistical features from full text
        stats = self.extract_statistical_features(text)
        features.update(stats)
        
        # Structural features from sections
        structural = self.extract_structural_features_from_sections(sections)
        features.update(structural)
        
        # Quality indicators
        quality = self.extract_quality_indicators(sections)
        features.update(quality)
        
        # Additional computed features
        features['is_too_short'] = features.get('word_count', 0) < 1000
        features['is_too_long'] = features.get('word_count', 0) > 12000
        features['has_few_references'] = features.get('reference_count', 0) < 10
        features['has_many_references'] = features.get('reference_count', 0) > 50
        
        return features


class DatasetBuilder:
    """Build and prepare dataset for training"""
    
    def __init__(self, data_path: str):
        """
        Args:
            data_path: Path to processed data (e.g., './data/processed/')
        """
        self.data_path = Path(data_path)
        self.feature_extractor = FeatureExtractor()
        self.text_preprocessor = TextPreprocessor()
    
    def build_dataset_from_papers(self, papers: List) -> pd.DataFrame:
        """
        Build feature dataset from list of Paper objects
        
        Args:
            papers: List of Paper objects from loader.py
            
        Returns:
            DataFrame with features and labels
        """
        rows = []
        
        for paper in papers:
            # Extract features
            features = self.feature_extractor.extract_all_features(
                paper.full_text, 
                paper.sections
            )
            
            # Add metadata
            row = {
                'paper_id': paper.paper_id,
                'title': paper.title,
                'label': paper.label,
                'decision': paper.decision,
                'venue': paper.venue,
                'year': paper.year,
                **features
            }
            
            # Add preprocessed abstract for TF-IDF
            row['abstract_clean'] = self.text_preprocessor.normalize_text(paper.abstract)
            row['full_text_clean'] = self.text_preprocessor.normalize_text(paper.full_text)
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Save to CSV
        output_file = self.data_path / 'dataset_features.csv'
        df.to_csv(output_file, index=False)
        print(f"✅ Dataset saved to {output_file}")
        
        return df
    
    def create_train_test_split(
        self, 
        df: pd.DataFrame, 
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Create train/test split"""
        from sklearn.model_selection import train_test_split
        
        # Filter valid labels
        df_valid = df[df['label'].isin([0, 1])].copy()
        
        X = df_valid.drop(['paper_id', 'title', 'decision', 'label'], axis=1)
        y = df_valid['label']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        train_df = df_valid.loc[X_train.index].copy()
        test_df = df_valid.loc[X_test.index].copy()
        
        # Save splits
        train_df.to_csv(self.data_path / 'train_split.csv', index=False)
        test_df.to_csv(self.data_path / 'test_split.csv', index=False)
        
        print(f"\n✅ Train size: {len(train_df)}")
        print(f"✅ Test size: {len(test_df)}")
        print(f"   Train - Accept: {(train_df['label']==1).sum()}, Reject: {(train_df['label']==0).sum()}")
        print(f"   Test  - Accept: {(test_df['label']==1).sum()}, Reject: {(test_df['label']==0).sum()}")
        
        return train_df, test_df
    
    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get list of feature columns (exclude metadata and labels)"""
        exclude_cols = ['paper_id', 'title', 'decision', 'label', 'abstract_clean', 'full_text_clean']
        return [col for col in df.columns if col not in exclude_cols]
    
    def generate_dataset_report(self, df: pd.DataFrame) -> str:
        """Generate a report about the dataset"""
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("DATASET REPORT")
        report_lines.append("=" * 60)
        
        # Basic stats
        report_lines.append(f"\n📊 Basic Statistics:")
        report_lines.append(f"   Total papers: {len(df)}")
        report_lines.append(f"   Accept: {(df['label']==1).sum()}")
        report_lines.append(f"   Reject: {(df['label']==0).sum()}")
        report_lines.append(f"   Unknown: {(df['label']==-1).sum()}")
        
        # Text statistics
        report_lines.append(f"\n📝 Text Statistics:")
        report_lines.append(f"   Avg word count: {df['word_count'].mean():.0f}")
        report_lines.append(f"   Avg abstract length: {df['abstract_length'] if 'abstract_length' in df.columns else 'N/A'}")
        
        # Section presence
        report_lines.append(f"\n📑 Section Presence:")
        section_cols = [c for c in df.columns if c.startswith('has_')]
        for col in section_cols:
            if col in df.columns:
                presence = df[col].mean() * 100
                report_lines.append(f"   {col}: {presence:.1f}%")
        
        # Quality indicators
        report_lines.append(f"\n⚠️ Quality Indicators:")
        quality_cols = ['is_too_short', 'has_few_references', 'missing_sections_count']
        for col in quality_cols:
            if col in df.columns:
                if col == 'missing_sections_count':
                    avg = df[col].mean()
                    report_lines.append(f"   {col}: {avg:.2f} (avg)")
                else:
                    count = df[col].sum()
                    pct = (count / len(df)) * 100
                    report_lines.append(f"   {col}: {count} ({pct:.1f}%)")
        
        return "\n".join(report_lines)


def preprocess_peerread_dataset(
    peerread_path: str, 
    output_path: str,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """
    Complete preprocessing pipeline for PeerRead dataset
    
    Args:
        peerread_path: Path to PeerRead data (e.g., './data/peerread/')
        output_path: Path to save processed data
        limit: Optional limit on number of papers
    
    Returns:
        DataFrame with processed features
    """
    from src.dataset.loader import PeerReadLoader
    
    print("=" * 60)
    print("PREPROCESSING PEERREAD DATASET")
    print("=" * 60)
    
    # Load data
    loader = PeerReadLoader(peerread_path)
    train_papers = loader.load_split('train')
    dev_papers = loader.load_split('dev')
    test_papers = loader.load_split('test')
    
    all_papers = train_papers + dev_papers + test_papers
    
    if limit:
        all_papers = all_papers[:limit]
    
    print(f"\n📚 Loaded {len(all_papers)} total papers")
    
    # Build dataset
    builder = DatasetBuilder(output_path)
    df = builder.build_dataset_from_papers(all_papers)
    
    # Generate report
    report = builder.generate_dataset_report(df)
    print(report)
    
    # Save report
    report_path = Path(output_path) / 'dataset_report.txt'
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\n✅ Report saved to {report_path}")
    
    # Create train/test split
    train_df, test_df = builder.create_train_test_split(df)
    
    # Save feature list
    feature_cols = builder.get_feature_columns(df)
    with open(Path(output_path) / 'feature_columns.json', 'w') as f:
        json.dump(feature_cols, f, indent=2)
    
    return df


if __name__ == "__main__":
    import sys
    
    # Example usage
    peerread_path = "./data/peerread/"
    output_path = "./data/processed/"
    
    # Check if paths exist
    if not Path(peerread_path).exists():
        print(f"❌ PeerRead path not found: {peerread_path}")
        print("   Please update the path to your PeerRead data")
        sys.exit(1)
    
    # Run preprocessing
    df = preprocess_peerread_dataset(
        peerread_path=peerread_path,
        output_path=output_path,
        limit=50  # Start with 50 papers for testing
    )
    
    print("\n✅ Preprocessing complete!")
    print(f"   Dataset shape: {df.shape}")
    print(f"   Features available: {len([c for c in df.columns if not c.startswith('paper')])}")