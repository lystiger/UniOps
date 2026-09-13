# UniOps Pilot Survey V2 — Design Document

> **This is a survey *design* document.** It specifies the questions, their types, their options, and their branching. It does not create or edit the Google Form. Building the form from this specification is a separate, explicit step.

**Supersedes:** the Round 1 form, [Khảo sát trải nghiệm pilot UniOps — UniGreen](https://docs.google.com/forms/d/1feLr6cBsfpxwbgXq41iMcsqcTv0QvLfiCDCyiraLr30/edit).
**Round 1 results:** [uniops-pilot-response-summary.md](../uniops-pilot-response-summary.md) — 3 respondents (1 management, 1 office, 1 finance, **0 factory**).

---

## 1. Why V2 exists

Round 1 produced answers that cannot be used to approve accounting semantics. Three defects in the instrument, not in the respondents:

| # | Defect in Round 1 | Consequence | Fixed by |
|---|---|---|---|
| D1 | The finance question was a **checkbox** group that contained both specific accounting topics *and* the option **"Không cần xác nhận thêm"**. | Respondents selected both at once. The answers are self-contradictory and cannot be read either way. | §3 — the "no further confirmation needed" option is moved into its own single-choice gate question, and the topic list only appears after it. |
| D2 | Finance-policy questions had no way to say **"I am not the person who decides this."** | A respondent without authority still had to pick an answer, so preference was recorded as if it were policy. | §4 — every policy question carries *"Tôi không có thẩm quyền xác nhận"*, and §6 asks who the authority actually is. |
| D3 | Display preference and official accounting rule were asked as **one question**. | "What I'd like to see" is indistinguishable from "what the books require". | §5 — every such topic is split into a preference question and a separate rule question. |

Two further gaps that V2 must close:

- **G1 — no factory respondent.** Round 1 has zero data on factory usability. V2 must be run with at least one factory/production participant, and §2 records role before anything else.
- **G2 — no named source report.** Receivables answers referred to "công nợ" generically, with no EasyBooks report named. §6 requires the exact report name.

---

## 2. Section A — Respondent (all respondents)

**A1. Vai trò của bạn trong công ty là gì?** *(single choice, required)*
- Quản lý / ra quyết định
- Văn phòng / điều phối
- Xưởng / sản xuất
- Tài chính / kế toán
- Khác: ⟨short answer⟩

> **Quota rule:** the round is not complete until **A1 = "Xưởng / sản xuất"** has at least one response. This is the Round 1 gap (G1).

**A2. Bạn dùng UniOps thường xuyên đến mức nào?** *(single choice)* — Hằng ngày / Vài lần một tuần / Vài lần một tháng / Mới dùng lần đầu

---

## 3. Section B — Finance confirmation gate (fixes D1)

This section replaces the single Round 1 checkbox question. **The gate and the topic list must be separate questions.** They must not appear in the same checkbox group under any circumstance.

**B1 (GATE). Các nội dung tài chính dưới đây có cần xác nhận thêm từ người có thẩm quyền không?** *(single choice, required)*

Preceded by this text, shown on the form:

> UniOps hiện hiển thị doanh số, chi mua hàng, chênh lệch Bán − Mua, thuế GTGT và công nợ phải thu. Cách định nghĩa và cách hiển thị những con số này chưa được xác nhận chính thức.

- **Có** — *(branch to B2)*
- **Không** — *(branch to Section C; B2 is not shown)*
- **Tôi không có thẩm quyền xác nhận** — *(branch to Section C; B2 is not shown)*

**B2. Những nội dung nào cần được xác nhận?** *(checkbox, shown only when B1 = "Có")*

This list contains **only topics**. It contains no "none of the above" option — B1 already carries that answer.

- Doanh số bán hàng (cách tính, trước/sau VAT)
- Chi mua hàng
- Chênh lệch Bán − Mua
- Thuế GTGT
- Công nợ phải thu (số dư khách hàng)
- Trạng thái thanh toán của hóa đơn
- Hạn thanh toán / quá hạn
- Trạng thái "Đã xuất hóa đơn" của đơn hàng
- Khác: ⟨short answer⟩

> **Validation rule for the form builder:** B2 must be a separate question with its own branch condition. If the form tool cannot branch, B2 must still be a separate question, and its header must read *"Chỉ trả lời nếu bạn đã chọn 'Có' ở câu trên."*

---

## 4. Section C — Authority escape hatch (fixes D2)

**Every question in Sections D and E carries the option *"Tôi không có thẩm quyền xác nhận"*.** Where a question asks what the books actually require, that option is mandatory. Where a question asks only what the respondent would prefer to see, it is not offered — preference needs no authority.

**C1. Bạn có thẩm quyền xác nhận định nghĩa kế toán cho công ty không?** *(single choice, required)*
- Có, tôi là người xác nhận
- Tôi tham gia nhưng không quyết định
- Không, tôi chỉ sử dụng số liệu
- Tôi không chắc

Answers to Sections D and E from a respondent who answered anything other than *"Có, tôi là người xác nhận"* are **signals, not approvals**, and must be recorded as such.

---

## 5. Section D — Preference and rule, asked separately (fixes D3)

Each topic below is **two questions**. The first is what the respondent would like to see; the second is what the books require. They must never be merged.

### D1 — Sales and VAT

**D1a — DISPLAY PREFERENCE. Bạn muốn UniOps hiển thị doanh số theo cách nào?** *(single choice)*
- Trước VAT
- Sau VAT
- Cả hai
- Không chắc

**D1b — OFFICIAL RULE. Theo quy định/sổ sách hiện tại, cách nào là chính thức?** *(single choice)*
- Trước VAT
- Sau VAT
- Cả hai
- Tôi không có thẩm quyền xác nhận
- Chưa được xác định

### D2 — Customer balance

**D2a — DISPLAY PREFERENCE. Bạn muốn UniOps hiển thị công nợ khách hàng theo cách nào?** *(single choice)*
- Tổng số dư của khách hàng
- Theo từng hóa đơn
- Cả hai
- Không chắc

**D2b — OFFICIAL RULE. Theo sổ sách hiện tại, số dư công nợ chính thức của một khách hàng được lấy ở đâu?** *(single choice)*
- Sổ tài khoản 131
- Báo cáo công nợ phải thu trên EasyBooks
- Bảng theo dõi riêng ngoài EasyBooks (Excel hoặc giấy)
- Tôi không có thẩm quyền xác nhận
- Chưa được xác định

### D3 — Overdue

**D3a — DISPLAY PREFERENCE. Bạn muốn UniOps cảnh báo "quá hạn thanh toán" không?** *(single choice)* — Có / Không / Không chắc

**D3b — OFFICIAL RULE. Theo quy định hiện tại, "quá hạn" được tính từ mốc nào?** *(single choice)*
- Từ ngày xuất hóa đơn
- Từ ngày giao hàng
- Theo thỏa thuận riêng với từng khách hàng
- Tôi không có thẩm quyền xác nhận
- Chưa được xác định

> **Note for the form builder:** UniOps currently reports due status as unknown and computes no overdue figure, because no observed EasyBooks sales document carries a due date. D3b decides whether that can ever change; it is not a request to start computing one.

### D4 — Payment status

**D4a — DISPLAY PREFERENCE. Khi UniOps chưa có dữ liệu thanh toán, bạn muốn nó hiển thị thế nào?** *(single choice)*
- "Chưa có dữ liệu xác nhận thanh toán" (cách hiện tại)
- Để trống
- Cách khác: ⟨short answer⟩

**D4b — OFFICIAL RULE. Một hóa đơn được coi là đã thanh toán khi nào?** *(single choice)*
- Khi có phiếu thu/ủy nhiệm chi gắn đúng với hóa đơn đó
- Khi khách hàng đã chuyển đủ tiền, dù chưa gắn vào hóa đơn cụ thể
- Theo quy tắc khác: ⟨short answer⟩
- Tôi không có thẩm quyền xác nhận
- Chưa được xác định

---

## 6. Section E — Source report and approval owner (fixes G2)

**E1. Trong EasyBooks, báo cáo nào hiện được dùng làm nguồn chính thức cho công nợ phải thu?** *(short answer, required if C1 = "Có, tôi là người xác nhận")*

> Xin ghi **đúng tên báo cáo** như hiển thị trên EasyBooks (ví dụ: tên trong menu báo cáo), không ghi chung chung là "báo cáo công nợ".

**E2. Ảnh chụp màn hình hoặc đường dẫn tới báo cáo đó** *(file upload or short answer, optional)*

**E3. Ai là người xác nhận quy tắc này?** *(single choice)*
- Kế toán phụ trách
- Người quản lý sổ sách
- Giám đốc
- Khác: ⟨short answer⟩
- Tôi không biết

**E4. Công nợ phải trả (nhà cung cấp) hiện được theo dõi ở đâu?** *(short answer, optional)*

> UniOps hiện **không** có bất kỳ số liệu công nợ phải trả nào. Câu hỏi này chỉ để ghi nhận thực tế, không phải yêu cầu tính năng.

**E5. Ai là người có quyền xác nhận định nghĩa "doanh số" cho báo cáo nội bộ?** *(single choice)* — same options as E3.

---

## 7. Section F — Usability (all respondents, no finance authority needed)

Kept close to Round 1 so the two rounds can be compared, plus the items Round 1 could not answer.

**F1. Bạn có tìm được việc cần làm tiếp theo với một đơn hàng không?** — Có, dễ dàng / Có, nhưng mất thời gian / Không
**F2. Trạng thái đồng bộ EasyBooks có dễ hiểu không?** — 1–5
**F3. Các thuật ngữ trên màn hình có rõ nghĩa không?** — 1–5 *(Round 1 average: 4.33)*
**F4. Màn hình tạo đơn hàng có ô nào khó hiểu không?** — Không có ô nào khó hiểu / Có, phần lớn rõ nhưng 1–2 ô chưa rõ / Có, nhiều ô chưa rõ
**F5. Nếu bạn chọn "có" ở câu trên, đó là (những) ô nào?** *(checkbox, shown when F4 ≠ "Không có ô nào khó hiểu")* — Khách hàng / Ngày đặt hàng / Hạn giao hàng / Sản phẩm / Mô tả sản phẩm / Số lượng / Đơn vị tính / Đơn giá thỏa thuận / Ghi chú / Khác: ⟨short answer⟩

> **This is the question Round 1 was missing.** One of two respondents reported 1–2 unclear fields but there was no follow-up naming them, so the fields were never identified. F5 must be present.

**F6. Lần đầu sử dụng UniOps, bạn mất bao lâu để làm quen?** — Ngay lập tức / Vài phút / Khoảng một buổi / Vẫn đang làm quen
**F7. Dòng giới thiệu ngắn hiện ra lần đầu đăng nhập có hữu ích không?** — Có / Không / Tôi không để ý thấy

**F8. Ở phần kế toán của một đơn hàng, dòng "Thanh toán" hiện ghi *"Chưa có dữ liệu xác nhận thanh toán"*. Theo bạn, câu đó có nghĩa là gì?** *(short answer, required)*

> **Do not offer options.** This must be free text, in the respondent's own words. The correct understanding is *"UniOps chưa biết đã thanh toán hay chưa"*. An answer meaning *"khách chưa thanh toán"* is a failure of the wording and must be recorded verbatim. This question mirrors Task C of the facilitated script in [human-pilot-checklist.md](human-pilot-checklist.md).

**F9. (Chỉ dành cho xưởng/sản xuất) Bạn có tìm được đơn hàng đang sản xuất và biết việc gì cần làm tiếp theo không?** — Có, dễ dàng / Có, nhưng mất thời gian / Không

---

## 8. How to read the results

| Answer pattern | How it must be recorded |
|---|---|
| A policy answer (Sections D-b, E) from a respondent whose C1 ≠ *"Có, tôi là người xác nhận"* | **Signal only.** It does not approve anything. |
| B1 = *"Không"* with no topics selected | Finance semantics stay **unconfirmed**, not approved. An absence of requests is not an approval. |
| B1 = *"Tôi không có thẩm quyền xác nhận"* | The instrument reached the wrong person. Find the authority named in E3/E5 and ask them. |
| F8 answered as *"khách chưa thanh toán"* | The payment wording has **failed again**. Reopen it; do not proceed to V1 sign-off. |
| No response with A1 = *"Xưởng / sản xuất"* | Factory usability remains **unvalidated**. The round is incomplete regardless of every other answer. |

No combination of answers in this survey approves an accounting definition on its own. Approval is a named person confirming a named rule, recorded against the topics in [finance-validation-questions.md](finance-validation-questions.md).
