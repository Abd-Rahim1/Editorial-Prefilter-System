# Layer 3 Latency Benchmark

## Methodology
- **N**: 1000 sequential online predictions
- **Environment**: Local development
- **Metric**: Execution time (`inference_time_ms`) returned by `Layer3Prediction`

## Results
- **Cold Initialization**: 2538.03 ms
- **Warm Inference**:
  - Minimum: 9.37 ms
  - Mean: 13.90 ms
  - Median: 12.99 ms
  - 95th Percentile: 20.34 ms
  - 99th Percentile: 28.67 ms
  - Maximum: 72.58 ms

## Conclusion
Warm Layer 3 inference operated in the tens-of-milliseconds range in the local development environment, confirming compliance with the < 30ms soft latency target for typical requests.
