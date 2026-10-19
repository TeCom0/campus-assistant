# Error analysis, run 3: 11 failures

Confirm each cause in error_causes_run3.json ("confirmed": one of grad_undergrad, heading_split, french_retrieval, citation_placement, crash, fallback, embellishment, misread, uncitable_tool, judge_artifact).

---

## 1. add_drop_en#8 (claim)

**Proposed cause:** judge_artifact -- Verbatim in [1] ('not official until all applicable tuition and fees have been paid to the University'); the quote failed only on the PDF's 'and/ or' spacing (as in runs 1-2).

**Question:** How do I add or drop a course at AUI?

**Searches:** [(None, {'query': 'add or drop a course policy AUI', 'query_en': 'add or drop a course policy AUI'})]

**Claim** (own, cites [1]):

> **Pay tuition and fees** – The add/drop is not official until all applicable tuition and fees have been paid to the university [1].

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** The adding and/or dropping of courses is not official until all applicable tuition and fees have been paid to the University.

**Judge's reason:** The passage directly supports the requirement to pay tuition and fees.

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [103]

```text
Section: Adding/Dropping Courses
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

## 2. add_drop_en#10 (claim)

**Proposed cause:** embellishment -- [1] says courses dropped within the add/drop period 'are not reflected on the academic record'; the claim adds 'until the process is finalized', which no passage says (and changes the meaning).

**Question:** How do I add or drop a course at AUI?

**Searches:** [(None, {'query': 'add or drop a course policy AUI', 'query_en': 'add or drop a course policy AUI'})]

**Claim** (own, cites [1]):

> **Result on your record** – Courses dropped during the add/drop period are not reflected on your academic record until the process is finalized [1].

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** The passage states courses dropped during the add/drop period are not reflected on the academic record, but it does not mention 'until the process is finalized.'

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [103]

```text
Section: Adding/Dropping Courses
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

## 3. add_drop_fr#6 (claim)

**Proposed cause:** judge_artifact -- The French claim restates [6]'s 'not official until all applicable tuition and fees have been paid'; the quote failed only on 'and/ or' spacing.

**Question:** Comment ajouter ou supprimer un cours à l'AUI ?

**Searches:** [(None, {'query': 'ajouter ou supprimer un cours AUI', 'query_en': 'add or drop a course AUI'}), (None, {'query': 'add drop courses AUI add or drop a course', 'query_en': 'add drop course AUI'})]

**Claim** (own, cites [6]):

> Étape: 5; Action: Paiement; Détails: L’ajout ou le retrait n’est officiel que lorsque **les frais de scolarité et les frais applicables** ont été réglés.; Citation: [6]

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** The adding and/or dropping of courses is not official until all applicable tuition and fees have been paid to the University.

**Judge's reason:** The passage confirms that payment of tuition and fees is required for the process to be official.

**Passages:**

[6] source: academic_catalog_2024_2025, pages: [103]

```text
Section: Adding/Dropping Courses
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

## 4. course_load_fr#5 (claim)

**Proposed cause:** french_retrieval -- The catalog HAS an explicit rule (p. 116: CGPA >= 3.00 may take six courses; below that, a sixth with the coordinator's and Dean's approval), but the French question's searches dropped its 'sixth course' half ('maximum number of courses per semester AUI'), so it was never retrieved (course_load_en searched 'allowed a sixth course' and found it). The model then claimed 'the catalog sets no explicit limit'.

**Question:** Combien de cours puis-je suivre pendant un semestre normal, et quand ai-je droit à un sixième cours ?

**Searches:** [(None, {'query': 'maximum number of courses per semester AUI', 'query_en': 'maximum number of courses per semester AUI'}), (None, {'query': 'maximum number of courses per semester undergraduate AUI', 'query_en': 'maximum number of courses per semester undergraduate AUI'}), (None, {'query': 'maximum number of courses per semester undergraduate normal semester AUI', 'query_en': 'maximum number of courses per semester undergraduate normal semester AUI'})]

**Claim** (lead_in, cites [2]):

> En dehors de cette situation, le catalogue ne fixe pas de limite explicite supérieure à la charge recommandée; une autorisation spéciale de la faculté ou du service académique serait alors nécessaire pour dépasser la charge habituelle (5 cours).

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** The passage does not mention any explicit limit or the need for special authorization to exceed the recommended load (5 courses).

**Passages:**

[2] source: academic_catalog_2024_2025, pages: [67]

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

## 5. course_load_fr#7 (claim)

**Proposed cause:** citation_placement -- 'Minimum: 4 cours (12 SCH)' is in [7] (p. 116, which the answer's own bullets cite); this summary line has no marker and the lead_in rule gave it [2] (the scholarship passage), which doesn't have it. Same pattern as run 2's add_drop_en#16.

**Question:** Combien de cours puis-je suivre pendant un semestre normal, et quand ai-je droit à un sixième cours ?

**Searches:** [(None, {'query': 'maximum number of courses per semester AUI', 'query_en': 'maximum number of courses per semester AUI'}), (None, {'query': 'maximum number of courses per semester undergraduate AUI', 'query_en': 'maximum number of courses per semester undergraduate AUI'}), (None, {'query': 'maximum number of courses per semester undergraduate normal semester AUI', 'query_en': 'maximum number of courses per semester undergraduate normal semester AUI'})]

**Claim** (lead_in, cites [2]):

> **Minimum** : 4 cours (12 SCH).

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** time for undergraduate students means that they must maintain at least twelve (12) SCH during the fall or spring semesters

**Judge's reason:** The passage explicitly states the minimum SCH requirement (12 SCH), which corresponds to 4 courses of 3 SCH each.

**Passages:**

[2] source: academic_catalog_2024_2025, pages: [67]

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

## 6. course_load_fr#8 (claim)

**Proposed cause:** citation_placement -- 'Recommandé: 5 cours (15 SCH)': the 15 SCH recommendation is in [7]; same lead_in scope ([2]) as #7.

**Question:** Combien de cours puis-je suivre pendant un semestre normal, et quand ai-je droit à un sixième cours ?

**Searches:** [(None, {'query': 'maximum number of courses per semester AUI', 'query_en': 'maximum number of courses per semester AUI'}), (None, {'query': 'maximum number of courses per semester undergraduate AUI', 'query_en': 'maximum number of courses per semester undergraduate AUI'}), (None, {'query': 'maximum number of courses per semester undergraduate normal semester AUI', 'query_en': 'maximum number of courses per semester undergraduate normal semester AUI'})]

**Claim** (lead_in, cites [2]):

> **Recommandé** : 5 cours (15 SCH).

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** the University strongly recommends that students enroll each semester for at least 15 credit hours

**Judge's reason:** The passage explicitly recommends 15 SCH, which corresponds to 5 courses of 3 SCH each.

**Passages:**

[2] source: academic_catalog_2024_2025, pages: [67]

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

## 7. course_load_fr#9 (claim)

**Proposed cause:** french_retrieval -- 'Sixth course mainly for scholarship students (perhaps with special authorization)' -- the real sixth-course rule (p. 116, CGPA 3.00) was never retrieved (see #5); [2] only recommends six courses to scholarship holders.

**Question:** Combien de cours puis-je suivre pendant un semestre normal, et quand ai-je droit à un sixième cours ?

**Searches:** [(None, {'query': 'maximum number of courses per semester AUI', 'query_en': 'maximum number of courses per semester AUI'}), (None, {'query': 'maximum number of courses per semester undergraduate AUI', 'query_en': 'maximum number of courses per semester undergraduate AUI'}), (None, {'query': 'maximum number of courses per semester undergraduate normal semester AUI', 'query_en': 'maximum number of courses per semester undergraduate normal semester AUI'})]

**Claim** (lead_in, cites [2]):

> **Sixième cours** possible surtout pour les étudiants sous bourse (et éventuellement avec autorisation particulière).

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** The passage only mentions the recommendation for scholarship beneficiaries to take six courses; it does not address the possibility of a sixth course for non-beneficiaries or the need for special authorization.

**Passages:**

[2] source: academic_catalog_2024_2025, pages: [67]

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

## 8. academic_probation_en#7 (claim)

**Proposed cause:** citation_placement -- '2 semesters or 12 credits (whichever comes first)... suspension or dismissal' is in retrieved passage [2] (p. 121, Academic Dismissal); the closing source line cites [1] only.

**Question:** What happens if my GPA falls between 1.5 and 1.99?

**Searches:** [(None, {'query': 'GPA falls between 1.5 and 1.99 academic probation AUI', 'query_en': 'GPA falls between 1.5 and 1.99 academic probation AUI'})]

**Claim** (source_line, cites [1]):

> If you remain on probation for **two semesters or 12 credits (whichever comes first)** without raising your GPA to 2.00, the university may suspend or dismiss you from the program.

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Undergraduate students on academic probation have 2 semesters or 12 credits (whichever occurs first) to raise their GPA to 2.00. Failure to raise the GPA to 2.00 after 2 semesters on academic probation may result in suspension or dismissal from the University.

**Judge's reason:** The passage supports the claim about the consequences of remaining on probation.

**Passages:**

[1] source: academic_catalog_2024_2025, pages: [121]

```text
Section: Undergraduate Studies > Repeat Policy
time, a student may, after consulting with the advisor and the school coordinator, appeal to the
school dean for permission to take the course a third time.
Academic Probation
Undergraduate students are placed on academic probation if their GPA falls between 1.5 and 1.99.
This probationary status serves as a warning to students that their performance is below the level
required. Students on academic probation may not exceed four courses (up to 13 semester hours)
in the subsequent regular semester. To return to satisfactory standing at the end of this semester
requires a semester GPA of 2.00 or greater. Performance in a summer session or intersession does
not grant a return to a satisfactory standing. No notation of academic probation appears on the
transcript.
Unsatisfactory Standing
Undergraduate students are considered to have an unsatisfactory standing if their semester
GPA is less than 1.5. Students at this level must appeal and obtain special permission from
```


---

## 9. repeat_course_fr#3 (claim)

**Proposed cause:** judge_artifact -- A faithful French translation of [5]'s 'A student may repeat any course in which a C- or lower has been earned' (undergraduate passage); the judge's quote mixed French and English ('...un C- ou lower has been earned'), so it failed the check.

**Question:** Je suis en licence et j'ai eu C- dans un cours. Puis-je reprendre ce cours, et quelle note compte dans ma moyenne ?

**Searches:** [(None, {'query': 'reprendre un cours AUI licence', 'query_en': 'course repetition AUI undergraduate'})]

**Claim** (own, cites [5]):

> « Un étudiant peut répéter tout cours dans lequel il a obtenu un C‑ ou une note inférieure. » [5]

**Judge:** supported -> unsupported [quote_not_found]

**Judge's quote:** Un étudiant peut répéter tout cours dans lequel il a obtenu un C- ou lower has been earned.

**Judge's reason:** The claim is an exact paraphrase of the policy stated in passage [5].

**Passages:**

[5] source: academic_catalog_2024_2025, pages: [120, 121]

```text
Section: Undergraduate Studies > Repeat Policy
SGPA ≥ 2.0 Under Watch Allowed
If Decision
was Strong Warning and...
SGPA < 2.0 Dismissal
(may appeal)
Not Allowed
SGPA ≥ 2.9 Under Watch Allowed
If Decision was Last Chance and...
If Decision was Last Chance and...
SGPA < 2.0
and no failing grade
Under Watch Allowed
SGPA > 2.0 and CGPA ≥
2.0 (at least 12 career* earned
credits)
Semester Off N/A
SGPA < 2.0
and CGAP < 2.0
Dismissal N/A
Al Akhawayn University
www.aui.ma
2024-
2025
121
If a course is repeated, the highest grade earned is the grade used to compute the cumulative
grade point average (CGPA) for all purposes. Repeated courses are counted only once for credit.
An undergraduate course in which a grade of C or higher has been earned may not be repeated for
credit. A student may repeat any course in which a C- or lower has been earned.
Normally a student is allowed to repeat a course only once. If a required course is failed a second
time, a student may, after consulting with the advisor and the school coordinator, appeal to the
```


---

## 10. repeat_course_fr#4 (claim)

**Proposed cause:** citation_placement -- 'If a course is repeated, the highest grade earned is used for the CGPA' is in BOTH [5] (undergraduate repeat policy) and [2] (graduate); the answer to a 'licence' question cites the graduate passage [2]. The fact is right for undergraduates, the citation points to the wrong level's passage. Alternative: grad_undergrad.

**Question:** Je suis en licence et j'ai eu C- dans un cours. Puis-je reprendre ce cours, et quelle note compte dans ma moyenne ?

**Searches:** [(None, {'query': 'reprendre un cours AUI licence', 'query_en': 'course repetition AUI undergraduate'})]

**Claim** (block, cites [2]):

> « Si un cours est répété, la note la plus élevée obtenue est utilisée pour calculer le GPA cumulé (CGPA) pour toutes les fins.

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** The claim incorrectly attributes the policy to passage [2], which is about graduate studies, not undergraduate (licence) studies.

**Passages:**

[2] source: academic_catalog_2024_2025, pages: [314]

```text
Section: Graduate Studies > Time Limitations
graduate according to the requirements of the catalog in force at the time of readmission.
Grading Policies and Academic Progress
Refer to the section on Grading Policy and to each school’s section for academic progress regulations.
Repeat Policy
All courses taken at AUI, whether passed or failed, remain a permanent part of the student’s record. If
a course is repeated, the highest grade earned is the grade used to compute the cumulative grade point
average (CGPA) for all purposes. Repeated courses are counted only once for credit.
A graduate course in which a grade of B or higher has been earned may not be repeated for credit. A
student may repeat any course in which a B- or lower has been earned.
Normally a student is allowed to repeat a course only once. If a required course is failed a second time, a
student may, after consulting with the advisor and the school coordinator, appeal to the school dean for
permission to take the course a third time.
Undergraduate Foundation Courses
```


---

## 11. scholarship_work_hours_en#3 (claim)

**Proposed cause:** embellishment -- 'This is the standard requirement for graduate scholarship students' generalizes [5], which limits it to graduate scholarship students 'benefiting from tuition waiver or more'.

**Question:** Do graduate scholarship students have to work for the university?

**Searches:** [(None, {'query': 'graduate scholarship students have to work for the university', 'query_en': 'graduate scholarship students have to work for the university'})]

**Claim** (block, cites [5]):

> This is the standard requirement for graduate scholarship students.

**Judge:** unsupported -> unsupported

**Judge's quote:** (none)

**Judge's reason:** The passage does not state that this is the 'standard requirement' for all graduate scholarship students; it only applies to those with a tuition waiver or more.

**Passages:**

[5] source: graduate_scholarships, pages: []

```text
Section: Graduate Studies > Lorem Ipsum
Graduate scholarship students benefiting from tuition waiver or more must provide services to Al Akhawayn by holding unpaid part-time jobs as assigned by the Financial Aid Office in different departments or schools at Al Akhawayn. They are required to work 10 hours per week (160 hours per semester) as part of their scholarship package.
Graduate scholarship holders can apply for the Exchange Program for one summer only and take a minimum of six transferable credits or for a regular semester where the programs offered are very limited.
However, if the student takes fewer than the recommended full-time load, they should be aware that they run the risk of needing more than four semesters to complete their studies, in which case they will have to pay for additional courses beyond the fourth semester.
Students are allowed to use their scholarships during summer sessions conditional upon not exceeding their scholarship period of 4 sessions.
Applying for Scholarships
```

