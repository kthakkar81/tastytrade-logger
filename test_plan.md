# Tastytrade Logger Test Plan

## Test Coverage

### Phase 1: Unit Tests
- [x] OAuth authentication
- [x] Token refresh mechanism
- [ ] Transaction grouping
- [ ] Strategy classification
- [ ] Price calculations
- [ ] Fee calculations
- [ ] Roll detection

### Phase 2: Integration Tests
- [ ] End-to-end API → processed trades
- [ ] Real transaction parsing
- [ ] Multi-leg strategy detection

### Phase 3: Manual Validation
- [ ] Verify sample trades match actual Tastytrade data
- [ ] Check P&L calculations
- [ ] Validate roll detection accuracy

---

## Test Execution Plan

### 1. Unit Tests (Automated)
Run: `pytest test_tastytrade_logger.py -v`

### 2. Integration Tests (Live API)
Run: `python test_integration.py`

### 3. Manual Verification
Run: `python manual_test.py`
- Review first 10 processed trades
- Compare against Tastytrade UI
- Validate all calculations

---

## Success Criteria

✅ All unit tests pass  
✅ API authentication works consistently  
✅ Token refresh handles expiration  
✅ Strategy classification >95% accurate  
✅ P&L calculations match Tastytrade  
✅ Roll detection identifies linked trades  
✅ No data loss in processing pipeline  

---

## Test Data Requirements

- Minimum 30 days of transaction history
- Mix of strategies: CSP, spreads, rolls, closes
- Various underlyings (UBER, TSLA, AAPL, etc.)
- Both winning and losing trades
