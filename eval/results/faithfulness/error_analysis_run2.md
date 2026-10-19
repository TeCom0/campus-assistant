# Error analysis, run 2: 21 failures

Confirm each cause in error_causes_run2.json ("confirmed": one of grad_undergrad, heading_split, french_retrieval, citation_placement, crash, fallback, embellishment, uncitable_tool, judge_artifact).

---

## 1. transfer_credits_en#3 (claim)

**Proposed cause:** citation_placement -- The 30-credit minimum is in [4], but the FAS exemption for 'more than 60 credits' is only in retrieved passage [3] (p. 31), which the sentence doesn't cite; it cites [4][6].

**Question:** How many credits can I transfer to AUI from another university?

**Searches:** [(None, {'query': 'credit transfer limit from other university Al Akhawayn University credit transfer limit'}), (None, {'query': 'maximum transferable credits Al Akhawayn University transfer limit 60 credits'})]

**Claim** (own, cites [4], [6]):

> (For reference, applicants must have at least 30 semester credits to be considered for admission, and if they have more than 60 credits of successful post‑secondary study they may be exempted from the Foundation Academic Studies (FAS) courses[4][6].)

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Transferring students who have successfully earned more than 60 credits in other institutions using the American system of higher education may be exempted from FAS courses... earned the minimum equivalent of 30 semester credits at the time of matriculation to the University.

**Judge's reason:** The claim is supported by the passages: 30 credits for admission ([4]) and exemption from FAS courses for more than 60 credits ([6]).

**Passages:**

[4] source: academic_catalog_2024_2025, pages: [29, 30]

```text
earned the minimum equivalent of 30 semester credits at the time of matriculation to the University. To
be considered for admission, transfer candidates must have a minimum grade point average of 2.5 on a
4.00 grading scale and be in good standing with their home institution.
Al Akhawayn University
www.aui.ma
2024-
2025
30
Applicants with fewer than 30 semester credits are considered first-year applicants for the purpose of
admission. They must provide secondary school records, applicable test scores, as well as all post-
secondary school records. A 2.5 grade point average is required. They should follow the procedure
outlined for first-time freshmen.
Admission Criteria for Transfer Students
• Evaluation of university transcripts
• Successful interview, where applicable
Required Documents for Transfer Students
• Application fee of 800 MAD
• A completed transfer online application
• Official transcripts of all university-level course work completed and/or attempted
• Syllabi of all transferable courses
```


[6] source: academic_catalog_2024_2025, pages: [31, 32]

```text
Transfer Credit Maximums
For undergraduate programs, a maximum of 68 semester credits are transferable to AUI.
Applicants for the programs in the School of Science and Engineering who have attended «classes
préparatoires» may request credit for courses as transfer students. Each application will be considered
individually. Appropriate initial courses at AUI may be based on placement examinations, portfolio
analyses, interviews, and/or other assessments.
Visiting (Non-Degree Seeking) Students
Students in good standing at another college or university may study at AUI with visiting, non-degree
seeking status during the summer or semester. Visiting applicants wishing to convert to regular, degree-
seeking status after one or more semesters at AUI will be required to complete all the General Education
Al Akhawayn University
www.aui.ma
2024-
2025
32
requirements pertaining to their academic programs. Former AUI students do not automatically qualify
for visiting or non-degree status.
```


---

## 2. plagiarism_en#6 (claim)

**Proposed cause:** citation_placement -- 'Several courses at AUI teach ... crediting sources' is in [2], but the faculty part is only in retrieved passage [5] (pp. 107-108: 'Faculty members are expected to make their practices clear'); the closing line cites [2] alone. 'model and enforce' is also a loose gloss of 'make their practices clear'.

**Question:** What is considered plagiarism at AUI?

**Searches:** [(None, {'query': 'plagiarism policy AUI'})]

**Claim** (source_line, cites [2]):

> The policy also notes that the university teaches students the formalities of properly crediting sources in several courses, and that faculty are expected to model and enforce these standards.

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Several courses at AUI teach undergraduate students the formalities of properly crediting sources... Faculty members are expected to make their practices clear to their students, and unit heads to their staff.

**Judge's reason:** The passage states that the university teaches crediting formalities in courses and expects faculty to enforce these standards.

**Passages:**

[2] source: academic_catalog_2024_2025, pages: [107]

```text
• Collaboration with other students in cheating,
• Alteration of grade records, and
• Illegal entry into or unauthorized presence in an office.
Plagiarism
Any attempt by students to present another person’s words, content, or ideas as their own is
regarded by the faculty and administration as a most serious offense. Offenders are subject to
serious consequences, including possible expulsion.
Writers, artists, and all others involved in creative endeavors must always make a clear distinction
between what words, images, ideas, and arguments are original to them; and what words,
images, ideas, and arguments are borrowed (taken) from the work of others. Failure to disclose
this distinction to readers/viewers of one’s creative work, via citations, footnotes, and proper
attributions (no matter how small or large, how formal or informal the work) constitutes plagiarism.
Several courses at AUI teach undergraduate students the formalities of properly crediting sources
```


---

## 3. add_drop_en#10 (claim)

**Proposed cause:** judge_artifact -- Verbatim in [1] ('not official until all applicable tuition and fees have been paid'); the quote failed only on the PDF's 'and/ or' spacing (same as run 1's add_drop_en#1/#6).

**Question:** How do I add or drop a course at AUI?

**Searches:** [(None, {'query': 'add or drop a course policy AUI'})]

**Claim** (own, cites [1]):

> The add/drop is not official until all applicable tuition and fees have been paid [1].

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** The adding and/or dropping of courses is not official until all applicable tuition and fees have been paid to the University.

**Judge's reason:** The claim is directly stated in passage [1].

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [103]

```text
Students in good academic standing with no holds on their account should proceed to add/drop
online. However, students with academic or other holds must go to the registrar’s office and
complete an Add/Drop Form before they can begin the process. All students must have permission
from their advisors and school coordinators to drop or add a course unless the course(s) being
added was/were included in the registration form under “alternate courses. ” The adding and/
or dropping of courses is not official until all applicable tuition and fees have been paid to the
University.
Neither faculty, nor friends or relatives may drop or add courses for a student. Courses dropped
within the official add/drop period (4th class day in regular term and 2nd class day in summer) are
not reflected on the academic record. Failure to attend a class without dropping will result in a
failing grade of WF on the academic record.
```


---

## 4. add_drop_en#14 (claim)

**Proposed cause:** citation_placement -- 'Courses dropped within the official add/drop period ... are not reflected on the academic record' is in [1]; list item 4 cites [4], whose text stops before that sentence.

**Question:** How do I add or drop a course at AUI?

**Searches:** [(None, {'query': 'add or drop a course policy AUI'})]

**Claim** (own, cites [4]):

> Courses dropped within this period are not reflected on the academic record [4].

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Courses dropped within the official add/drop period... are not reflected on the academic record.

**Judge's reason:** The claim is directly stated in passage [4].

**Passages:**

[4] source: academic_catalog_2024_2025, pages: [103]

```text
from the first day of classes.
Administrative Withdrawal
When a student has exceeded the maximum number of absences according to the mentioned
ceiling (except as stated in the External Events and Field Trips sections), the instructor has the
right to drop a student from a course with a “WF” grade.
Once WF is assigned for excessive absences, a student will not be allowed to drop the course with
W during the period indicated in the academic calendar.
Special hardship cases as stated in 1.3 and 1.4 may be referred to the Dean of Student Affairs
or to the Dean/Directors for consideration. The Administrative Withdrawal Form must reach the
Registrar’s Office at least five days before the start of final exams.
Adding/Dropping Courses
Dropping courses should not be confused with withdrawing from all courses. Students may add
and/or drop courses during the course add/drop period specified in the academic calendar.
Students in good academic standing with no holds on their account should proceed to add/drop
```


---

## 5. add_drop_en#16 (claim)

**Proposed cause:** citation_placement -- 'not official until all applicable tuition and fees have been paid' is in [1]. Item 5 has no marker of its own; the lead_in rule gave it [4] (item 4's marker), which doesn't have it. The model cited nothing here.

**Question:** How do I add or drop a course at AUI?

**Searches:** [(None, {'query': 'add or drop a course policy AUI'})]

**Claim** (lead_in, cites [4]):

> Ensure that any required tuition/fees are paid.

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** The adding and/or dropping of courses is not official until all applicable tuition and fees have been paid to the University.

**Judge's reason:** The claim is implied by the requirement that tuition and fees must be paid for the process to be official.

**Passages:**

[4] source: academic_catalog_2024_2025, pages: [103]

```text
from the first day of classes.
Administrative Withdrawal
When a student has exceeded the maximum number of absences according to the mentioned
ceiling (except as stated in the External Events and Field Trips sections), the instructor has the
right to drop a student from a course with a “WF” grade.
Once WF is assigned for excessive absences, a student will not be allowed to drop the course with
W during the period indicated in the academic calendar.
Special hardship cases as stated in 1.3 and 1.4 may be referred to the Dean of Student Affairs
or to the Dean/Directors for consideration. The Administrative Withdrawal Form must reach the
Registrar’s Office at least five days before the start of final exams.
Adding/Dropping Courses
Dropping courses should not be confused with withdrawing from all courses. Students may add
and/or drop courses during the course add/drop period specified in the academic calendar.
Students in good academic standing with no holds on their account should proceed to add/drop
```


---

## 6. add_drop_en#17 (claim)

**Proposed cause:** embellishment -- 'Verify that the changes appear on your academic record; if not, contact the Registrar's Office' is a procedural step no passage gives (scope [4] via the lead_in rule).

**Question:** How do I add or drop a course at AUI?

**Searches:** [(None, {'query': 'add or drop a course policy AUI'})]

**Claim** (lead_in, cites [4]):

> Verify that the changes appear on your academic record; if not, contact the Registrar’s Office.

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** The passage does not state that students must verify changes on their academic record or contact the Registrar’s Office if changes do not appear.

**Passages:**

[4] source: academic_catalog_2024_2025, pages: [103]

```text
from the first day of classes.
Administrative Withdrawal
When a student has exceeded the maximum number of absences according to the mentioned
ceiling (except as stated in the External Events and Field Trips sections), the instructor has the
right to drop a student from a course with a “WF” grade.
Once WF is assigned for excessive absences, a student will not be allowed to drop the course with
W during the period indicated in the academic calendar.
Special hardship cases as stated in 1.3 and 1.4 may be referred to the Dean of Student Affairs
or to the Dean/Directors for consideration. The Administrative Withdrawal Form must reach the
Registrar’s Office at least five days before the start of final exams.
Adding/Dropping Courses
Dropping courses should not be confused with withdrawing from all courses. Students may add
and/or drop courses during the course add/drop period specified in the academic calendar.
Students in good academic standing with no holds on their account should proceed to add/drop
```


---

## 7. add_drop_fr (crash)

**Proposed cause:** crash -- Forced-final-answer 400: 'Tool choice is none, but model called a tool' (before Fix A).

**Question:** Comment ajouter ou supprimer un cours à l'AUI ?

**Searches:** []

**Error:** BadRequestError('Error code: 400 - {\'error\': {\'message\': \'Tool choice is none, but model called a tool\', \'type\': \'invalid_request_error\', \'code\': \'tool_use_failed\', \'failed_generation\': \'{"name": "search_documents", "arguments": {"query":"ajouter cours AUI annuler cours ajouter supp

---

## 8. course_load_en (crash)

**Proposed cause:** crash -- Forced-final-answer 400, same error (also crashed in run 1).

**Question:** How many courses can I take in a regular semester, and when am I allowed a sixth course?

**Searches:** []

**Error:** BadRequestError('Error code: 400 - {\'error\': {\'message\': \'Tool choice is none, but model called a tool\', \'type\': \'invalid_request_error\', \'code\': \'tool_use_failed\', \'failed_generation\': \'{"name": "search_documents", "arguments": {"query":"maximum number of courses per semester AUI u

---

## 9. course_load_fr (crash)

**Proposed cause:** crash -- Forced-final-answer 400, same error.

**Question:** Combien de cours puis-je suivre pendant un semestre normal, et quand ai-je droit à un sixième cours ?

**Searches:** []

**Error:** BadRequestError('Error code: 400 - {\'error\': {\'message\': \'Tool choice is none, but model called a tool\', \'type\': \'invalid_request_error\', \'code\': \'tool_use_failed\', \'failed_generation\': \'{"name": "search_documents", "arguments": {"query":"sixth course AUI semester limit","topn":5,"s

---

## 10. w_grade_en#3 (claim)

**Proposed cause:** judge_artifact -- BORDERLINE. [2] says after the W period (40th class day) 'Faculty must assign either a grade of WP ... or WF' -- the claim's substance. The judge quoted [1] (withdrawing from ALL classes after mid-semester), not cited, so the quote failed. 'mid-semester cutoff' paraphrases '40th class day' (the calendar's W deadline, Oct 29, is mid-semester). Alternative: embellishment, if 'mid-semester' counts as a detail [2] doesn't give.

**Question:** What does a W grade mean, and until when can I drop a course and still get a W?

**Searches:** [(None, {'query': 'W grade meaning withdrawal policy drop deadline W grade Al Akhawayn University'}), (None, {'query': 'W grade meaning "W" grade meaning "withdrawal" Al Akhawayn University"'}), (None, {'query': '"last date to drop/add" "W" Al Akhawayn University"'})]

**Claim** (own, cites [2]):

> If you withdraw after the mid‑semester cutoff, the instructor can assign a **WP** (withdrawal‑pass) or **WF** (withdrawal‑fail) instead of a plain W [2].

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Students wishing to withdraw after mid-semester may do so with the permission of their dean and will receive the grade of WP (if passing at the time of withdrawal) or WF, if failing in their respective courses.

**Judge's reason:** The passage explicitly states that WP or WF is assigned after mid-semester.

**Passages:**

[2] source: academic_catalog_2024_2025, pages: [103, 104]

```text
not reflected on the academic record. Failure to attend a class without dropping will result in a
failing grade of WF on the academic record.
Although no refund will be given up to the 40th class day of the regular semester and up to 18 class
days of the summer session (refer to academic calendar for published dates), students may drop
one or more courses and receive a grade of W. This becomes part of the student’s academic record.
After that period, instructors have the responsibility of determining the grade based on classroom
performance up to the time of the student’s request to withdraw from the course. Faculty must
assign either a grade of WP (at the time of withdrawing), or WF (if failing). This process is complete
only when the form bearing all required signatures is returned to the Registrar’s Office.
Al Akhawayn University
www.aui.ma
2024-
2025
104
Students may withdraw from all classes after the last date to drop/add courses with permission
```


---

## 11. w_grade_en#4 (claim)

**Proposed cause:** misread -- PROPOSED NEW CAUSE: the cited passage contradicts the claim. [8] says Oct 29 is the 'Last Day to Drop a Course with W'; the claim says the W lasts 'until the last day of the add/drop period' (4th class day per [1]) -- then gives Oct 29 as that date. Not an added detail (embellishment): a wrong reading of a retrieved, cited passage.

**Question:** What does a W grade mean, and until when can I drop a course and still get a W?

**Searches:** [(None, {'query': 'W grade meaning withdrawal policy drop deadline W grade Al Akhawayn University'}), (None, {'query': 'W grade meaning "W" grade meaning "withdrawal" Al Akhawayn University"'}), (None, {'query': '"last date to drop/add" "W" Al Akhawayn University"'})]

**Claim** (block, cites [8]):

> You can drop a course and still receive a W **until the last day of the add‑/drop period**.

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** The passage states the last day to drop a course with a W is October 29, which is *after* the add/drop period (ends September 5). The claim incorrectly equates the last day to drop with the add/drop period.

**Passages:**

[8] source: academic_catalog_2024_2025, pages: [12, 13]

```text
October 25    Last Day for faculty to return the Mid-Semester evaluations
October 29    Last Day to Drop a Course with “W” . Beyond this date
“WP” or  “WF”
November 4-15                    Mandatory Pre-Registration for Spring 2025
(November 6: Green March)
November 6                Holiday: Green March
November 14    Last Day to Drop a Course with “WP” or “WF”
November 18-19     Holiday: Independence Day & long weekend
December 2    Last Day for graduate students to register
for project/thesis defense
December 6     Last Day to Withdraw from the University
December 13                 Last Regular Class Day
FALL
SEMESTER 2024
Al Akhawayn University
www.aui.ma
2024-
2025
13
December 14                    Review Day
December 15-23                     Final Exams (including Common Exams)
December 27                   Final Day for Faculty to Submit Semester Grades
SPRING SEMESTER 2025
January 2-12                          Winter Intersession Program (January 11 -Holiday: Independence
Manifesto Day)
```


---

## 12. scholarship_conditions_fr (false_refusal)

**Proposed cause:** french_retrieval -- 3 French searches ('conditions conserver bourse Al Akhawayn') returned course lists, loans and MBA pages, none of the renewal-policy chunks; it declined. Same as run 1.

**Question:** Quelles sont les conditions pour conserver une bourse Al Akhawayn ?

**Searches:** [(None, {'query': 'conditions conserver bourse Al Akhawayn'}), (None, {'query': 'conditions conserver bourse Al Akhawayn conditions de maintien de bourse'}), (None, {'query': 'bourse Al Akhawayn conditions de maintien bourse"'})]

**Answer:**

```text
Je suis désolé, mais je ne dispose d’aucune information concernant les conditions de conservation d’une bourse à l’Université Al Akhawayn dans les documents que vous avez fournis.
```

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [142, 143]

```text
1303, ART 1304, ART 1305,
ART 3399, COM 2327, ENG
2320, HUM 2301, LIT 3370
3
Mathematics MTH 1305 3
Physical Sciences BIO 1400, BIO 1401, CHE
1400, PHY 1400
4
Social Sciences GEO 1301, PSY 1301, SOC 1301, 2
Civic Engagement XXX ****SL or SLP 1101 or CIP 1
Al Akhawayn University
www.aui.ma
2024-
2025
143
BBA Core Courses (50 SCH)
Concentration in Finance
The Finance concentration is designed to enhance the understanding of finance and the
principles for the management of national and international financial markets and businesses.
The concentration also emphasizes financial analysis and assessment and a good understanding
of the impact of finance on decision-making. Students must select five courses from the following:
Course Code Course Name
ACC 2301 Accounting Principles I
ACC 2302 Accounting Principles II
ACC 3201 Moroccan Accounting and Taxation
ECO 2301 Microeconomics
ECO 2302 Macroeconomics
FIN 3301 Principles of Finance
GBU 2301 Business Statistics
GBU 3302 Business Law and Ethics
```


[2] source: academic_catalog_2024_2025, pages: [53, 54]

```text
period only. However, if the student falls in the 3rd year without being able to reimburse the global amount
offered by the end of the 2nd year, the interest rate of (%5.20 to be confirmed by the bank) is applicable
during the repayment period.
- Loan Conditions
Students’ loans are released to the order of Al Akhawayn University only after all the guarantee procedures
have been completed and the student loan contracts have been duly certified by local authorities. At
the beginning of each semester, the Financial Aid Office cannot process the students› loan amounts
until they are released to the order of Al Akhawayn University, and no advances are made at the time of
registration and fee payment.
Al Akhawayn University
www.aui.ma
2024-
2025
54
In the event that the new loan borrower cannot provide all the necessary documents to complete
his/her loan contract within the period specified by the Business Office, the University may take
the following actions:
```


[3] source: academic_catalog_2024_2025, pages: [143, 144]

```text
ECO 2301 Microeconomics
ECO 2302 Macroeconomics
FIN 3301 Principles of Finance
GBU 2301 Business Statistics
GBU 3302 Business Law and Ethics
GBU 3203 Enterprises, Markets, and the Moroccan Economy
GBU 3311 Quantitative Methods in Business
GBU 4101 Transitioning To The Business World
INT 4001 Internship Field Work
INT 4301 Internship
MGT 3301 Principles of Management
MGT 3302 Entrepreneurship
MGT 4301 Capstone Course: Business Policy and Corporate Strategy
MGT 4303 Operations Management
MIS 3301 Management Information Systems
MKT 3301 Principles of Marketing
Al Akhawayn University
www.aui.ma
2024-
2025
144
Course Code Course Name
FIN 3302 Money and Banking
FIN 3303 Corporate Financial Management
FIN 3305 Introduction to Islamic Banking and Finance
FIN 3306 Corporate Governance
FIN 3307 Financial Reporting and Analysis
FIN 3399 Special Topics in Finance
FIN 4304 International Finance
FIN 4305 Financial Intermediation
FIN 4306 Financial Investments and Securities Analysis
```


[4] source: academic_catalog_2024_2025, pages: [320, 321]

```text
Al Akhawayn University
www.aui.ma
2024-
2025
320
Concentration Courses, MBA (9 SCH)
Students may select three courses from the following concentrations:
Finance
Marketing
Management
Logistics and Supply Chain Management`
•   General Business
A student may choose to have a concentration in General Business. In this case, the student selects any
three graduate courses from the business discipline.
The availability of courses may vary by semester and discipline. A course is offered only if there is a
minimum number of students enrolled in it.
Concentration in Finance
Course code Course Name
ACC 5302 Managerial Accounting
ECO 5305 Managerial Economics
FIN 5305 Financial Management
GBU 5306 Business Decision Making and Management Science
MGT 5305 Organization Behavior and Leadership
MGT 5306 Strategic Management in Global Markets
MIS 5301 Managing Information Systems in Organizations
MKT 5305 Advanced Marketing Management
Al Akhawayn University
www.aui.ma
2024-
2025
321
```


[5] source: academic_catalog_2024_2025, pages: [261, 262]

```text
nation and the relationship of commercial banking with the supply and demand for money. This course
also analyses monetary concepts, central banking functions, and techniques of monetary stabilization.
FIN 3303 Corporate Financial Management (3 SCH)
Prerequisite: FIN 3301
3 lecture hours
This course continues the study of financial decision-making in corporations. The main
topics covered are advanced ratios analysis, capital budgeting, capital structure, dividend policy, and
an introduction to portfolio management. The course also provides an in-depth analysis of financial
problems with the organization, operation, merger, and dissolution of corporations.
Al Akhawayn University
www.aui.ma
2024-
2025
262
FIN 3305 Introduction to Islamic Banking and Finance (3 SCH)
Prerequisite: FIN 3301
3 lecture hours
This course discusses the basic differences between Islamic banks and conventional banks, financial
instruments of Islamic banks, profit/loss sharing, Takaful, capital markets, and unique risks faced by
```


[6] source: academic_catalog_2024_2025, pages: [380, 381]

```text
for financial soundness. At a minimum, the following topics are discussed: strategic decision making in
Al Akhawayn University
www.aui.ma
2024-
2025
381
determining investments/expenditures, capital budgeting decision criteria, refinancing techniques, and
determination of capital structure.
FIN 5370 e-Money and Payment (3 SCH)
This is an overview of general monetary and banking policies. It deals with the supply of money for a
nation and commercial banking’s relationship with the supply and demand for money. This course also
analyses monetary concepts, central banking functions, and techniques of monetary stabilization.
FIN 5399 Special Topics in Finance (3 SCH)
Prerequisite: FIN 5305, or special permission
3 lecture hours
Specially scheduled courses on significant issues or topics relevant to the study of finance.
FIN 6201 Corporate Financial Management (2 SCH)
2 lecture hours
This course is designed to equip executives with the underlying analytical framework of corporate finance.
```


---

## 13. scholarship_work_hours_en#1 (claim)

**Proposed cause:** judge_artifact -- 'Yes.' is supported by [5] and [6]. The judge's quote started with the answer's own 'Yes.' and joined [6]'s wording to [5]'s, which the one-passage rule fails.

**Question:** Do graduate scholarship students have to work for the university?

**Searches:** [(None, {'query': 'graduate scholarship students have to work for the university'}), (None, {'query': 'graduate scholarship students must perform part-time job 10 hours per week'})]

**Claim** (block, cites [5], [6]):

> Yes.

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Yes. Graduate scholarship holders are required to perform a contractual part-time job of up to 10 hours per week... starting from their second semester at AUI.

**Judge's reason:** The claim is directly supported by the passages, which explicitly state the requirement for graduate scholarship holders to perform unpaid part-time work.

**Passages:**

[5] source: academic_catalog_2024_2025, pages: [68]

```text
scholarships without any possibility to submit an appeal if ever they are allowed to return and
register again with good academic scholarship standing.
Part-time Employment for Scholarship Students
All scholarship holders must take an active part in AUI student activities, particularly in the area of com-
munity service. Undergraduate full coverage scholarship holders must provide services to AUI by holding
unpaid part-time jobs of 5 hours per week (80 hours per semester), starting their second semester at AUI,
while graduate students on scholarship have to perform a contractual part-time job of up to 10 hours per
week starting their 2nd semester at AUI. Failing to complete the total hours of work required per semester
may jeopardize the continuation of a scholarship. If a student is selected to work for an externally funded
project, s/he may receive compensation for the work, if authorized by the COO (Chief Operating Office).
```


[6] source: graduate_scholarships, pages: []

```text
Graduate scholarship students benefiting from tuition waiver or more must provide services to Al Akhawayn by holding unpaid part-time jobs as assigned by the Financial Aid Office in different departments or schools at Al Akhawayn. They are required to work 10 hours per week (160 hours per semester) as part of their scholarship package.
Graduate scholarship holders can apply for the Exchange Program for one summer only and take a minimum of six transferable credits or for a regular semester where the programs offered are very limited.
However, if the student takes fewer than the recommended full-time load, they should be aware that they run the risk of needing more than four semesters to complete their studies, in which case they will have to pay for additional courses beyond the fourth semester.
Students are allowed to use their scholarships during summer sessions conditional upon not exceeding their scholarship period of 4 sessions.
Applying for Scholarships
```


---

## 14. scholarship_work_hours_en#2 (claim)

**Proposed cause:** judge_artifact -- Supported across the two cited passages: 'up to 10 hours per week starting their 2nd semester' in [5], '(160 hours per semester)' in [6]. The quote joined both, failing the one-passage rule.

**Question:** Do graduate scholarship students have to work for the university?

**Searches:** [(None, {'query': 'graduate scholarship students have to work for the university'}), (None, {'query': 'graduate scholarship students must perform part-time job 10 hours per week'})]

**Claim** (block, cites [5], [6]):

> Graduate scholarship holders are required to perform a contractual part‑time job of up to 10 hours per week (about 160 hours per semester) starting from their second semester at AUI.

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** graduate students on scholarship have to perform a contractual part-time job of up to 10 hours per week starting their 2nd semester at AUI... (160 hours per semester)

**Judge's reason:** The claim is directly supported by the passages, which specify the hours and starting semester for the work requirement.

**Passages:**

[5] source: academic_catalog_2024_2025, pages: [68]

```text
scholarships without any possibility to submit an appeal if ever they are allowed to return and
register again with good academic scholarship standing.
Part-time Employment for Scholarship Students
All scholarship holders must take an active part in AUI student activities, particularly in the area of com-
munity service. Undergraduate full coverage scholarship holders must provide services to AUI by holding
unpaid part-time jobs of 5 hours per week (80 hours per semester), starting their second semester at AUI,
while graduate students on scholarship have to perform a contractual part-time job of up to 10 hours per
week starting their 2nd semester at AUI. Failing to complete the total hours of work required per semester
may jeopardize the continuation of a scholarship. If a student is selected to work for an externally funded
project, s/he may receive compensation for the work, if authorized by the COO (Chief Operating Office).
```


[6] source: graduate_scholarships, pages: []

```text
Graduate scholarship students benefiting from tuition waiver or more must provide services to Al Akhawayn by holding unpaid part-time jobs as assigned by the Financial Aid Office in different departments or schools at Al Akhawayn. They are required to work 10 hours per week (160 hours per semester) as part of their scholarship package.
Graduate scholarship holders can apply for the Exchange Program for one summer only and take a minimum of six transferable credits or for a regular semester where the programs offered are very limited.
However, if the student takes fewer than the recommended full-time load, they should be aware that they run the risk of needing more than four semesters to complete their studies, in which case they will have to pay for additional courses beyond the fourth semester.
Students are allowed to use their scholarships during summer sessions conditional upon not exceeding their scholarship period of 4 sessions.
Applying for Scholarships
```


---

## 15. scholarship_work_hours_en#3 (claim)

**Proposed cause:** judge_artifact -- 'unpaid ... as part of their scholarship package' is in [6]; 'must be completed each semester' matches [5] ('Failing to complete the total hours of work required per semester may jeopardize...'). Cross-passage quote.

**Question:** Do graduate scholarship students have to work for the university?

**Searches:** [(None, {'query': 'graduate scholarship students have to work for the university'}), (None, {'query': 'graduate scholarship students must perform part-time job 10 hours per week'})]

**Claim** (block, cites [5], [6]):

> This unpaid work is a condition of the scholarship package and must be completed each semester.

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** They are required to work 10 hours per week (160 hours per semester) as part of their scholarship package... Failing to complete the total hours of work required per semester may jeopardize the continuation of a scholarship.

**Judge's reason:** The passages explicitly state that the unpaid work is a condition of the scholarship package and must be completed each semester.

**Passages:**

[5] source: academic_catalog_2024_2025, pages: [68]

```text
scholarships without any possibility to submit an appeal if ever they are allowed to return and
register again with good academic scholarship standing.
Part-time Employment for Scholarship Students
All scholarship holders must take an active part in AUI student activities, particularly in the area of com-
munity service. Undergraduate full coverage scholarship holders must provide services to AUI by holding
unpaid part-time jobs of 5 hours per week (80 hours per semester), starting their second semester at AUI,
while graduate students on scholarship have to perform a contractual part-time job of up to 10 hours per
week starting their 2nd semester at AUI. Failing to complete the total hours of work required per semester
may jeopardize the continuation of a scholarship. If a student is selected to work for an externally funded
project, s/he may receive compensation for the work, if authorized by the COO (Chief Operating Office).
```


[6] source: graduate_scholarships, pages: []

```text
Graduate scholarship students benefiting from tuition waiver or more must provide services to Al Akhawayn by holding unpaid part-time jobs as assigned by the Financial Aid Office in different departments or schools at Al Akhawayn. They are required to work 10 hours per week (160 hours per semester) as part of their scholarship package.
Graduate scholarship holders can apply for the Exchange Program for one summer only and take a minimum of six transferable credits or for a regular semester where the programs offered are very limited.
However, if the student takes fewer than the recommended full-time load, they should be aware that they run the risk of needing more than four semesters to complete their studies, in which case they will have to pay for additional courses beyond the fourth semester.
Students are allowed to use their scholarships during summer sessions conditional upon not exceeding their scholarship period of 4 sessions.
Applying for Scholarships
```


---

## 16. scholarship_work_hours_en#4 (claim)

**Proposed cause:** judge_artifact -- A statement that [5] and [6] state the requirement -- true for both. Cross-passage quote.

**Question:** Do graduate scholarship students have to work for the university?

**Searches:** [(None, {'query': 'graduate scholarship students have to work for the university'}), (None, {'query': 'graduate scholarship students must perform part-time job 10 hours per week'})]

**Claim** (own, cites [5], [6]):

> The requirement is stated in the scholarship policy documents for graduate students [5] [6].

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** graduate students on scholarship have to perform a contractual part-time job of up to 10 hours per week starting their 2nd semester at AUI... (160 hours per semester)

**Judge's reason:** The requirement is explicitly stated in the provided passages [5] and [6].

**Passages:**

[5] source: academic_catalog_2024_2025, pages: [68]

```text
scholarships without any possibility to submit an appeal if ever they are allowed to return and
register again with good academic scholarship standing.
Part-time Employment for Scholarship Students
All scholarship holders must take an active part in AUI student activities, particularly in the area of com-
munity service. Undergraduate full coverage scholarship holders must provide services to AUI by holding
unpaid part-time jobs of 5 hours per week (80 hours per semester), starting their second semester at AUI,
while graduate students on scholarship have to perform a contractual part-time job of up to 10 hours per
week starting their 2nd semester at AUI. Failing to complete the total hours of work required per semester
may jeopardize the continuation of a scholarship. If a student is selected to work for an externally funded
project, s/he may receive compensation for the work, if authorized by the COO (Chief Operating Office).
```


[6] source: graduate_scholarships, pages: []

```text
Graduate scholarship students benefiting from tuition waiver or more must provide services to Al Akhawayn by holding unpaid part-time jobs as assigned by the Financial Aid Office in different departments or schools at Al Akhawayn. They are required to work 10 hours per week (160 hours per semester) as part of their scholarship package.
Graduate scholarship holders can apply for the Exchange Program for one summer only and take a minimum of six transferable credits or for a regular semester where the programs offered are very limited.
However, if the student takes fewer than the recommended full-time load, they should be aware that they run the risk of needing more than four semesters to complete their studies, in which case they will have to pay for additional courses beyond the fourth semester.
Students are allowed to use their scholarships during summer sessions conditional upon not exceeding their scholarship period of 4 sessions.
Applying for Scholarships
```


---

## 17. scholarship_work_hours_fr#3 (claim)

**Proposed cause:** judge_artifact -- The claim quotes [10] word for word; the judge's quote failed only on the PDF's line-break hyphenation ('com-
munity service' vs 'community service').

**Question:** Les étudiants boursiers en master doivent-ils travailler pour l'université ?

**Searches:** [(None, {'query': 'boursier master travailler université obligation'}), (None, {'query': 'boursier master travailler université obligation boursier master travail'}), (None, {'query': 'unpaid part-time job as exchange for their scholarship package if ever there is no available vacant part-time job position for them'})]

**Claim** (own, cites [10]):

> **Obligation générale** – « All scholarship holders must take an active part in AUI student activities … graduate students on scholarship have to perform a contractual part‑time job of up to 10 hours per week starting their 2nd semester at AUI. » [10]

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** All scholarship holders must take an active part in AUI student activities, particularly in the area of community service... graduate students on scholarship have to perform a contractual part-time job of up to 10 hours per week starting their 2nd semester at AUI.

**Judge's reason:** The claim is a direct quote from passage [10] and matches it exactly.

**Passages:**

[10] source: academic_catalog_2024_2025, pages: [68]

```text
scholarships without any possibility to submit an appeal if ever they are allowed to return and
register again with good academic scholarship standing.
Part-time Employment for Scholarship Students
All scholarship holders must take an active part in AUI student activities, particularly in the area of com-
munity service. Undergraduate full coverage scholarship holders must provide services to AUI by holding
unpaid part-time jobs of 5 hours per week (80 hours per semester), starting their second semester at AUI,
while graduate students on scholarship have to perform a contractual part-time job of up to 10 hours per
week starting their 2nd semester at AUI. Failing to complete the total hours of work required per semester
may jeopardize the continuation of a scholarship. If a student is selected to work for an externally funded
project, s/he may receive compensation for the work, if authorized by the COO (Chief Operating Office).
```


---

## 18. csc3326_prereqs_fr#3 (claim)

**Proposed cause:** judge_artifact -- 'Junior classification' is verbatim in [1]; the judge's quote 'and Junior classification' is 3 words, under the 4-word minimum (same as run 1's csc3326_prereqs_en#3).

**Question:** Quels sont les prérequis du cours CSC 3326 ?

**Searches:** [(None, {'code': 'CSC 3326', 'follow_prerequisites': False})]

**Claim** (own, cites [1]):

> être classé **Junior** [1].

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** and Junior classification

**Judge's reason:** The claim matches the prerequisite of Junior classification stated in passage [1].

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [239]

```text
[1] CSC 3326: Database Systems (3 SCH), department CSC (source: academic_catalog_2024_2025, page 239)
Prerequisites (as stated in catalog): CSC 2306 (or CSC 1402 or BAI 3301) and Junior classification
```


---

## 19. intl_scholarships_fr (false_refusal)

**Proposed cause:** french_retrieval -- 3 French searches ('bourses étudiants internationaux ...') returned the table of contents, fees, faculty lists and course descriptions -- none of the scholarship pages; it declined. (The regression question; run 1 answered it.)

**Question:** Quelles bourses sont disponibles pour les étudiants internationaux ?

**Searches:** [(None, {'query': 'bourses étudiants internationaux Al Akhawayn University'}), (None, {'query': 'bourses internationales Al Akhawayn University bourse internationale 2026'}), (None, {'query': 'bourses internationales Al Akhawayn University bourse internationale'})]

**Answer:**

```text
Je suis désolé, mais je ne dispose pas d’informations sur les bourses disponibles pour les étudiants internationaux dans les documents que j’ai consultés.
```

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [7, 8, 9]

```text
Center for Business Ethics 423
Center for Teaching and Learning 423
UNIVERSITY FACULTY 424
School of Business Administration 424
School of Science and Engineering 426
School of Humanities and Social Sciences 429
Language Center 434
Disclaimer
The material included in this catalog is based on information available as of Fall 2023 and is subject to change.
Students enrolling in Fall 2023 shall abide by the graduation requirements herein, and students enrolling in Spring
2024 shall abide by the same requirements or any changes or addenda that are published.
Al Akhawayn University
www.aui.ma
2024-
2025
9
Welcome to Al Akhawayn University in Ifrane (AUI)!
I am very happy you are connecting with us, whether
you are a prospective student, a parent, a partner, or
an alumnus. We are more than just an institution of
learning, we are a vibrant community dedicated to
personal growth, discovery, and global
impact.
We are a liberal arts university in Morocco committed
to marrying universal Excellence and Moroccan
```


[2] source: academic_catalog_2024_2025, pages: [42, 43]

```text
any other document.
The student is the sole party responsible vis-à-vis the University with regard to payment matters.
Payments can be made by wire transfers, cash deposit in banks, online credit card payments, or certified
bank checks. These fees are subject to change each academic year at the discretion of the Board of
Trustees.
Registration Fees: 5100 MAD
All registered students must pay registration fees regardless of status. Students who defend their theses,
capstones, or internships before the end of a semester receive a prorated reimbursement  of their
registration fees.
Registration fees cover fixed costs, such as: student health services, student activities, athletics,
swimming pool access, restaurant access, IT services.
Al Akhawayn University
www.aui.ma
2024-
2025
43
Tuition
Semester tuition is calculated based on the total credits taken, except for students enrolled in the
Language Center, who are charged a flat amount.
```


[3] source: academic_catalog_2024_2025, pages: [128, 129]

```text
earned a passing grade toward the ordinary AUI graduation requirements.
Withdrawal Policy
• Students intending to withdraw from the UHP must promptly notify the UHPC by completing the
UHP Withdrawal Form (provided by the UHP Office).
• Students who fail to enroll in any Honors Courses for two consecutive semesters without official
notification to the UHPC will be automatically withdrawn from the UHP .
Al Akhawayn University
www.aui.ma
2024-
2025
129
BACHELOR’S DEGREE PROGRAMS
• Bachelor of Business Administration (BBA)
• Bachelor of Arts in International Studies (BAIS)
• Bachelor of Science in Human Resource Development (BSHRD)
• Bachelor of Arts in Communication Studies (BACS)
• Bachelor of Science in Environmental Studies and Sustainability (BSESS)
• Bachelor of Science in Territorial Planning and Management (BSTPM)
• Bachelor of Science in Psychology (BSP)
• Bachelor of Science in Computer Science (BSCSC)
• Bachelor of Science in Big Data Analytics (BSBDA)
```


[4] source: academic_catalog_2024_2025, pages: [143, 144]

```text
ECO 2301 Microeconomics
ECO 2302 Macroeconomics
FIN 3301 Principles of Finance
GBU 2301 Business Statistics
GBU 3302 Business Law and Ethics
GBU 3203 Enterprises, Markets, and the Moroccan Economy
GBU 3311 Quantitative Methods in Business
GBU 4101 Transitioning To The Business World
INT 4001 Internship Field Work
INT 4301 Internship
MGT 3301 Principles of Management
MGT 3302 Entrepreneurship
MGT 4301 Capstone Course: Business Policy and Corporate Strategy
MGT 4303 Operations Management
MIS 3301 Management Information Systems
MKT 3301 Principles of Marketing
Al Akhawayn University
www.aui.ma
2024-
2025
144
Course Code Course Name
FIN 3302 Money and Banking
FIN 3303 Corporate Financial Management
FIN 3305 Introduction to Islamic Banking and Finance
FIN 3306 Corporate Governance
FIN 3307 Financial Reporting and Analysis
FIN 3399 Special Topics in Finance
FIN 4304 International Finance
FIN 4305 Financial Intermediation
FIN 4306 Financial Investments and Securities Analysis
```


[5] source: academic_catalog_2024_2025, pages: [24, 25, 26, 27]

```text
Touhami, Yassir
Chief Financial Officer
Ben El Jarbouh, Abderrahim
Director, Business Services
Ali, El Awad
Executive Director for Support & Administration
Nouamani, Said
Director, Procurement and Infrastructure Development`
2024-
2025
25
Harroud, Hamid
Director, Information Technology Services
Jadid, Mohammed
Director, Grounds and Maintenance
Bouflous, Mohammed
Director, Security and Safety Department
Other Senior Administrators
Office for Institutional Research and Effectiveness
Belfekih, Moulay Cherif
Executive Director
Office of Internal Audit
Mechiche, Souhail
Junior Auditor, Internal Audit and Management Control
Department of Development and Communication
Dalil, Hamza
Chief Marketing Officer in charge of Development and Communication,
Outreach, and Admissions
Office of Human Capital
Hazzaz, Safia
Director of Human Capital
Al Akhawayn University
www.aui.ma
2024-
2025
26
2024-
2025
27
ADMISSIONS
Al Akhawayn University encourages all academically qualified senior high school students
```


[6] source: academic_catalog_2024_2025, pages: [424, 425]

```text
Geneva, Switzerland.
Al Akhawayn University
www.aui.ma
2024-
2025
425
El Bouchikhi, Yassine, PhD in Management Science, Paris Dauphine University – PSL Research,
France.
El Garah, Ouafaa, Ph.D. in Management Information Systems, University of Central Florida, Orlando,
Florida, USA.
Fakhar, Ahlam, Ph.D. in Economics, Claremont Graduate University, Claremont, California, USA.
Gamar, Alae, Master of Business Administration, Al Akhawayn University in Ifrane, Morocco.
Hamidi Alaoui, Abdelhamid, Ph.D. in Mathematics, University of Oklahoma, Norman, Oklahoma, USA.
Hammoud, Rhizlane, Master of Business Administration, Michigan State University, East Lansing,
Michigan, USA.
Hassi, Abderrahman, Doctorate in Relations Industrielles, Laval University, Quebec, Canada.
Ikram, Muhammed , Ph.D. in Management, Nanjing University of Aeronautics and Astronautics,
Nanjing, China.
Jabbouri, Imad, Ph.D. in Finance, ESC Rennes School of Business, Rennes, France.
Konou, Comlanvi Martin, Ph.D. in Economics,
```


[7] source: academic_catalog_2024_2025, pages: [19, 20]

```text
fields of knowledge, as well as a forum for cooperation and understanding between
people and civilizations. With its expertise and the outcomes of its research activities,
Al Akhawayn University assumes a pioneering and exploratory role in the fields that
most preoccupy humanity and industrial ventures. Thus, the university organizes
ongoing training courses, specialized study sessions, symposia, and conferences.
2024-
2025
20
BOARD OF TRUSTEES
Representatives of the Royal Cabinet and the Private Secretariat of His Majesty the King
M. André Azoulay
Advisor to His Majesty the King
M. Mohamed Mounir El Majidi
Director of the Private Secretariat of His Majesty the King
M. Abdelouafi LAFTIT
Minister of Interior
M. Nasser BOURITA
Minister of Foreign Affairs, African Cooperation and Moroccan Expatriates
Ms. Nadia FETTAH
Minister of Economy and Finance
M. Mohamed Saad BERRADA
Minister of National Education, Preschool, and Sports
M. Azzedine EL MIDAOUI
```


[8] source: academic_catalog_2024_2025, pages: [16, 17]

```text
among peoples and civilizations.
Since its inception, the University has manifested its wish to contribute to the training of highly qualified
professionals and executives, people committed to the quest for knowledge and culture and imbued with
the values of human solidarity and tolerance.
In addition to a global focus, the University desires that the education imparted grant a special status to
the Arabic language and the Arab-Islamic culture at all educational levels and majors. While adopting
the English language as the main medium of instruction, we also offer a range of courses in Arabic and
French.
Within the framework of the Dahir-bearing law, Al Akhawayn University works to establish cooperative
relations with universities and other national and international organizations concerned with education
and research. It strives also to enter cooperative relations with public and private entities from various
sectors of the national economy.
Al Akhawayn University
www.aui.ma
2024-
2025
17
```


[9] source: academic_catalog_2024_2025, pages: [261, 262]

```text
nation and the relationship of commercial banking with the supply and demand for money. This course
also analyses monetary concepts, central banking functions, and techniques of monetary stabilization.
FIN 3303 Corporate Financial Management (3 SCH)
Prerequisite: FIN 3301
3 lecture hours
This course continues the study of financial decision-making in corporations. The main
topics covered are advanced ratios analysis, capital budgeting, capital structure, dividend policy, and
an introduction to portfolio management. The course also provides an in-depth analysis of financial
problems with the organization, operation, merger, and dissolution of corporations.
Al Akhawayn University
www.aui.ma
2024-
2025
262
FIN 3305 Introduction to Islamic Banking and Finance (3 SCH)
Prerequisite: FIN 3301
3 lecture hours
This course discusses the basic differences between Islamic banks and conventional banks, financial
instruments of Islamic banks, profit/loss sharing, Takaful, capital markets, and unique risks faced by
```


[10] source: academic_catalog_2024_2025, pages: [246, 247]

```text
also highlights the importance of trade in the development of economies and examines different issues
in international capital flows.
ECO 3302 Economic Growth and Development (3 SCH)
Prerequisites: ECO 2302, ECO 2310 for International Studies Major
3 lecture hours
This course introduces theories of growth and planning and supports formulating policies to foster and
regulate growth. Emphasis is on the application of analytical concepts to improve economic welfare
patterns, considering problems of capital formation and human and material resource use. Social
indicators to differentiate between growth and development (e.g., education, health, women’s status)
are also addressed.
Al Akhawayn University
www.aui.ma
2024-
2025
247
ECO 3303 Monetary Economics (3 SCH)
Prerequisite: ECO 2302
3 lecture hours
This course offers a study of Moroccan and international financial systems, institutions, investments,
and instruments, including alternative monetary systems, exchange rate determination, and the balance
```


---

## 20. mth1305_fr (false_refusal)

**Proposed cause:** uncitable_tool -- Only query_courses was called; it returned the 'no description' note (no marker); the model declined citing a [1] no tool returned, never searching. Same as run 1.

**Question:** Qu'est-ce que le cours MTH 1305 ?

**Searches:** [(None, {'code': 'MTH 1305', 'follow_prerequisites': False})]

**Answer:**

```text
Je ne trouve pas de description détaillée du cours **MTH 1305** dans le catalogue officiel ; il est mentionné mais aucun intitulé ou détail de contenu n’est fourni. Il vaut mieux consulter un conseiller académique ou le service des cours pour obtenir les informations précises sur ce cours. [1]
```

**Passages:**

---

## 21. fulbright_fr (crash)

**Proposed cause:** crash -- Forced-final-answer 400, same error (unanswerable question).

**Question:** Comment postuler à la bourse Fulbright via l'AUI ?

**Searches:** []

**Error:** BadRequestError('Error code: 400 - {\'error\': {\'message\': \'Tool choice is none, but model called a tool\', \'type\': \'invalid_request_error\', \'code\': \'tool_use_failed\', \'failed_generation\': \'{"name": "search_documents", "arguments": {"query":"bourse Fulbright Al Akhawayn University","ma
