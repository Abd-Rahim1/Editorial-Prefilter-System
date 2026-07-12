from setuptools import setup, find_packages

setup(
    name="packages.calibration",
    version="1.0.0",
    description="Dual-Mode Layer 3 Calibration & Decision Engine for Editorial Prefilter System",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "scikit-learn>=1.0.0",
        "joblib>=1.1.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0"],
        "xgb": ["xgboost>=1.6.0"],
    },
)
