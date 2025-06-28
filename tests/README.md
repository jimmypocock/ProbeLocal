# ProbeLocal Testing Suite

## Directory Structure

```
tests/
├── unit/               # Unit tests for individual components
├── integration/        # Integration tests with PDFs and models
├── fixtures/           # Test data (PDFs, configs)
├── results/           # Test outputs and reports
├── test_all_models.py # Main test runner
└── README.md          # This file
```

## Running Tests

### Quick Test
```bash
make test-models
```

### Comprehensive PDF Test
```bash
python tests/test_all_models.py --pdf tests/fixtures/test_invoice.pdf
```

### Test Specific Model
```bash
python tests/test_all_models.py --models deepseek --pdf tests/fixtures/test_invoice.pdf
```

## Test Categories

1. **Model Compatibility** - Tests which parameters work with each model
2. **PDF Processing** - Tests document upload and text extraction
3. **Question Answering** - Tests accuracy of answers from PDFs
4. **Performance** - Measures response times and memory usage
5. **Error Handling** - Tests 422 and other error scenarios