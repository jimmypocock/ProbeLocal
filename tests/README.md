# Greg Testing Suite

## Overview

Greg includes comprehensive testing capabilities to evaluate model performance across different use cases:

1. **Invoice Q&A Testing** - Tests models with structured data extraction from invoices
2. **Story Comprehension Testing** - Tests models' ability to understand context, inferences, and meaning
3. **Model Compatibility Testing** - Quick tests to identify parameter compatibility issues

## Directory Structure

```
tests/
├── unit/                       # Unit tests for individual components
├── integration/                # Integration tests with PDFs and models
├── fixtures/                   # Test data (PDFs, configs)
│   ├── test_invoice.pdf       # Invoice for structured data testing
│   └── test_story.pdf         # Story for comprehension testing
├── results/                    # Test outputs and reports
├── test_all_models.py         # Invoice Q&A test runner
├── test_story_comprehension.py # Story comprehension test runner
└── README.md                  # This file
```

## Test Suites

### 1. Invoice Q&A Testing
Tests models' ability to extract structured information from a sample invoice.

**What it tests:**
- Basic data retrieval (invoice number, amounts, dates)
- Complex queries (services provided, payment terms)
- Calculation abilities (discount amounts, hourly rates)
- Accuracy based on expected keywords

**Run:**
```bash
# Test all models
make test-models

# Test specific models
python tests/test_all_models.py --models deepseek mistral

# Test with custom PDF
python tests/test_all_models.py --pdf /path/to/invoice.pdf
```

### 2. Story Comprehension Testing
Tests models' ability to understand narrative context, symbolism, and deeper meaning.

**What it tests:**
- Context understanding and inference
- Character analysis and transformation
- Thematic interpretation
- Symbolic meaning comprehension
- Hidden meanings and subtext
- 12 carefully crafted questions requiring deep understanding

**Run:**
```bash
# Test all models
python tests/test_story_comprehension.py

# Test specific models
python tests/test_story_comprehension.py --models deepseek phi

# Use custom story PDF
python tests/test_story_comprehension.py --story-pdf /path/to/story.pdf
```

### 3. Model Compatibility Testing
Quick parameter compatibility test without PDF processing.

**What it tests:**
- Which parameters each model accepts
- Identifies 422 errors and incompatibilities
- Generates model configuration file

**Run:**
```bash
make test-models-quick
```

## Running All Tests

To run both invoice and story comprehension tests on all available models:

```bash
# Run all test suites
./tests/run_all_tests.sh
```

Or manually:
```bash
# Start services if not running
make run

# In another terminal, run tests sequentially
python tests/test_all_models.py && python tests/test_story_comprehension.py
```

## Understanding Results

### Invoice Test Results
- **Accuracy**: Based on finding expected keywords in answers
- **Response Time**: How long each question takes
- **Error Rate**: Percentage of failed questions

### Story Comprehension Results
- **Comprehension Score**: 0-1 scale based on key concepts identified
- **Inference Questions**: Marked separately as they require deeper understanding
- **Response Quality**: Longer, detailed answers score higher

### Interpreting Scores
- **Invoice Tests**: High accuracy (>80%) indicates good structured data extraction
- **Story Tests**: High comprehension (>0.7) indicates good contextual understanding
- **Combined**: Models performing well on both show versatility

## Common Issues and Fixes

### Deepseek 422 Errors
```bash
python tests/unit/fix_deepseek.py
```

### Service Not Running
Ensure all services are running:
```bash
make run
```

### Memory Issues
For large PDFs or multiple model tests:
```bash
# Monitor memory usage
make monitor

# Clean up between tests
make clean
```

## Test Data

### Creating Test PDFs
1. **Invoice**: Structured data with tables, numbers, dates
2. **Story**: Rich narrative with context, themes, symbolism

### Adding New Tests
1. Add PDF to `tests/fixtures/`
2. Create test script following pattern of existing tests
3. Update this README with test description

## Results Location

All test results are saved to `tests/results/` with timestamps:
- `model_test_results_YYYYMMDD_HHMMSS.json` - Invoice tests
- `story_comprehension_YYYYMMDD_HHMMSS.json` - Story tests
- `latest.json` - Symlink to most recent test

## Best Practices

1. **Run tests after model changes** to ensure compatibility
2. **Test new models** before adding to production
3. **Compare results** across model updates
4. **Save important results** for regression testing
5. **Clean between tests** with `make clean` if needed