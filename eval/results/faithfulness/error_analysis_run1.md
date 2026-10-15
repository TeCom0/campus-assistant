# Error analysis, run 1: 18 failures

Confirm each cause in error_causes_run1.json ("confirmed": one of grad_undergrad, heading_split, french_retrieval, citation_placement, crash, embellishment, uncitable_tool, judge_artifact).

---

## 1. plagiarism_fr#2 (claim)

**Proposed cause:** citation_placement -- 'failure in a course' is in retrieved passage [4] (pp. 107-108) but the sentence cites [2], which only says 'possible expulsion'.

**Question:** Qu'est-ce que le plagiat selon le règlement de l'AUI ?

**Searches:** [(None, {'query': 'plagiat règlement AUI'})]

**Claim** (own, cites [2]):

> Cette pratique est considérée comme une infraction grave par le corps professoral et l’administration ; les contrevenants peuvent faire l’objet de sanctions sévères, allant de l’échec d’un cours à l’expulsion [2].

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** The passage states that offenders are subject to serious consequences, including possible expulsion, but does not explicitly mention failure of a course as a possible sanction.

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

## 2. plagiarism_en#3 (claim)

**Proposed cause:** judge_artifact -- Supported verbatim by [2] ('heavy penalties, including failure in a course, suspension from the university, or expulsion'); the claim cites [1,2], and the judge's quote joined [1] and [2], which the one-passage rule fails.

**Question:** What is considered plagiarism at AUI?

**Searches:** [(None, {'query': 'plagiarism policy AUI plagiarism considered'})]

**Claim** (block, cites [1], [2]):

> Plagiarism is treated as a serious offense that can lead to failure in a course, suspension, or expulsion.

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Offenders are subject to serious consequences, including possible expulsion... will result in heavy penalties, including failure in a course, suspension from the university, or expulsion.

**Judge's reason:** The passage states that plagiarism can lead to failure in a course, suspension, or expulsion.

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [107]

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


[2] source: academic_catalog_2024_2025, pages: [107, 108]

```text
Several courses at AUI teach undergraduate students the formalities of properly crediting sources
in their work. Some graduate programs teach these formalities as well. When members of the AUI
community—faculty, staff, administration, or student—doubt the legitimacy of someone’s work
regarding the requirements for crediting sources, they may consult reference books in the main
office of their academic or support unit. Faculty members are expected to make their practices
clear to their students, and unit heads to their staff.
In addition, it is the general policy of the University that willfully ignoring the principle of academic
honesty—once taught—and the formalities regarding citation for one’s discipline, will result in
heavy penalties, including failure in a course, suspension from the university, or expulsion.
Al Akhawayn University
www.aui.ma
2024-
2025
108
Falsifying Documents
Any attempt to forge or alter academic documents, transcripts, grade reports, letters of
```


---

## 3. add_drop_en#1 (claim)

**Proposed cause:** judge_artifact -- A 9-word lead-in ('...follow the official registration procedure:'); judge said supported. The quote failed only because the PDF text has 'and/ or' (space after the slash) where the quote has 'and/or'.

**Question:** How do I add or drop a course at AUI?

**Searches:** [(None, {'query': 'add drop course AUI policy'}), (None, {'query': 'add drop process AUI registration regulations'})]

**Claim** (source_line, cites [4], [7]):

> To add or drop a course at Al Akhawayn University you need to follow the official registration procedure:

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Students in good academic standing with no holds on their account should proceed to add/drop online... All students must have permission from their advisors and school coordinators to drop or add a course... The adding and/or dropping of courses is not official until all applicable tuition and fees have been paid to the University.

**Judge's reason:** The claim is supported by the general procedure outlined in passage [4].

**Passages:**

[4] source: academic_catalog_2024_2025, pages: [103]

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


[7] source: academic_catalog_2024_2025, pages: [97]

```text
preregistration deposit will apply (2000 MAD for Fall/Spring, 1000 MAD for Summer).
Regular Registration
Registration and late registration dates are published in this catalog and in the Academic Calendar.
Students may register for classes on the regularly scheduled registration dates through the end of
the Add/Drop period (4th class day in regular semesters and 2nd class day in summer sessions).
Students must confirm registration during the online period before classes begin. If a student fails
to confirm registration according to the schedule, a 1500 MAD late registration fee will be assessed
for late registration. Students must be officially enrolled at AUI during the semester in which they
graduate. Students enrolling late in a course should not expect special make-up assistance from
the instructor.
Late Registration
For the purpose of the fee assessment, late registration is defined as the period between the first
```


---

## 4. add_drop_en#6 (claim)

**Proposed cause:** judge_artifact -- Both facts are in [4] ('not official until all applicable tuition and fees have been paid'; 'not reflected on the academic record'). Same 'and/ or' PDF spacing broke the quote.

**Question:** How do I add or drop a course at AUI?

**Searches:** [(None, {'query': 'add drop course AUI policy'}), (None, {'query': 'add drop process AUI registration regulations'})]

**Claim** (source_line, cites [4], [7]):

> Step: **5. Pay any tuition/fees**; What to do: The change is not official until all applicable tuition and fees are paid.; Key details & dates: Courses dropped within the add/drop window are not reflected on your academic record.

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** The adding and/or dropping of courses is not official until all applicable tuition and fees have been paid to the University... Courses dropped within the official add/drop period (4th class day in regular term and 2nd class day in summer) are not reflected on the academic record.

**Judge's reason:** The claim is supported by the requirements in passage [4].

**Passages:**

[4] source: academic_catalog_2024_2025, pages: [103]

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


[7] source: academic_catalog_2024_2025, pages: [97]

```text
preregistration deposit will apply (2000 MAD for Fall/Spring, 1000 MAD for Summer).
Regular Registration
Registration and late registration dates are published in this catalog and in the Academic Calendar.
Students may register for classes on the regularly scheduled registration dates through the end of
the Add/Drop period (4th class day in regular semesters and 2nd class day in summer sessions).
Students must confirm registration during the online period before classes begin. If a student fails
to confirm registration according to the schedule, a 1500 MAD late registration fee will be assessed
for late registration. Students must be officially enrolled at AUI during the semester in which they
graduate. Students enrolling late in a course should not expect special make-up assistance from
the instructor.
Late Registration
For the purpose of the fee assessment, late registration is defined as the period between the first
```


---

## 5. add_drop_fr#3 (claim)

**Proposed cause:** french_retrieval -- 3 padded French searches; the cited [4] is the catalog's TABLE OF CONTENTS (p. 5), not the add/drop policy (p. 103), so the steps ('portail', 'Drop') are invented around TOC headings.

**Question:** Comment ajouter ou supprimer un cours à l'AUI ?

**Searches:** [(None, {'query': 'ajouter supprimer cours AUI procédure inscription cours ajouter supprimer cours AUI'}), (None, {'query': "ajouter supprimer cours AUI procédure ajouter cours supprimer cours AUI politique d'inscription cours ajouter supprimer"}), (None, {'query': 'ajouter cours AUI supprimer cours AUI "ajout" "suppression" "ajouter" "supprimer" "cours" "AUI" "politique"'})]

**Claim** (own, cites [4]):

> Action: **Supprimer un cours**; Étapes principales: 1. **Late Registration / Drop Deadline** – Vous devez retirer le cours avant la date limite indiquée dans le calendrier académique (voir « Late Registration » et « Class Day »).  2. **Utilisez le portail d’inscription** – Sélectionnez le cours dans votre emploi du temps et choisissez « Drop ».  3. **Consultez votre conseiller académique** – En cas de doute ou pour des situations particulières (par ex. si vous avez déjà reçu un crédit pour un cours équivalent), demandez l’avis de votre conseiller ou de l’OASP.; Références: [4]

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Late Registration  97...Class Day  97

**Judge's reason:** Passage [4] explicitly mentions 'Late Registration' and 'Class Day' as part of the drop deadlines and procedures, and the use of the registration portal for dropping courses.

**Passages:**

[4] source: academic_catalog_2024_2025, pages: [5]

```text
REQUIRED DOCUMENTS FOR FINANCIAL AID 50
APPLICATION DEADLINES   52
TYPES OF FINANCIAL AID OFFERED AT AUI 52
AUI Scholarships for New Students  66
AUI Scholarships for Continuing Students  74
STUDENT SUPPORT    75
Center for Learning Excellence (CLE)  75
Student Services    77
Student Life    78
Athletics     81
Student Housing    85
Student Conduct    86
Campus Store    87
Counseling    87
Health Center    88
Dining Services    88
Computer and Email Support   88
ACADEMIC RESOURCES  92
Mohammed VI Library  92
Advising for Freshmen  93
The office of Employability & Entrepreneurship  93
Office of Academic Support and Progress (OASP)  94
Office of International Programs  94
REGISTRATION REGULATIONS  97
Academic Advising  97
Preregistration  97
Regular Registration  97
Late Registration  97
Class Day  97
Semester Credit Hour  97
Prerequisites  98
Academic Calendar  98
Enrollment Certificates  98
Student Transcripts  98
Certificate of Completion  98
Name Change of Current Students  99
Death of a Current Student  99
```


---

## 6. add_drop_fr#7 (claim)

**Proposed cause:** french_retrieval -- Same answer: cites the table of contents [4] for drop deadlines; the add/drop policy chunk was never retrieved.

**Question:** Comment ajouter ou supprimer un cours à l'AUI ?

**Searches:** [(None, {'query': 'ajouter supprimer cours AUI procédure inscription cours ajouter supprimer cours AUI'}), (None, {'query': "ajouter supprimer cours AUI procédure ajouter cours supprimer cours AUI politique d'inscription cours ajouter supprimer"}), (None, {'query': 'ajouter cours AUI supprimer cours AUI "ajout" "suppression" "ajouter" "supprimer" "cours" "AUI" "politique"'})]

**Claim** (own, cites [4]):

> **Délais** : les dates de début et de fin de registration, ainsi que les dates limites de drop, sont indiquées dans le calendrier académique et dans la section « Late Registration » (voir [4]).

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Late Registration  97...Academic Calendar  98

**Judge's reason:** Passage [4] mentions 'Late Registration' and 'Academic Calendar' as sources for registration and drop deadlines.

**Passages:**

[4] source: academic_catalog_2024_2025, pages: [5]

```text
REQUIRED DOCUMENTS FOR FINANCIAL AID 50
APPLICATION DEADLINES   52
TYPES OF FINANCIAL AID OFFERED AT AUI 52
AUI Scholarships for New Students  66
AUI Scholarships for Continuing Students  74
STUDENT SUPPORT    75
Center for Learning Excellence (CLE)  75
Student Services    77
Student Life    78
Athletics     81
Student Housing    85
Student Conduct    86
Campus Store    87
Counseling    87
Health Center    88
Dining Services    88
Computer and Email Support   88
ACADEMIC RESOURCES  92
Mohammed VI Library  92
Advising for Freshmen  93
The office of Employability & Entrepreneurship  93
Office of Academic Support and Progress (OASP)  94
Office of International Programs  94
REGISTRATION REGULATIONS  97
Academic Advising  97
Preregistration  97
Regular Registration  97
Late Registration  97
Class Day  97
Semester Credit Hour  97
Prerequisites  98
Academic Calendar  98
Enrollment Certificates  98
Student Transcripts  98
Certificate of Completion  98
Name Change of Current Students  99
Death of a Current Student  99
```


---

## 7. course_load_en (crash)

**Proposed cause:** crash -- Forced-final-answer 400: 'Tool choice is none, but model called a tool'.

**Question:** How many courses can I take in a regular semester, and when am I allowed a sixth course?

**Searches:** []

**Error:** BadRequestError('Error code: 400 - {\'error\': {\'message\': \'Tool choice is none, but model called a tool\', \'type\': \'invalid_request_error\', \'code\': \'tool_use_failed\', \'failed_generation\': \'{"name": "search_documents", "arguments": {"query":"maximum number of courses per semester AUI r

---

## 8. course_load_fr#6 (claim)

**Proposed cause:** french_retrieval -- '5 cours' for a regular student is TRUE in the catalog (p. 116 Course Load Policy: 'A normal course load per semester is five courses'), but no French search retrieved that chunk; it cites [14], the scholarship six-course recommendation.

**Question:** Combien de cours puis-je suivre pendant un semestre normal, et quand ai-je droit à un sixième cours ?

**Searches:** [(None, {'query': 'nombre de cours semestre normal droit à sixième cours Al Akhawayn University politique académique'}), (None, {'query': 'sexe cours maximum semestre normal sixième cours droit à sixième cours Al Akhawayn University "sixième" "cours"'}), (None, {'query': 'nombre de cours maximum semestre normal sixième cours droit à sixième cours AUI semestre normal cours maximum'})]

**Claim** (lead_in, cites [14]):

> Situation: Étudiant régulier (sans bourse); Nombre de cours autorisés par semestre: 5 cours

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** No passage explicitly states that a regular (non-scholarship) student is limited to 5 courses per semester. This is an interpretation not directly supported by the passages.

**Passages:**

[14] source: academic_catalog_2024_2025, pages: [67]

```text
Scholarship Period
Undergraduate beneficiaries are eligible for AUI scholarship for a maximum of nine semesters (or eight
semesters plus two summer sessions), while graduate scholarships are allowed to use their scholarship
for a maximum of four semesters, including one semester at the Language Center. However,
extension for any extra semester including the summer session may be granted based on the scholarship
fund and on the beneficiary’s academic standing during the previous semesters at AUI.
Scholarships cover courses required for graduation only. It is highly recommended that the scholarship
beneficiary should take six courses per semester and enroll in at least two summer sessions. In addition,
any course dropped by the students must be validated by the Financial Aid Office.
If the student takes less than the recommended full-load, s/he should be aware that s/he runs the risk
of extending his/her time before graduation, therefore having to pay for additional or remaining courses.
```


---

## 9. academic_probation_fr (crash)

**Proposed cause:** crash -- Forced-final-answer 400, same as course_load_en.

**Question:** Que se passe-t-il si ma moyenne (GPA) est entre 1,5 et 1,99 ?

**Searches:** []

**Error:** BadRequestError('Error code: 400 - {\'error\': {\'message\': \'Tool choice is none, but model called a tool\', \'type\': \'invalid_request_error\', \'code\': \'tool_use_failed\', \'failed_generation\': \'{"name": "search_documents", "arguments": {"query":"GPA minimum cumulative GPA 2.00 \\\\"Al Akha

---

## 10. w_grade_fr#6 (claim)

**Proposed cause:** embellishment -- 'peuvent varier légèrement d'une année à l'autre' is in neither [1] nor [3]; the judge's quote even invented an English version of it.

**Question:** Que signifie la note W, et jusqu'à quand puis-je abandonner un cours en obtenant un W ?

**Searches:** [(None, {'query': "note W AUI politique de retrait cours W jusqu'à quand abandonner un cours W"})]

**Claim** (own, cites [1], [3]):

> Ces dates sont indiquées dans le calendrier académique et peuvent varier légèrement d’une année à l’autre ; il est donc conseillé de vérifier le calendrier académique de l’année en cours [1][3].

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** refer to academic calendar for published dates... These dates are indicated in the calendar académique and can vary slightly from one year to another

**Judge's reason:** Passage [1] mentions referring to the academic calendar for published dates, and the claim aligns with this.

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [103, 104]

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


[3] source: academic_catalog_2024_2025, pages: [112]

```text
only to graduate students. (Grade points not counted in GPA).
NPR: Indicates that the course was not passed and subsequently replaced with another one.
PMC: Indicates credits earned by a student before being matriculated.
W: Indicates official withdrawal from a course or withdrawal from the University up to the 40th
class day of a semester, or up to the 18th class day of a summer term (grade points not counted
in GPA).
WF: Indicates official withdrawal after the specified period for a W while having a failing grade,
and/or for excessive absences. (Grade points: 0.00) Starting Fall 2016, a ‘WF’ can be assigned up
to and including the last day of class.
WP: Indicates official withdrawal after the specified period for a W grade while having a passing
grade, at the time of withdrawal from the course (grade points are not counted in GPA).
I: Indicates incomplete work – used at the discretion of the instructor when a student has legitimate
```


---

## 11. scholarship_conditions_en#1 (claim)

**Proposed cause:** grad_undergrad -- Row labelled 'All scholarships (under-graduate & graduate)', but its conditions come from [1], the GRADUATE scholarships page (non-transferable, program change), mixed with an undergraduate-section line from [2].

**Question:** What are the conditions for keeping an Al Akhawayn scholarship?

**Searches:** [(None, {'query': 'Al Akhawayn scholarship conditions for keeping'})]

**Claim** (own, cites [1], [2]):

> Type of scholarship: **All scholarships (under‑graduate & graduate)**; Key conditions for continued eligibility: • Scholarships are granted for a specific program and **cannot be transferred** to another program outside the school in which the recipient was initially accepted.  • Newly admitted scholarship recipients may change their chosen program **before the first day of classes**.  • Students must **confirm acceptance** of the award and its renewal policy by paying any required deposit before the deadline.  • Scholarship holders who do not meet the renewal criteria will face **reduction, suspension, or termination** of the award. [1][2]

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Scholarships are granted for specific programs and are not transferable to other programs outside the school to which the scholarship recipient was initially accepted. New admitted candidates enrolled with a scholarship in their first semester at AUI are allowed to change their chosen program before the first day of classes... Students offered a scholarship should confirm their acceptance of the award and of its renewal policy by paying a scholarship deposit before the set deadline... Scholarship holders who do not meet the renewal criteria will face reduction, suspension, or termination of the award.

**Judge's reason:** The claim is fully supported by passages [1] and [2].

**Passages:**

[1] source: graduate_scholarships, pages: []

```text
Scholarships
Scholarships
Graduate Admissions
Lorem Ipsum
A place where inspiration finds you
Scholarship Types Offered based on 12 credits per semester
Scholarship Conditions
Al Akhawayn scholarships are predicated on the following conditions:
Scholarships are granted for specific programs and are not transferable to other programs outside the school to which the scholarship recipient was initially accepted. New admitted candidates enrolled with a scholarship in their first semester at AUI are allowed to change their chosen program before the first day of classes.
Graduate scholarship students benefiting from tuition waiver or more must provide services to Al Akhawayn by holding unpaid part-time jobs as assigned by the Financial Aid Office in different departments or schools at Al Akhawayn. They are required to work 10 hours per week (160 hours per semester) as part of their scholarship package.
```


[2] source: academic_catalog_2024_2025, pages: [66, 67]

```text
• A combination of these elements is used to rank undergraduate scholarship applicants and determine
the type of scholarship they will be awarded, students offered a scholarship should confirm their ac-
ceptance of the award and of its renewal policy by paying a scholarship deposit before the set deadline
stated on the scholarship decision message.
N.B.: High School Diploma must be recently obtained. However, the scholarship offer may also be
extended to one previous Bac year (the scholarship is not limited to first-year students).
Al Akhawayn University
www.aui.ma
2024-
2025
67
Newly admitted scholarship applicants should confirm their admission to AUI by paying any deposit re-
quired by the Admissions or the Financial Aid Office so that their files can be reviewed by the scholarship
committee.
Graduates
• Good post-baccalaureate academic results and recommendation of the school’s graduate com-
mittee with a distinction of at least “Assez Bien” in the “Licence, ” an equivalent for the French sys-
```


---

## 12. scholarship_conditions_en#2 (claim)

**Proposed cause:** judge_artifact -- Labelled 'Graduate (Master's)' and every fact is in [3] (graduate renewal policy) or [1] (graduate work hours) -- correctly attributed. Failed only because the quote joins [1] and [3].

**Question:** What are the conditions for keeping an Al Akhawayn scholarship?

**Searches:** [(None, {'query': 'Al Akhawayn scholarship conditions for keeping'})]

**Claim** (own, cites [1], [3]):

> Type of scholarship: **Graduate (Master’s) scholarships**; Key conditions for continued eligibility: • Maximum of **four enrolling semesters** (including one semester at the Language Center).  • Must maintain a **Semester Grade Point Average (SGPA) of at least 3.5**.  • If SGPA falls between **3.00 and 3.49**, the student is placed on **scholarship probation**; failure to return to the required standing results in reduction or suspension.  • If a student receives **W, WP, or WF in all courses** at the end of a semester, they are **automatically suspended** for the following semester.  • Graduate scholarship recipients must provide services to the university by holding **unpaid part‑time jobs** (10 hours/week, 160 hours per semester) as assigned by the Financial Aid Office. [3][1]

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Scholarship beneficiaries are eligible for an Al Akhawayn scholarship for a maximum of four enrolling semesters including one semester at the Language Center... maintaining a Semester Grade Point Average (SGPA) of at least 3.5. If the SGPA falls between 3.00 and 3.49, the student will be placed on scholarship probation... If the student obtains "W" or "WP" or "WF" in all courses at the end of any semester, s/he will be automatically placed on scholarship suspension for the following semester... Graduate scholarship students benefiting from tuition waiver or more must provide services to Al Akhawayn by holding unpaid part-time jobs as assigned by the Financial Aid Office... They are required to work 10 hours per week (160 hours per semester).

**Judge's reason:** The claim is fully supported by passages [1] and [3].

**Passages:**

[1] source: graduate_scholarships, pages: []

```text
Scholarships
Scholarships
Graduate Admissions
Lorem Ipsum
A place where inspiration finds you
Scholarship Types Offered based on 12 credits per semester
Scholarship Conditions
Al Akhawayn scholarships are predicated on the following conditions:
Scholarships are granted for specific programs and are not transferable to other programs outside the school to which the scholarship recipient was initially accepted. New admitted candidates enrolled with a scholarship in their first semester at AUI are allowed to change their chosen program before the first day of classes.
Graduate scholarship students benefiting from tuition waiver or more must provide services to Al Akhawayn by holding unpaid part-time jobs as assigned by the Financial Aid Office in different departments or schools at Al Akhawayn. They are required to work 10 hours per week (160 hours per semester) as part of their scholarship package.
```


[3] source: graduate_scholarships, pages: []

```text
Scholarship Renewal Policy for Graduate Students (Master’s Candidates)
Scholarship beneficiaries are eligible for an Al Akhawayn scholarship for a maximum of four enrolling semesters including one semester at the Language Center. The scholarship renewability depends on demonstrating excellence and successful progress in the student's studies as evidenced by maintaining a Semester Grade Point Average (SGPA) of at least 3.5. If the SGPA falls between 3.00 and 3.49, the student will be placed on scholarship probation. If the student fails to return to the required standing, reduction or suspension of the scholarship will apply. If the student obtains "W" or "WP" or "WF" in all courses at the end of any semester, s/he will be automatically placed on scholarship suspension for the following semester as described in the table below:
```


---

## 13. scholarship_conditions_en#3 (claim)

**Proposed cause:** heading_split -- Chunk [5] starts mid-sentence: '...semesters for undergraduates and 4 semesters for graduates' -- the undergraduate number was cut into the previous chunk, so the model guessed 'typically 8' (the catalog says nine, p. 67) and added 'often 3.0 or higher'.

**Question:** What are the conditions for keeping an Al Akhawayn scholarship?

**Searches:** [(None, {'query': 'Al Akhawayn scholarship conditions for keeping'})]

**Claim** (own, cites [5]):

> Type of scholarship: **Under‑graduate scholarships**; Key conditions for continued eligibility: • Scholarships are renewable for the **number of semesters specified** in the program (typically 8 for under‑graduates, 4 for graduates).  • Students must maintain an **overall GPA** that meets the program’s minimum (often 3.0 or higher).  • Summer‑session GPA is **not counted** for probation, suspension, or reinstatement purposes.  • Failure to maintain the required GPA can trigger **probation, suspension, or loss** of the scholarship. [5]

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** Passage [5] does not specify the number of semesters for undergraduates (only mentions 'typically 8' is not stated), nor does it confirm the minimum GPA requirement for undergraduates as 'often 3.0 or higher'.

**Passages:**

[5] source: academic_catalog_2024_2025, pages: [69, 70]

```text
semesters for undergraduates and 4 semesters for graduates. Students should be aware that the sum-
mer session GPA would not be taken into account for probation, suspension, or reinstatement.
Al Akhawayn University
www.aui.ma
2024-
2025
70
Combined Programs for Students with Scholarships
After completing the number of credits specified by their school graduate committee, scholarship holders
have the right to combine bachelor’s and master’s degrees, but they must apply for a new scholarship,
which may be granted based upon their CGPA, dean’s recommendation, and on their involvement and
respect for their commitments. If they are granted the scholarship, this scholarship will go towards the
tuition of the graduate course(s) only. This scholarship for the combined program covers three semesters
only with the possibility to apply for an extension and their scholarship type should not exceed the tuition
```


---

## 14. scholarship_conditions_fr (false_refusal)

**Proposed cause:** french_retrieval -- 3 French searches ('conditions pour conserver une bourse') returned loans, course lists and MBA pages -- none of the renewal-policy chunks the English question found -- so it declined.

**Question:** Quelles sont les conditions pour conserver une bourse Al Akhawayn ?

**Searches:** [(None, {'query': 'conditions pour conserver une bourse Al Akhawayn'}), (None, {'query': 'conditions conserver bourse Al Akhawayn conditions de maintien bourse'}), (None, {'query': 'bourse Al Akhawayn conditions de maintien'})]

**Answer:**

```text
Je n’ai trouvé aucune information concernant les conditions de maintien d’une bourse dans les documents que vous avez fournis.  

Si vous avez accès à d’autres ressources (site web de l’Université, portail des bourses, etc.) ou si vous pouvez préciser le type de bourse (bourse académique, bourse d’excellence, etc.), je pourrais vous aider à chercher les critères appropriés.
```

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [53, 54]

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


[2] source: academic_catalog_2024_2025, pages: [142, 143]

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


[4] source: academic_catalog_2024_2025, pages: [120]

```text
Al Akhawayn University
www.aui.ma
2024-
2025
120
student (Warning, Strong Warning, or Last Chance) will be considered to issue a decision.
• Dismissed means the student has been given ample opportunity to improve but failed to do so.
After earning 30 credit hours, the probation history of the students who are on the «At Risk List» is
managed by the Office of the Registrar.
Students dismissed by the Freshman Committee may reapply for readmission after one semester
( see” Readmission Process”). Their file shall be forwarded to the Vice President for Student Affairs.
Important Note:
• All Pass/Fail courses shall be converted to letter grades (A+, A, A-, B+, B, B-, C+, C, C-, D, F , or WF
instead of P/F) to compute a virtual SGPA.
• All students on the «At-Risk List» are required to complete 4 courses each semester.
• Students may not withdraw from any course.
• A failing grade means D, F , or WF .
Probation Regulations and Procedures
```


[5] source: academic_catalog_2024_2025, pages: [52]

```text
DHS so that their files can be reviewed by the financial aid committee.
2. AUI-Approved Bank Loans “Avenir Plus” or State Guaranteed Loan with CCG (Caisse Cen-
trale de Garantie)
Al Akhawayn University has convened agreements with a national bank for a loan program that will serve
the interests of students and at the same time enable them to contribute substantially toward financing
their own studies. Student loans are offered for the purpose of meeting the costs of studies at AUI.
They are available to all interested students for any semester while the bank bases the final decision on
adequate supporting documentation.
-  Loan Terms and Amounts
• Undergraduate Students
The loan program will provide qualified students with long-term loans payable over an extended period
with %0 annual interest rate, as the interest is supported by AUI. Students may borrow up to
50,000 MAD per year. Repayment begins 12 months following the date of the last amount released by the
```


[6] source: academic_catalog_2024_2025, pages: [261, 262]

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


[7] source: academic_catalog_2024_2025, pages: [380, 381]

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


[8] source: academic_catalog_2024_2025, pages: [320, 321]

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


---

## 15. scholarship_work_hours_fr#3 (claim)

**Proposed cause:** citation_placement -- 'up to 10 hours/week from the 2nd semester' is in [11], but '(160 heures par semestre)' is only in [12] (graduate page); the sentence cites [11] alone.

**Question:** Les étudiants boursiers en master doivent-ils travailler pour l'université ?

**Searches:** [(None, {'query': 'bourse master étudiant doit travailler université'}), (None, {'query': 'étudiants boursiers master travail université bourse doit travailler'}), (None, {'query': '"unpaid part-time job as exchange for their scholarship package"'})]

**Claim** (own, cites [11]):

> Ils doivent travailler **jusqu’à 10 heures par semaine (≈ 160 heures par semestre)** à partir de leur deuxième semestre [11].

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** graduate students on scholarship have to perform a contractual part-time job of up to 10 hours per week starting their 2nd semester at AUI... (160 hours per semester)

**Judge's reason:** The claim is directly supported by passage [11].

**Passages:**

[11] source: academic_catalog_2024_2025, pages: [68]

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

## 16. csc3326_prereqs_en#3 (claim)

**Proposed cause:** judge_artifact -- 'Junior classification' is verbatim in [1]; the judge's quote 'and Junior classification' is 3 words, under the 4-word minimum, so it doesn't count as evidence.

**Question:** What are the prerequisites for CSC 3326?

**Searches:** [(None, {'code': 'CSC 3326', 'follow_prerequisites': False})]

**Claim** (source_line, cites [1]):

> **Junior classification**

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** and Junior classification

**Judge's reason:** The claim matches the prerequisites stated in the passage exactly.

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [239]

```text
[1] CSC 3326: Database Systems (3 SCH), department CSC (source: academic_catalog_2024_2025, page 239)
Prerequisites (as stated in catalog): CSC 2306 (or CSC 1402 or BAI 3301) and Junior classification
```


---

## 17. csc3326_prereqs_fr#3 (claim)

**Proposed cause:** embellishment -- 'Junior' is in [1], but the gloss 'c'est-à-dire être au troisième semestre de votre programme' is not in any passage (and likely wrong).

**Question:** Quels sont les prérequis du cours CSC 3326 ?

**Searches:** [(None, {'code': 'CSC 3326', 'follow_prerequisites': False})]

**Claim** (source_line, cites [1]):

> être **classé en Junior** (c’est‑à‑dire être au troisième semestre de votre programme)

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** The passage states 'Junior classification' but does not define it as 'être au troisième semestre de votre programme'.

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [239]

```text
[1] CSC 3326: Database Systems (3 SCH), department CSC (source: academic_catalog_2024_2025, page 239)
Prerequisites (as stated in catalog): CSC 2306 (or CSC 1402 or BAI 3301) and Junior classification
```


---

## 18. mth1305_fr (false_refusal)

**Proposed cause:** uncitable_tool -- Only query_courses was called; it returned the 'no description' note (no marker), the model cited a [1] no tool returned and declined, never searching -- the catalog's p. 155 has 'MTH 1305 Mathematics for Business'.

**Question:** Qu'est-ce que le cours MTH 1305 ?

**Searches:** [(None, {'code': 'MTH 1305', 'follow_prerequisites': False})]

**Answer:**

```text
Je n’ai pas trouvé de description détaillée pour le cours **MTH 1305** dans le catalogue de l’Université d’Akhawayn : le code apparaît, mais aucun titre ni aucune liste de prérequis n’est fournie. [1]  

Je vous conseille donc de :

1. Vérifier votre programme d’études ou les exigences de votre filière, où le cours pourrait être mentionné ;
2. Contacter votre conseiller académique ou le service des études pour obtenir les informations précises (titre, crédits, prérequis, contenu, etc.).
```

**Passages:**
