# Tasks: Advanced Sell Strategy

**Input**: Design documents from `/specs/006-advanced-sell-strategy/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included as they validate critical risk management behavior (stop-loss must never fail).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `trading_wizard_web/backend/src/`, `trading_wizard_web/backend/tests/`

---

## Phase 1: Setup (Database Migration)

**Purpose**: Add required database field for take-profit tracking

- [X] T001 Create Alembic migration for `partial_take_profit_executed` column in `trading_wizard_web/backend/alembic/versions/`
- [X] T002 Add `partial_take_profit_executed` boolean field to Position model in `trading_wizard_web/backend/src/models/position.py`
- [X] T003 Run database migration to apply schema change

---

## Phase 2: Foundational (SignalScanner Configuration)

**Purpose**: Extend SignalScanner with new configuration parameters that all user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add `take_profit_pct` parameter (default 10.0) to SignalScanner.__init__() in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T005 Add `take_profit_ratio` parameter (default 0.5) to SignalScanner.__init__() in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T006 Add `sell_quantity` and `sell_ratio` fields to indicators dict structure in `trading_wizard_web/backend/src/wizard/signal_scanner.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Stop Loss Protection (Priority: P1) MVP

**Goal**: Ensure stop-loss triggers full exit at -5% loss (existing behavior, must be preserved)

**Independent Test**: Create position with 10,000 KRW entry, simulate 9,500 KRW price (-5%), verify SELL signal with reason "stop_loss_hit" and 100% quantity

### Tests for User Story 1

- [X] T007 [P] [US1] Unit test: stop-loss triggers at exactly -5% threshold in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T008 [P] [US1] Unit test: stop-loss does NOT trigger at -4% in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T009 [P] [US1] Unit test: stop-loss triggers at -10% (beyond threshold) in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`

### Implementation for User Story 1

- [X] T010 [US1] Refactor `scan_for_sell_signals()` to use priority-based evaluation structure in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T011 [US1] Implement stop-loss check as Priority 1 with early return in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T012 [US1] Add sell_quantity (100% of quantity) and sell_ratio (1.0) to stop-loss signal indicators in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T013 [US1] Verify stop-loss reason string is "stop_loss_hit" in `trading_wizard_web/backend/src/wizard/signal_scanner.py`

**Checkpoint**: User Story 1 complete - stop-loss protection verified independently

---

## Phase 4: User Story 2 - Partial Take Profit (Priority: P2)

**Goal**: Trigger 50% sell when position gains +10% (first time only per position)

**Independent Test**: Create position of 100 shares at 10,000 KRW, simulate 11,000 KRW price (+10%), verify SELL signal for 50 shares with reason "take_profit_target_hit"

### Tests for User Story 2

- [X] T014 [P] [US2] Unit test: take-profit triggers at +10% with 50% sell quantity in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T015 [P] [US2] Unit test: take-profit does NOT trigger at +9% in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T016 [P] [US2] Unit test: take-profit does NOT re-trigger when partial_take_profit_executed is True in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T017 [P] [US2] Unit test: minimum 1 share sold when quantity * ratio < 1 (round up) in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`

### Implementation for User Story 2

- [X] T018 [US2] Implement take-profit check as Priority 2 in `scan_for_sell_signals()` in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T019 [US2] Add partial_take_profit_executed check to prevent re-triggering in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T020 [US2] Calculate sell_quantity using `max(1, math.ceil(quantity * take_profit_ratio))` in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T021 [US2] Add sell_ratio to indicators dict for take-profit signals in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T022 [US2] Add `mark_take_profit_executed()` method to Position model in `trading_wizard_web/backend/src/models/position.py`
- [X] T023 [US2] Verify take-profit reason string is "take_profit_target_hit" in `trading_wizard_web/backend/src/wizard/signal_scanner.py`

**Checkpoint**: User Stories 1 AND 2 work independently

---

## Phase 5: User Story 3 - Trend Breakdown Exit (Priority: P3)

**Goal**: Exit remaining position when close < middle band (20 MA), replacing old lower band logic

**Independent Test**: Create position, simulate price dropping below BB_Middle, verify SELL signal for 100% remaining with reason "trend_broken_middle_band"

### Tests for User Story 3

- [X] T024 [P] [US3] Unit test: trend-breakdown triggers when close < BB_Middle in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T025 [P] [US3] Unit test: trend-breakdown does NOT trigger when close >= BB_Middle in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T026 [P] [US3] Unit test: stop-loss takes priority over trend-breakdown in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T027 [P] [US3] Unit test: take-profit and trend-breakdown can coexist (both signals for remaining shares) in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`

### Implementation for User Story 3

- [X] T028 [US3] Remove existing lower band touch condition from `scan_for_sell_signals()` in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T029 [US3] Implement trend-breakdown check as Priority 3 using BB_Middle in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T030 [US3] Handle coexistence with take-profit (generate both signals when applicable) in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T031 [US3] Skip trend-breakdown check if BB_Middle is NaN (insufficient data) in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T032 [US3] Verify trend-breakdown reason string is "trend_broken_middle_band" in `trading_wizard_web/backend/src/wizard/signal_scanner.py`

**Checkpoint**: User Stories 1, 2, AND 3 work independently

---

## Phase 6: User Story 4 - Configurable Sell Parameters (Priority: P3)

**Goal**: Allow customization of stop-loss %, take-profit %, and take-profit ratio

**Independent Test**: Set stop_loss_pct to 3.0%, verify stop-loss triggers at -3% instead of default -5%

### Tests for User Story 4

- [X] T033 [P] [US4] Unit test: custom stop_loss_pct (3.0%) triggers at -3% in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T034 [P] [US4] Unit test: custom take_profit_pct (15.0%) does NOT trigger at +10% in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`
- [X] T035 [P] [US4] Unit test: custom take_profit_ratio (0.7) sells 70% instead of 50% in `trading_wizard_web/backend/tests/unit/test_sell_strategy.py`

### Implementation for User Story 4

- [X] T036 [US4] Add parameter validation for stop_loss_percent (1.0-20.0 range) in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T037 [US4] Add parameter validation for take_profit_pct (5.0-50.0 range) in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T038 [US4] Add parameter validation for take_profit_ratio (0.1-1.0 range) in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T039 [US4] Ensure configuration changes take effect immediately on next scan in `trading_wizard_web/backend/src/wizard/signal_scanner.py`

**Checkpoint**: All user stories complete and independently testable

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration, documentation, and validation

- [X] T040 [P] Integration test: full sell signal flow with all conditions in `trading_wizard_web/backend/tests/integration/test_sell_signals.py`
- [X] T041 [P] Integration test: priority order verification (stop-loss > take-profit > trend-breakdown) in `trading_wizard_web/backend/tests/integration/test_sell_signals.py`
- [X] T042 Verify all sell signals include complete indicators (entry_price, pnl_pct, sell_quantity, sell_ratio, bb_middle) in `trading_wizard_web/backend/src/wizard/signal_scanner.py`
- [X] T043 Run quickstart.md validation scenarios manually
- [X] T044 Update API response schema if needed in `trading_wizard_web/backend/src/api/recommendations.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May generate signals alongside US2
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Configuration only, no logic dependencies

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation tasks in order (refactor → logic → validation)
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T001 → T002 → T003 (sequential - migration before model change)
- **Phase 2**: T004, T005, T006 can run in parallel (different concerns in same file, careful merge)
- **Phase 3-6**: All tests within a story [P] can run in parallel
- **Phase 7**: T040, T041 can run in parallel

---

## Parallel Example: User Story 2 Tests

```bash
# Launch all tests for User Story 2 together:
Task: "Unit test: take-profit triggers at +10% with 50% sell quantity"
Task: "Unit test: take-profit does NOT trigger at +9%"
Task: "Unit test: take-profit does NOT re-trigger when partial_take_profit_executed is True"
Task: "Unit test: minimum 1 share sold when quantity * ratio < 1"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (database migration)
2. Complete Phase 2: Foundational (SignalScanner parameters)
3. Complete Phase 3: User Story 1 (stop-loss - existing behavior preserved)
4. **STOP and VALIDATE**: Run stop-loss tests, verify no regression
5. Deploy/demo if ready - critical risk management working

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test stop-loss → Deploy (MVP - risk protection)
3. Add User Story 2 → Test take-profit → Deploy (profit locking)
4. Add User Story 3 → Test trend-breakdown → Deploy (improved exits)
5. Add User Story 4 → Test configuration → Deploy (customization)

### Critical Path

```
T001 → T002 → T003 → T004/T005/T006 → T010 → T011 → [US1 complete]
                                    ↘ T018 → T019 → [US2 complete]
                                    ↘ T028 → T029 → [US3 complete]
                                    ↘ T036 → T037 → [US4 complete]
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- **IMPORTANT**: Stop-loss (US1) must never break - it's the critical risk management feature
