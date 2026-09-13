# UniOps Pilot Survey — Response Summary

**Form:** [Khảo sát trải nghiệm pilot UniOps — UniGreen](https://docs.google.com/forms/d/1feLr6cBsfpxwbgXq41iMcsqcTv0QvLfiCDCyiraLr30/edit)

**Response analytics:** [Open response analytics](https://docs.google.com/forms/d/1feLr6cBsfpxwbgXq41iMcsqcTv0QvLfiCDCyiraLr30/viewanalytics)

**Responses reviewed:** 3

## Executive summary

The pilot feedback is broadly positive about UniOps as a central place for operational information. The clearest value is order-progress visibility, data synchronization, faster search, and reducing manual work.

The main usability risk is payment-status wording. One of two people who completed the interface task misunderstood **“Chưa có thông tin”** as meaning the customer definitely had not paid. This should be changed to wording such as **“Chưa có dữ liệu xác nhận thanh toán”**.

The accounting responses are useful as signals, but they are not sufficient to approve finance semantics. The finance validation question also produced contradictory answers because respondents selected both specific accounting topics and **“Không cần xác nhận thêm.”**

## 1. Respondent profile

| Role | Responses | Share |
|---|---:|---:|
| Quản lý / ra quyết định | 1 | 33.3% |
| Văn phòng / điều phối | 1 | 33.3% |
| Tài chính / kế toán | 1 | 33.3% |
| Xưởng / sản xuất | 0 | 0% |
| Khác | 0 | 0% |

The sample includes management, office coordination, and finance/accounting, but no factory/production respondent yet.

## 2. Current workflow and system usage

### Difficulty finding information

| Answer | Responses | Share |
|---|---:|---:|
| Rất khó | 0 | 0% |
| Khá khó | 0 | 0% |
| Bình thường | 2 | 66.7% |
| Dễ | 1 | 33.3% |
| Không áp dụng | 0 | 0% |

### Existing tools

- **Paper/Zalo/oral communication:** all 3 respondents use these daily.
- **Excel:** all 3 respondents use Excel daily.
- **EasyBooks:** 1 respondent uses it daily, 1 weekly, and 1 does not use it directly.

### Why paper, Zalo, or oral communication is still used

The written answers were:

- “tiện- nhanh” — convenient and fast.
- “Do thói quen” — because of habit.

One respondent did not provide a written answer.

## 3. Priority use cases

| Priority | Responses | Share |
|---|---:|---:|
| Theo dõi tiến độ đơn hàng | 2 | 66.7% |
| Xem tài chính / công nợ / VAT | 1 | 33.3% |
| Tìm và đối chiếu hóa đơn | 0 | 0% |

Order-progress tracking is the strongest immediate use case.

## 4. Missing information

| Information area | Responses selecting it | Share |
|---|---:|---:|
| Tiến độ / trạng thái đơn hàng | 3 | 100% |
| Sales / doanh số | 3 | 100% |
| Purchases / mua hàng | 3 | 100% |
| Receivables / công nợ phải thu | 3 | 100% |
| Debt / nợ phải trả | 3 | 100% |
| Payment / thanh toán | 2 | 66.7% |
| VAT / thuế GTGT | 2 | 66.7% |

The results indicate that users want a connected operational view spanning orders, sales, purchases, receivables, payables, payment status, and VAT.

## 5. UI/UX task results

### Task 1 — Identify the next order action

- 2/2 respondents selected **“Có, dễ dàng.”**
- No respondent reported uncertainty.

### Task 2 — Understand what is needed to create a new order

- 1/2 selected **“Rõ ràng toàn bộ.”**
- 1/2 selected **“Rõ phần lớn, còn 1–2 mục chưa rõ.”**

The new-order screen is generally understandable, but some fields or instructions could be clearer.

### Task 3 — Interpret “Chưa có thông tin” for payment

- 1/2 correctly understood it as: **UniOps does not have data proving whether payment was made.**
- 1/2 incorrectly understood it as: **the customer definitely has not paid.**

This is the most important usability issue found in the pilot.

Recommended label:

> **Chưa có dữ liệu xác nhận thanh toán**

Optional supporting text:

> UniOps chưa có đủ dữ liệu để kết luận đã trả, chưa trả, trả một phần hoặc quá hạn. Hãy kiểm tra EasyBooks.

### Task 4 — Understand EasyBooks sync status

- 2/2 selected **“Có, thấy ngay.”**
- No respondent reported uncertainty.

The sync-status presentation appears clear in this pilot sample.

### Terminology clarity

- Average rating: **4.33/5**
- Rating 4: 2 responses
- Rating 5: 1 response

Terminology is generally clear, but the payment-status wording requires revision despite the high overall rating.

### Facilitator observation

The written observation was:

> “cũng phải mất thời gian để làm quen”

Users can understand the interface, but onboarding and first-use guidance are still valuable.

## 6. Comparison with current workflow

Written responses included:

- Zalo is convenient, while paper documents are perceived as safer to retain.
- A centralized system is better for synchronized information, but less flexible.
- One response only said “data,” which is not specific enough to interpret.

The main product trade-off identified is:

| UniOps advantage | Current-workflow advantage |
|---|---|
| Centralized and synchronized data | Zalo feels fast and convenient |
| Easier search and automation | Paper feels safer for retention |
| Less manual work and fewer scattered sources | Existing tools are flexible and familiar |

## 7. Recommended changes from respondents

Written recommendations included:

- Make work more consistent and professional.
- Improve data synchronization.
- Add automation.
- Make the system easy to use and search.
- Reduce manual entry, paper, and Zalo communication.

## 8. Finance and bookkeeper validation

### Finance authority

Two respondents answered this section:

- 1 selected **“Có – tôi xác nhận một phần.”**
- 1 selected **“Chỉ người có vai trò lưu trữ và quản lý sổ sách / quản lý xác nhận.”**

This supports keeping accounting-policy approval with the bookkeeper or authorized record owner.

### Sales amount and VAT

Two responses were recorded:

- 1 selected **“Tổng gồm VAT.”**
- 1 selected **“Khác / ghi rõ”** and wrote **“VAT including.”**

This suggests interest in VAT-inclusive reporting, but it is not a formal accounting decision. The bookkeeper should confirm whether UniOps should display:

- amount before VAT;
- amount including VAT; or
- both, with clear labels.

### Official customer-debt source

Two responses were recorded:

- 1 selected the customer receivables report in EasyBooks.
- 1 selected **“Chưa chắc / cần xác nhận.”**

EasyBooks should remain the source of truth until the authorized finance owner confirms otherwise.

### Topics requiring finance confirmation

Both respondents selected every listed accounting topic, including **“Không cần xác nhận thêm.”** This makes the result contradictory and unusable as a decision record.

Topics listed were:

- Sales
- Purchases
- Receivables
- Payables
- Payment status, including paid, unpaid, partially paid, and overdue
- VAT
- No further confirmation needed

### Written accounting rules

The two written answers were:

- “người quản lý cao nhất” — the highest manager.
- “VAT including.”

These answers do not yet define the required source reports, VAT treatment, payment-status rules, overdue logic, or approval authority in enough detail.

## 9. Data-quality observations

The form is producing useful directional feedback, but the following issues should be corrected before treating the results as formal validation:

1. **Make “Không cần xác nhận thêm” mutually exclusive.** Use a separate single-choice question or branching logic instead of placing it in the same checkbox list as accounting topics.
2. **Separate “What do you prefer?” from “What is officially approved?”** User preference should not be treated as accounting policy.
3. **Add an explicit “I am not authorized to answer this” option** to finance questions.
4. **Ask for the exact source report and approval owner** when the respondent claims finance authority.
5. **Clarify “VAT including.”** Ask whether this means displaying totals including VAT, storing VAT-inclusive values, or only showing them as a secondary reference.
6. **Add a production/factory respondent** before drawing conclusions about shop-floor usability.

## 10. Recommended next actions

### Product/UI

- Replace **“Chưa có thông tin”** with **“Chưa có dữ liệu xác nhận thanh toán.”**
- Add a clear instruction to check EasyBooks for payment confirmation.
- Add onboarding or a short first-use walkthrough.
- Review the unclear fields on the new-order screen.
- Preserve visible sync-success and sync-error indicators.

### Finance/governance

- Have the authorized bookkeeper define the official source for receivables and payables.
- Confirm whether Sales uses pre-VAT, VAT-inclusive, or both values.
- Define paid, unpaid, partially paid, and overdue rules.
- Record who is allowed to approve each finance definition.
- Keep EasyBooks as the accounting system of record until those definitions are approved.

### Research

- Run the revised form with at least one factory/production user.
- Repeat the payment-status task after changing the wording.
- Conduct a short facilitated session where users explain what they think each status means.
- Treat this first 3-response sample as an early pilot signal, not final acceptance evidence.
